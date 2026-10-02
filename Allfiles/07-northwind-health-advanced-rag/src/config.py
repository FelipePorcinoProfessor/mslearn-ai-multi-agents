from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    search_endpoint: str
    openai_endpoint: str
    embedding_deployment: str
    semantic_configuration: str = "clinical-semantic-config"
    vector_dimensions: int = 1536


def load_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    return Settings(
        search_endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        openai_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        embedding_deployment=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
    )