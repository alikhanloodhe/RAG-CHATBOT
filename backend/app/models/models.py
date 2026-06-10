from datetime import datetime
from sqlalchemy import Column, String
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    """Database model representing an authenticated system user."""
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str = Field(sa_column=Column("password", String, nullable=False))

class UserDocument(SQLModel, table=True):
    """Database model representing document metadata records owned by a user."""
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id")
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="pending")  # pending, processing, completed, failed
    vector_count: int = Field(default=0)
