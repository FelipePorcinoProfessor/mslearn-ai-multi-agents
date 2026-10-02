from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    cosmos_endpoint: str
    database_name: str
    memory_container: str
    audit_container: str
    openai_endpoint: str
    embedding_deployment: str


def load_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    return Settings(
        cosmos_endpoint=os.environ["AZURE_COSMOS_ENDPOINT"],
        database_name=os.getenv("AZURE_COSMOS_DATABASE_NAME", "clinical-memory-db"),
        memory_container=os.getenv("AZURE_COSMOS_MEMORY_CONTAINER", "patient-memories"),
        audit_container=os.getenv("AZURE_COSMOS_AUDIT_CONTAINER", "memory-audit"),
        openai_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        embedding_deployment=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
    )