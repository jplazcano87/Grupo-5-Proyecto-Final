from sqlalchemy.orm import relationship
from app import db

from flask_login import UserMixin

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from datetime import datetime, timezone

# print(username, email, password, repeat_password, birthdate, gender)


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    password = db.Column(db.Text, nullable=False)
    birthdate = db.Column(db.Text, nullable=False)
    gender = db.Column(db.Text, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now().date())

    messages = relationship("Message", back_populates="user")


class Message(db.Model):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    content = Column(Text, nullable=False)
    author = Column(String, nullable=False)  # 'user' or 'assistant'
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="messages")
