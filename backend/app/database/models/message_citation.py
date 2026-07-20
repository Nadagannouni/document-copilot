from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin


class MessageCitation(CreatedAtMixin, Base):
    __tablename__ = "message_citations"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    citation_index: Mapped[int] = mapped_column(Integer, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default="{}",
    )

    message = relationship("ChatMessage", back_populates="citations")
    document_chunk = relationship("DocumentChunk", back_populates="citations")

    __table_args__ = (
        Index("ix_message_citations_message_id", "message_id"),
        Index("ix_message_citations_document_chunk_id", "document_chunk_id"),
    )
