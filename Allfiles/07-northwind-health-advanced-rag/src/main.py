from __future__ import annotations

import argparse
import json
from pathlib import Path

from azure.identity import DefaultAzureCredential

from .chunking import generate_chunks
from .config import load_settings
from .embeddings import create_embedding_client
from .experiment import run_experiment
from .index_manager import create_or_update_indexes
from .ingest import upload_documents
from .router import route_query
from .search_pipeline import hybrid_semantic_search


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Northwind Health advanced RAG lab")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate-chunks")
    generate.add_argument("--source", type=Path, required=True)
    generate.add_argument("--strategies", type=Path, required=True)
    generate.add_argument("--output", type=Path, required=True)
    commands.add_parser("create-indexes")
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--documents", type=Path, required=True)
    search = commands.add_parser("search")
    search.add_argument("--query", required=True)
    search.add_argument("--mode", choices=("vector", "hybrid", "semantic"), default="hybrid")
    search.add_argument("--embedding-profile", choices=("baseline", "content-aware"), default="content-aware")
    search.add_argument(
        "--chunk-strategy",
        choices=("fixed-overlap", "structural-parent-child"),
        default="structural-parent-child",
    )
    compare = commands.add_parser("compare")
    compare.add_argument("--queries", type=Path, required=True)
    compare.add_argument("--documents", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "generate-chunks":
        result = generate_chunks(
            json.loads(args.source.read_text(encoding="utf-8")),
            json.loads(args.strategies.read_text(encoding="utf-8")),
        )
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return
    settings = load_settings()
    credential = DefaultAzureCredential()
    embedding_client = create_embedding_client(settings.openai_endpoint)
    if args.command == "create-indexes":
        result = create_or_update_indexes(settings.search_endpoint, credential, settings.vector_dimensions, settings.semantic_configuration)
    elif args.command == "ingest":
        documents = json.loads(args.documents.read_text(encoding="utf-8"))["chunks"]
        result = upload_documents(settings.search_endpoint, credential, embedding_client, settings.embedding_deployment, documents)
    elif args.command == "search":
        result = {}
        for index_name in route_query(args.query):
            result[index_name] = hybrid_semantic_search(
                settings.search_endpoint,
                index_name,
                credential,
                embedding_client,
                settings.embedding_deployment,
                settings.semantic_configuration,
                args.query,
                mode=args.mode,
                vector_field="optimized_vector" if args.embedding_profile == "content-aware" else "content_vector",
                filter_expression=f"chunk_strategy eq '{args.chunk_strategy}'",
            )
    else:
        result = run_experiment(
            settings.search_endpoint,
            credential,
            embedding_client,
            settings.embedding_deployment,
            settings.semantic_configuration,
            json.loads(args.queries.read_text(encoding="utf-8")),
            json.loads(args.documents.read_text(encoding="utf-8")),
        )
        args.output.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()