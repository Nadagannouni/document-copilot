"""create initial schema

Revision ID: 202607210001
Revises:
Create Date: 2026-07-21 00:01:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


revision: str = "202607210001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("create extension if not exists vector")
    op.execute("create extension if not exists pgcrypto")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "source_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("filing_type", sa.String(length=20), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("accession_number", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("accession_number", name="uq_source_documents_accession_number"),
    )

    op.create_table(
        "chat_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', content)", persisted=True),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_document_id",
            "chunk_index",
            name="uq_document_chunks_source_document_id_chunk_index",
        ),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["chat_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "message_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("citation_index", sa.Integer(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_chunk_id"], ["document_chunks.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_chat_threads_user_id_updated_at", "chat_threads", ["user_id", "updated_at"])
    op.create_index("ix_chat_messages_thread_id_created_at", "chat_messages", ["thread_id", "created_at"])
    op.create_index("ix_message_citations_message_id", "message_citations", ["message_id"])
    op.create_index("ix_message_citations_document_chunk_id", "message_citations", ["document_chunk_id"])
    op.create_index("ix_source_documents_ticker_fiscal_year", "source_documents", ["ticker", "fiscal_year"])
    op.create_index("ix_document_chunks_source_document_id", "document_chunks", ["source_document_id"])
    op.create_index(
        "ix_document_chunks_metadata",
        "document_chunks",
        ["metadata"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_document_chunks_search_vector",
        "document_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.execute(
        """
        create index ix_document_chunks_embedding_hnsw
        on document_chunks
        using hnsw (embedding vector_cosine_ops)
        where embedding is not null
        """
    )

    op.execute("alter table users enable row level security")
    op.execute("alter table chat_threads enable row level security")
    op.execute("alter table chat_messages enable row level security")
    op.execute("alter table message_citations enable row level security")
    op.execute("alter table source_documents enable row level security")
    op.execute("alter table document_chunks enable row level security")

    op.execute(
        """
        create policy users_own_rows
        on users
        for all
        to authenticated
        using (id = auth.uid())
        with check (id = auth.uid())
        """
    )
    op.execute(
        """
        create policy service_role_manage_users
        on users
        for all
        to service_role
        using (true)
        with check (true)
        """
    )
    op.execute(
        """
        create policy chat_threads_own_rows
        on chat_threads
        for all
        to authenticated
        using (user_id = auth.uid())
        with check (user_id = auth.uid())
        """
    )
    op.execute(
        """
        create policy service_role_manage_chat_threads
        on chat_threads
        for all
        to service_role
        using (true)
        with check (true)
        """
    )
    op.execute(
        """
        create policy chat_messages_own_thread_rows
        on chat_messages
        for all
        to authenticated
        using (
            exists (
                select 1
                from chat_threads
                where chat_threads.id = chat_messages.thread_id
                and chat_threads.user_id = auth.uid()
            )
        )
        with check (
            exists (
                select 1
                from chat_threads
                where chat_threads.id = chat_messages.thread_id
                and chat_threads.user_id = auth.uid()
            )
        )
        """
    )
    op.execute(
        """
        create policy service_role_manage_chat_messages
        on chat_messages
        for all
        to service_role
        using (true)
        with check (true)
        """
    )
    op.execute(
        """
        create policy message_citations_own_message_rows
        on message_citations
        for all
        to authenticated
        using (
            exists (
                select 1
                from chat_messages
                join chat_threads on chat_threads.id = chat_messages.thread_id
                where chat_messages.id = message_citations.message_id
                and chat_threads.user_id = auth.uid()
            )
        )
        with check (
            exists (
                select 1
                from chat_messages
                join chat_threads on chat_threads.id = chat_messages.thread_id
                where chat_messages.id = message_citations.message_id
                and chat_threads.user_id = auth.uid()
            )
        )
        """
    )
    op.execute(
        """
        create policy service_role_manage_message_citations
        on message_citations
        for all
        to service_role
        using (true)
        with check (true)
        """
    )
    op.execute(
        """
        create policy source_documents_authenticated_read
        on source_documents
        for select
        to authenticated
        using (true)
        """
    )
    op.execute(
        """
        create policy service_role_manage_source_documents
        on source_documents
        for all
        to service_role
        using (true)
        with check (true)
        """
    )
    op.execute(
        """
        create policy document_chunks_authenticated_read
        on document_chunks
        for select
        to authenticated
        using (true)
        """
    )
    op.execute(
        """
        create policy service_role_manage_document_chunks
        on document_chunks
        for all
        to service_role
        using (true)
        with check (true)
        """
    )


def downgrade() -> None:
    op.drop_table("message_citations")
    op.drop_table("chat_messages")
    op.drop_table("document_chunks")
    op.drop_table("chat_threads")
    op.drop_table("source_documents")
    op.drop_table("users")

    op.execute("drop extension if exists vector")
