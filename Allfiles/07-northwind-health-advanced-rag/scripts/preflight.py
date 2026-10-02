from __future__ import annotations

import importlib.util
import json
import os
import py_compile
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
sys.path.insert(0, str(ROOT))

from src.chunking import generate_chunks


def main() -> int:
    failures: list[str] = []
    if sys.version_info < (3, 11):
        failures.append("Python 3.11 or later is required.")
    for package in ("azure.search.documents", "azure.identity", "openai"):
        if importlib.util.find_spec(package) is None:
            failures.append(f"Missing package: {package}")
    try:
        source_documents = json.loads((ROOT / "assets" / "source-documents.json").read_text(encoding="utf-8"))
        configurations = json.loads((ROOT / "assets" / "chunk-strategies.json").read_text(encoding="utf-8"))
        queries = json.loads((ROOT / "assets" / "queries.json").read_text(encoding="utf-8"))
        legacy_marker = json.loads((ROOT / "assets" / "documents.json").read_text(encoding="utf-8"))
        if legacy_marker.get("deprecated") is not True or "chunks" in legacy_marker:
            failures.append("assets/documents.json must remain a chunk-free legacy marker.")
        required_source = {"id", "title", "category", "source", "sections"}
        if not source_documents or any(required_source - set(document) for document in source_documents):
            failures.append("Every synthetic source document must contain source and section metadata.")
        elif any(not document["sections"] for document in source_documents):
            failures.append("Every synthetic source document must contain at least one section.")
        manifest = generate_chunks(source_documents, configurations)
        expected_strategies = {"fixed-overlap", "structural-parent-child"}
        actual_strategies = {summary["strategy"] for summary in manifest["strategy_summaries"]}
        parent_ids = {document["id"] for document in source_documents}
        if actual_strategies != expected_strategies:
            failures.append("Chunk configurations must include both required strategies.")
        if len({chunk["id"] for chunk in manifest["chunks"]}) != len(manifest["chunks"]):
            failures.append("Generated chunk IDs must be unique across strategies.")
        for strategy in expected_strategies:
            strategy_parents = {
                chunk["parent_id"] for chunk in manifest["chunks"] if chunk["chunk_strategy"] == strategy
            }
            if strategy_parents != parent_ids:
                failures.append(f"Strategy {strategy} must cover every source document.")
        if not queries or any("expected_parent_ids" not in query for query in queries):
            failures.append("Every query must define expected_parent_ids for strategy-neutral evaluation.")
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"Invalid Lab 07 asset: {error}")
    except (KeyError, TypeError, ValueError) as error:
        failures.append(f"Invalid chunk configuration: {error}")
    for source in (ROOT / "src").glob("*.py"):
        try:
            py_compile.compile(str(source), doraise=True)
        except py_compile.PyCompileError as error:
            failures.append(str(error))
    for variable in ("AZURE_SEARCH_ENDPOINT", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"):
        print(f"{variable} configured: {bool(os.getenv(variable))}")
    if failures:
        print("Preflight failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Preflight passed. Live service configuration may remain unset until provisioning.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())