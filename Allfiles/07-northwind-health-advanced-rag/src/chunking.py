from __future__ import annotations

from typing import Any


def _fixed_overlap(document: dict[str, Any], configuration: dict[str, Any]) -> list[dict[str, Any]]:
    size = int(configuration["size_chars"])
    overlap = int(configuration["overlap_chars"])
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("fixed-overlap requires size_chars > overlap_chars >= 0")
    text = "\n\n".join(str(section["content"]) for section in document["sections"])
    chunks: list[dict[str, Any]] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(_chunk(document, configuration, text[start:end], len(chunks), start, end, None))
        if end == len(text):
            break
        start = end - overlap
    return chunks


def _structural_parent_child(document: dict[str, Any], configuration: dict[str, Any]) -> list[dict[str, Any]]:
    include_parent_title = bool(configuration.get("include_parent_title", True))
    chunks: list[dict[str, Any]] = []
    cursor = 0
    for section in document["sections"]:
        content = str(section["content"])
        start = cursor
        end = start + len(content)
        text = f"{document['title']}\n{section['heading']}\n{content}" if include_parent_title else content
        chunks.append(
            _chunk(
                document,
                configuration,
                text,
                len(chunks),
                start,
                end,
                str(section["heading"]),
            )
        )
        cursor = end + 2
    return chunks


def _chunk(
    document: dict[str, Any],
    configuration: dict[str, Any],
    content: str,
    order: int,
    start: int,
    end: int,
    section_heading: str | None,
) -> dict[str, Any]:
    strategy = str(configuration["strategy"])
    return {
        "id": f"{strategy}-{document['id']}-{order:03d}",
        "title": document["title"],
        "content": content,
        "category": document["category"],
        "source": document["source"],
        "parent_id": document["id"],
        "chunk_order": order,
        "chunk_strategy": strategy,
        "boundary_start": start,
        "boundary_end": end,
        "section_heading": section_heading,
    }


def generate_chunks(
    source_documents: list[dict[str, Any]],
    configurations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate comparable chunk sets from the same synthetic source documents."""
    handlers = {
        "fixed-overlap": _fixed_overlap,
        "structural-parent-child": _structural_parent_child,
    }
    chunks: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for configuration in configurations:
        strategy = str(configuration["strategy"])
        if strategy not in handlers:
            raise ValueError(f"Unknown chunk strategy: {strategy}")
        strategy_chunks: list[dict[str, Any]] = []
        for document in source_documents:
            strategy_chunks.extend(handlers[strategy](document, configuration))
        chunks.extend(strategy_chunks)
        summaries.append(
            {
                "strategy": strategy,
                "configuration": configuration,
                "chunk_count": len(strategy_chunks),
                "boundaries": [
                    {
                        "id": chunk["id"],
                        "parent_id": chunk["parent_id"],
                        "start": chunk["boundary_start"],
                        "end": chunk["boundary_end"],
                        "section_heading": chunk["section_heading"],
                    }
                    for chunk in strategy_chunks
                ],
            }
        )
    return {"strategy_summaries": summaries, "chunks": chunks}