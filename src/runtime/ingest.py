"""Ingest a domain pack: blob PDFs -> clean -> split by Article -> embed -> upload to AI Search.

Usage:
  python ingest.py --dry-run                      # all manifest files, preview only
  python ingest.py --dry-run --file X.pdf         # one file (for comparison)
  python ingest.py --dry-run --layout             # use pypdf layout extraction mode
  python ingest.py                                # embed + upload
"""
import argparse
import io
import json
import re
import unicodedata
from bisect import bisect_right
from collections import Counter
from pathlib import Path

from azure.identity import get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import AzureOpenAI
from pypdf import PdfReader

from settings import (
    OPENAI_ENDPOINT, SEARCH_ENDPOINT, STORAGE_ACCOUNT, EMBED_DEPLOYMENT,
    SEARCH_INDEX, DOCS_CONTAINER, PACK, credential,
)

REPO = Path(__file__).resolve().parents[2]
PACK_DIR = REPO / "packs" / PACK
MANIFEST = json.loads((PACK_DIR / "pack.json").read_text())

ARTICLE_RE = re.compile(r"(?m)^\s*Article\s*\(\s*(\d+)\s*\)[ \t]*(.*)$")
MIN_SECTION_CHARS = 250      # shorter = table-of-contents line or noise
MIN_PART_ARTICLES = 5        # a "part" with fewer articles is a TOC, not a document
HEADER_PAGE_SHARE = 0.3      # a line on >=30% of pages is a header/footer
TITLE_JUNK = "►•▪◦- \t"

splitter = RecursiveCharacterTextSplitter(
    chunk_size=2400, chunk_overlap=300, separators=["\n\n", "\n", ". ", " "],
)


def fix_text(text):
    text = unicodedata.normalize("NFKC", text)                 # ligatures: ﬁ -> fi, ﬀ -> ff
    text = re.sub(r"/([A-Za-z])_([A-Za-z])", r"\1\2", text)     # glyph names: /T_he -> The
    return text


def download_pdf(file_name):
    svc = BlobServiceClient(f"https://{STORAGE_ACCOUNT}.blob.core.windows.net", credential=credential)
    return svc.get_blob_client(DOCS_CONTAINER, f"{PACK}/{file_name}").download_blob().readall()


def read_pages(pdf_bytes, layout=False):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        raw = page.extract_text(extraction_mode="layout") if layout else page.extract_text()
        pages.append((i + 1, fix_text(raw or "")))
    return pages


def clean_pages(pages):
    counts = Counter()
    for _, text in pages:
        counts.update({line.strip() for line in text.splitlines() if line.strip()})
    threshold = max(3, int(len(pages) * HEADER_PAGE_SHARE))
    repeated = {line for line, c in counts.items() if c >= threshold}
    cleaned = []
    for page_no, text in pages:
        lines = [
            line for line in text.splitlines()
            if line.strip() and line.strip() not in repeated and not re.fullmatch(r"\d{1,3}", line.strip())
        ]
        cleaned.append((page_no, "\n".join(lines)))
    return cleaned, repeated


def split_articles(pages):
    full, starts = "", []
    for _, text in pages:
        starts.append(len(full))
        full += text + "\n"

    def page_of(pos):
        return pages[bisect_right(starts, pos) - 1][0]

    matches = list(ARTICLE_RE.finditer(full))
    sections, part, prev_num = [], 1, 0
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full)
        body = full[m.start():end].strip()
        if len(body) < MIN_SECTION_CHARS:
            continue
        num = int(m.group(1))
        if num < prev_num - 5:
            part += 1
        prev_num = num
        lines = body.splitlines()
        title = m.group(2).strip() or (lines[1].strip() if len(lines) > 1 else "")
        sections.append({
            "article": str(num), "part": part, "title": title.strip(TITLE_JUNK)[:120],
            "page": page_of(m.start()), "body": body,
        })

    counts = Counter(s["part"] for s in sections)
    keep = [p for p in sorted(counts) if counts[p] >= MIN_PART_ARTICLES]
    remap = {p: i + 1 for i, p in enumerate(keep)}
    return label_ranges([dict(s, part=remap[s["part"]]) for s in sections if s["part"] in remap])


def label_ranges(sections):
    """If numbering jumps (50 -> 52), the missing article's label was lost in extraction and its
    text merged into the previous one. Label honestly as 'Articles 50-51' instead of 'Article 50'."""
    for i, s in enumerate(sections):
        cur = int(s["article"])
        same_part_next = i + 1 < len(sections) and sections[i + 1]["part"] == s["part"]
        nxt = int(sections[i + 1]["article"]) if same_part_next else cur + 1
        s["label"] = f"Articles {cur}-{nxt - 1}" if nxt > cur + 1 else f"Article {cur}"
    return sections


def coverage_report(sections):
    for p in sorted({s["part"] for s in sections}):
        nums = sorted({int(s["article"]) for s in sections if s["part"] == p})
        missing = [n for n in range(1, max(nums) + 1) if n not in nums]
        label = MANIFEST.get("parts", {}).get(str(p), f"Part {p}")
        print(f"  part {p} ({label}): articles 1-{max(nums)} | found {len(nums)} | missing {len(missing)}: {missing[:15]}")


ARTICLE_ANY_RE = re.compile(r"Article\s*\(\s*(\d+)\s*\)")
TOC_ARTICLE_LIMIT = 12       # a page naming more articles than this is a table of contents
CARRY_CHARS = 300            # tail of previous page prepended, to keep cross-page articles together


def part_for_page(page_no):
    for rng, label in MANIFEST.get("page_parts", {}).items():
        a, b = (int(x) for x in rng.split("-"))
        if a <= page_no <= b:
            return label
    return MANIFEST["display_name"]


def page_chunks(file_name, pages):
    label = MANIFEST["display_name"]
    language = MANIFEST.get("language", "en")
    chunks, skipped, prev_tail = [], [], ""
    for page_no, text in pages:
        nums = sorted({int(n) for n in ARTICLE_ANY_RE.findall(text)})
        if len(nums) > TOC_ARTICLE_LIMIT:
            skipped.append(page_no)
            prev_tail = ""
            continue
        if len(text.strip()) < 100:
            continue
        part = part_for_page(page_no)
        arts = ", ".join(map(str, nums)) if nums else "none labelled"
        header = f"{label} > {part} > page {page_no} (Articles on page: {arts})"
        body = f"{prev_tail}\n{text}" if prev_tail else text
        for j, piece in enumerate(splitter.split_text(body)):
            cid = re.sub(r"[^A-Za-z0-9_\-=]", "-", f"{PACK}-{Path(file_name).stem}-pg{page_no}-{j}")
            chunks.append({
                "id": cid, "pack": PACK, "language": language, "source_file": file_name,
                "article": str(nums[0]) if nums else "", "page": page_no,
                "title": f"{part} - page {page_no} - Articles {arts}",
                "content": f"{header}\n{piece}",
            })
        prev_tail = text[-CARRY_CHARS:]
    return chunks, skipped


def build_chunks(file_name, sections):
    label = MANIFEST["display_name"]
    language = MANIFEST.get("language", "en")
    seen, chunks = set(), []
    for s in sections:
        part_label = MANIFEST.get("parts", {}).get(str(s["part"]), f"Part {s['part']}")
        header = f"{label} > {part_label} > {s['label']}: {s['title']}"
        for j, piece in enumerate(splitter.split_text(s["body"])):
            cid = re.sub(r"[^A-Za-z0-9_\-=]", "-", f"{PACK}-{Path(file_name).stem}-p{s['part']}-a{s['article']}-{j}")
            base, n = cid, 1
            while cid in seen:
                n += 1
                cid = f"{base}-dup{n}"
            seen.add(cid)
            chunks.append({
                "id": cid, "pack": PACK, "language": language, "source_file": file_name,
                "article": s["article"], "page": s["page"],
                "title": f"{part_label} - {s['label']}: {s['title']}",
                "content": f"{header}\n{piece}",
            })
    return chunks


def embed(chunks, batch_size=16):
    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
    client = AzureOpenAI(azure_endpoint=OPENAI_ENDPOINT, api_version="2024-10-21",
                         azure_ad_token_provider=token_provider, max_retries=6)
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        resp = client.embeddings.create(model=EMBED_DEPLOYMENT, input=[c["content"] for c in batch])
        for chunk, item in zip(batch, resp.data):
            chunk["content_vector"] = item.embedding
        print(f"  embedded {min(i + batch_size, len(chunks))}/{len(chunks)}")


def upload(chunks, batch_size=100):
    client = SearchClient(SEARCH_ENDPOINT, SEARCH_INDEX, credential)
    for i in range(0, len(chunks), batch_size):
        results = client.merge_or_upload_documents(chunks[i:i + batch_size])
        failed = [r.key for r in results if not r.succeeded]
        print(f"  uploaded {min(i + batch_size, len(chunks))}/{len(chunks)} (failed: {len(failed)})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--file", help="ingest only this file (must be uploaded under the pack prefix)")
    parser.add_argument("--layout", action="store_true", help="use pypdf layout extraction mode")
    parser.add_argument("--strategy", choices=["article", "page"], help="override pack.json strategy")
    args = parser.parse_args()

    files = [args.file] if args.file else MANIFEST["ingest"]
    all_chunks = []
    for file_name in files:
        print(f"\n== {file_name} (layout={args.layout})")
        pages, repeated = clean_pages(read_pages(download_pdf(file_name), layout=args.layout))
        strategy = args.strategy or MANIFEST.get("strategy", "article")
        if strategy == "page":
            chunks, skipped = page_chunks(file_name, pages)
            print(f"  strategy=page | pages: {len(pages)} | header lines removed: {len(repeated)} | TOC pages skipped: {skipped} | chunks: {len(chunks)}")
        else:
            sections = split_articles(pages)
            chunks = build_chunks(file_name, sections)
            print(f"  strategy=article | pages: {len(pages)} | articles: {len(sections)} | chunks: {len(chunks)}")
            coverage_report(sections)
        all_chunks.extend(chunks)

    print(f"\nTOTAL chunks: {len(all_chunks)} | ~{sum(len(c['content']) for c in all_chunks) // 4:,} tokens")

    if args.dry_run:
        out = PACK_DIR / "chunks.preview.jsonl"
        with out.open("w") as f:
            for c in all_chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        print(f"Dry run: wrote {out.relative_to(REPO)}")
        return

    print("\nEmbedding...")
    embed(all_chunks)
    print("Uploading...")
    upload(all_chunks)
    print("Done.")


if __name__ == "__main__":
    main()
