"""Creates (or updates) the search index. Safe to run repeatedly."""
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField, SearchFieldDataType,
    VectorSearch, HnswAlgorithmConfiguration, HnswParameters, VectorSearchProfile,
    SemanticSearch, SemanticConfiguration, SemanticPrioritizedFields, SemanticField,
)
from settings import SEARCH_ENDPOINT, SEARCH_INDEX, EMBED_DIMENSIONS, credential

fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
    SimpleField(name="pack", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="source_file", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="article", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="page", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
    SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
    SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
    SearchField(
        name="content_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=EMBED_DIMENSIONS,
        vector_search_profile_name="hnsw-cosine",
    ),
]

vector_search = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(name="hnsw", parameters=HnswParameters(metric="cosine"))],
    profiles=[VectorSearchProfile(name="hnsw-cosine", algorithm_configuration_name="hnsw")],
)

semantic_search = SemanticSearch(
    configurations=[
        SemanticConfiguration(
            name="default",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="title"),
                content_fields=[SemanticField(field_name="content")],
            ),
        )
    ],
    default_configuration_name="default",
)

index = SearchIndex(name=SEARCH_INDEX, fields=fields, vector_search=vector_search, semantic_search=semantic_search)

client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)
result = client.create_or_update_index(index)
print(f"Index ready: {result.name}")
for f in result.fields:
    print(f"  {f.name:15} {str(f.type):35} filterable={f.filterable}")
