"""Loads the configured domain pack: manifest, system prompt, and pack-specific tools."""
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

from settings import PACK

PACK_DIR = Path(__file__).resolve().parents[2] / "packs" / PACK


@lru_cache
def manifest() -> dict:
    return json.loads((PACK_DIR / "pack.json").read_text())


@lru_cache
def system_prompt() -> str:
    return (PACK_DIR / "prompt.md").read_text()


@lru_cache
def pack_tools() -> dict:
    path = PACK_DIR / "tools.py"
    if not path.exists():
        return {}
    spec = importlib.util.spec_from_file_location(f"pack_tools_{PACK.replace('-', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "TOOLS", {})
