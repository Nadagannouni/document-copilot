from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin


EMBEDDING_DIMENSIONS = 1536


class DocumentChunk(CreatedAtMixin, Base):
    __tablename__ = "document_chunks"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    search_vector = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True),
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default="{}",
    )

    source_document = relationship("SourceDocument", back_populates="chunks")
    citations = relationship("MessageCitation", back_populates="document_chunk")

    __table_args__ = (
        UniqueConstraint(
            "source_document_id",
            "chunk_index",
            name="uq_document_chunks_source_document_id_chunk_index",
        ),
        Index("ix_document_chunks_source_document_id", "source_document_id"),
    )
