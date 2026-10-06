"""Central configuration. Every script imports from here; values come from .env or the environment."""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential

load_dotenv()

OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
STORAGE_ACCOUNT = os.environ["AZURE_STORAGE_ACCOUNT"]
CHAT_DEPLOYMENT = os.environ.get("CHAT_DEPLOYMENT", "chat-mini")
EMBED_DEPLOYMENT = os.environ.get("EMBED_DEPLOYMENT", "embed-small")
EMBED_DIMENSIONS = int(os.environ.get("EMBED_DIMENSIONS", "1536"))
SEARCH_INDEX = os.environ.get("SEARCH_INDEX", "mizan-kb")
DOCS_CONTAINER = os.environ.get("DOCS_CONTAINER", "docs")
PACK = os.environ.get("PACK", "uae-labour-law")

# One credential for everything: az login on the Mac, managed identity in Azure.
credential = DefaultAzureCredential()
