from datetime import UTC, date, datetime

from flask_login import UserMixin
from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True)
    password: Mapped[str] = mapped_column(Text)  # bcrypt hash
    birthdate: Mapped[date] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=_utcnow)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="user", order_by="Message.id"
    )

    @property
    def age(self) -> int:
        today = date.today()
        years = today.year - self.birthdate.year
        if (today.month, today.day) < (self.birthdate.month, self.birthdate.day):
            years -= 1
        return years


class Message(db.Model):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=_utcnow)
    content: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String)  # 'user' or 'assistant'
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    user: Mapped["User"] = relationship(back_populates="messages")
