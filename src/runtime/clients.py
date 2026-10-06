"""Shared, keyless Azure clients. Created once and reused (connection reuse = lower latency)."""
from functools import lru_cache

from azure.identity import get_bearer_token_provider
from azure.search.documents import SearchClient
from openai import AzureOpenAI

from settings import OPENAI_ENDPOINT, SEARCH_ENDPOINT, SEARCH_INDEX, credential

API_VERSION = "2024-10-21"


@lru_cache
def aoai() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=OPENAI_ENDPOINT,
        api_version=API_VERSION,
        azure_ad_token_provider=get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default"),
        max_retries=6,
    )


@lru_cache
def search_client() -> SearchClient:
    return SearchClient(SEARCH_ENDPOINT, SEARCH_INDEX, credential)
