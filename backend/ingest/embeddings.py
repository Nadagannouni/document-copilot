from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from openai import AzureOpenAI, OpenAI

from app.config import settings
from ingest.models import PreparedChunk


def create_embedding_client() -> OpenAI | AzureOpenAI:
    if settings.openai_api_key.strip():
        return OpenAI(api_key=settings.openai_api_key)
    if settings.azure_openai_api_key.strip():
        return AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
    raise ValueError("Configure OPENAI_API_KEY or AZURE_OPENAI_API_KEY for embeddings.")


def embed_chunks(
    client: Any | None,
    chunks: Sequence[PreparedChunk],
    *,
    batch_size: int,
) -> list[list[float]]:
    if client is None:
        raise ValueError("OpenAI client is required when embeddings are enabled.")
    if batch_size < 1:
        raise ValueError("--batch-size must be greater than 0")

    embeddings: list[list[float]] = []
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        response = client.embeddings.create(
            input=[chunk.content for chunk in batch],
            model=settings.openai_embedding_model,
            dimensions=settings.openai_embedding_dimensions,
        )
        response_embeddings = [
            item.embedding for item in sorted(response.data, key=lambda item: item.index)
        ]
        for embedding in response_embeddings:
            if len(embedding) != settings.openai_embedding_dimensions:
                raise ValueError(
                    "Embedding dimension mismatch: expected "
                    f"{settings.openai_embedding_dimensions}, got {len(embedding)}."
                )
        embeddings.extend(response_embeddings)

    if len(embeddings) != len(chunks):
        raise ValueError(f"Expected {len(chunks)} embeddings, got {len(embeddings)}.")
    return embeddings
