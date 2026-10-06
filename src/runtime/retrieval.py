"""search_law: the generic retrieval tool. Glossary expansion + hybrid + semantic rerank + pack filter."""
from azure.search.documents.models import VectorizedQuery

from clients import aoai, search_client
from packs import manifest
from settings import EMBED_DEPLOYMENT, PACK


def expand(query: str) -> str:
    extra = [v for k, v in manifest().get("glossary", {}).items() if k in query.lower()]
    return f"{query} {' '.join(extra)}".strip()


def search_law(query: str, top: int = 4) -> list:
    q = expand(query)
    vector = aoai().embeddings.create(model=EMBED_DEPLOYMENT, input=q).data[0].embedding
    results = search_client().search(
        search_text=q,
        vector_queries=[VectorizedQuery(vector=vector, k_nearest_neighbors=top, fields="content_vector")],
        filter=f"pack eq '{PACK}'",
        query_type="semantic",
        semantic_configuration_name="default",
        top=top,
        select=["title", "page", "content"],
    )
    return [
        {
            "source": r["title"],
            "pdf_page": r["page"],
            "relevance": round(r.get("@search.reranker_score") or 0, 2),
            "text": " ".join(r["content"].split()),
        }
        for r in results
    ]


def search_tool_schema() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "search_law",
            "description": (
                f"Search the official {manifest()['display_name']} documents. Call this before answering "
                "ANY legal question. Returns passages labelled with source, PDF page and article numbers for citation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query in plain English using key legal terms"}
                },
                "required": ["query"],
            },
        },
    }
