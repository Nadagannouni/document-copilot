from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    chat_threads = relationship(
        "ChatThread",
        back_populates="user",
        cascade="all, delete-orphan",
    )
