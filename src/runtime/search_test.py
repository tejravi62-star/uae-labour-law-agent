"""Compare keyword vs vector vs hybrid(+semantic) retrieval for one question.
Usage: python search_test.py "your question" [keyword|vector|hybrid]
"""
import sys

from azure.identity import get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

from settings import OPENAI_ENDPOINT, SEARCH_ENDPOINT, SEARCH_INDEX, EMBED_DEPLOYMENT, PACK, credential

question = sys.argv[1]

import json
from pathlib import Path
_manifest = json.loads((Path(__file__).resolve().parents[2] / "packs" / PACK / "pack.json").read_text())
_expansions = [v for k, v in _manifest.get("glossary", {}).items() if k in question.lower()]
expanded = f"{question} {' '.join(_expansions)}".strip()
if _expansions:
    print(f"(glossary expanded: + {_expansions})")
mode = sys.argv[2] if len(sys.argv) > 2 else "hybrid"

search = SearchClient(SEARCH_ENDPOINT, SEARCH_INDEX, credential)
kwargs = {"filter": f"pack eq '{PACK}'", "top": 5, "select": ["title", "page", "content"]}

if mode in ("vector", "hybrid"):
    aoai = AzureOpenAI(
        azure_endpoint=OPENAI_ENDPOINT, api_version="2024-10-21",
        azure_ad_token_provider=get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default"),
    )
    vector = aoai.embeddings.create(model=EMBED_DEPLOYMENT, input=expanded).data[0].embedding
    kwargs["vector_queries"] = [VectorizedQuery(vector=vector, k_nearest_neighbors=5, fields="content_vector")]

if mode == "hybrid":
    kwargs["query_type"] = "semantic"
    kwargs["semantic_configuration_name"] = "default"

search_text = None if mode == "vector" else expanded
print(f'\nQ: "{question}"  [mode={mode}]\n')
for i, r in enumerate(search.search(search_text=search_text, **kwargs), 1):
    rerank = r.get("@search.reranker_score")
    score = f"rerank={rerank:.2f}" if rerank is not None else f"score={r['@search.score']:.3f}"
    snippet = " ".join(r["content"].split())[120:280]
    print(f"{i}. {r['title'][:75]:75} | {score}")
    print(f"   ...{snippet}...")
