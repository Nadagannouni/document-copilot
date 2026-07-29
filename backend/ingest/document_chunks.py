from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import create_engine, delete, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.models.document_chunk import DocumentChunk
from app.database.models.message_citation import MessageCitation
from app.database.models.source_document import SourceDocument
from ingest.models import PreparedChunk, SourceDocumentRef
from ingest.settings import database_url


def fetch_source_documents(accession_numbers: Sequence[str]) -> dict[str, SourceDocumentRef]:
    engine = create_engine(database_url())
    with Session(engine) as session:
        rows = session.execute(
            select(SourceDocument.id, SourceDocument.accession_number).where(
                SourceDocument.accession_number.in_(accession_numbers)
            )
        ).all()
    return {
        accession_number: SourceDocumentRef(
            id=source_document_id,
            accession_number=accession_number,
        )
        for source_document_id, accession_number in rows
    }


def upsert_chunks(
    chunks: Sequence[PreparedChunk],
    embeddings: Sequence[Sequence[float]] | None,
) -> None:
    engine = create_engine(database_url())
    with Session(engine) as session:
        for index, chunk in enumerate(chunks):
            row = {
                "source_document_id": chunk.source_document_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "token_count": chunk.token_count,
                "embedding": embeddings[index] if embeddings is not None else None,
                "metadata_json": chunk.metadata,
            }
            statement = insert(DocumentChunk).values(row)
            update_values = {
                column.name: statement.excluded[column.name]
                for column in DocumentChunk.__table__.columns
                if column.name not in {"id", "created_at", "search_vector"}
            }
            session.execute(
                statement.on_conflict_do_update(
                    constraint="uq_document_chunks_source_document_id_chunk_index",
                    set_=update_values,
                )
            )
        session.commit()


def cleanup_stale_chunks(source_document_id: UUID, chunk_count: int) -> None:
    engine = create_engine(database_url())
    with Session(engine) as session:
        cited_chunk_exists = exists().where(
            MessageCitation.document_chunk_id == DocumentChunk.id
        )
        session.execute(
            delete(DocumentChunk).where(
                DocumentChunk.source_document_id == source_document_id,
                DocumentChunk.chunk_index >= chunk_count,
                ~cited_chunk_exists,
            )
        )
        session.commit()
