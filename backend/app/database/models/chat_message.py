from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin


class ChatMessage(CreatedAtMixin, Base):
    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_json: Mapped[dict | None] = mapped_column(JSONB)

    thread = relationship("ChatThread", back_populates="messages")
    citations = relationship(
        "MessageCitation",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="MessageCitation.citation_index",
    )

    __table_args__ = (
        Index("ix_chat_messages_thread_id_created_at", "thread_id", "created_at"),
    )
