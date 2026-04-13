from datetime import datetime, timezone, date
from typing import Optional
from sqlmodel import SQLModel, Field 
import uuid
from sqlalchemy import Column, DateTime

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: uuid.UUID = Field(primary_key=True)
    email: str = Field(unique=True, nullable=False, index=True)
    role: str = Field(default="student")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))