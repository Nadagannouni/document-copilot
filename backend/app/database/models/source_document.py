from datetime import date
from uuid import UUID

from sqlalchemy import Date, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class SourceDocument(TimestampMixin, Base):
    __tablename__ = "source_documents"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    filing_type: Mapped[str] = mapped_column(String(20), nullable=False)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    accession_number: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default="{}",
    )

    chunks = relationship(
        "DocumentChunk",
        back_populates="source_document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )

    __table_args__ = (
        UniqueConstraint("accession_number", name="uq_source_documents_accession_number"),
        Index("ix_source_documents_ticker_fiscal_year", "ticker", "fiscal_year"),
    )
