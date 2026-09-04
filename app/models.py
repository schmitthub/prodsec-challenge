import uuid
from enum import Enum

from pydantic import BaseModel, EmailStr, HttpUrl
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


class PreviewRequest(BaseModel):
    callback_url: HttpUrl


class UserRole(str, Enum):
    member = "member"
    staff = "staff"


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    role: str = Field(default=UserRole.member, max_length=50)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    records: list["Record"] = Relationship(back_populates="user", cascade_delete=True)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class RecordType(str, Enum):
    lab_result = "lab_result"


class RecordStatus(str, Enum):
    released = "released"


class RecordBase(SQLModel):
    type: RecordType
    summary: str | None = Field(default=None, max_length=255)
    status: RecordStatus


class RecordCreate(RecordBase):
    pass


class Record(RecordBase, table=True):
    __table_args__ = (
        UniqueConstraint("user_id", "summary", name="unique_user_record_summary"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    user: User | None = Relationship(back_populates="records")
    notes: list["RecordNote"] = Relationship(
        back_populates="record", cascade_delete=True
    )


class RecordPublic(RecordBase):
    id: uuid.UUID
    user_id: uuid.UUID


class RecordsPublic(SQLModel):
    data: list[RecordPublic]
    count: int


class RecordNoteBase(SQLModel):
    note: str = Field(max_length=255)


class RecordNoteCreate(RecordNoteBase):
    pass


class RecordNote(RecordNoteBase, table=True):
    __table_args__ = (UniqueConstraint("record_id", "note", name="unique_record_note"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    record_id: uuid.UUID = Field(
        foreign_key="record.id", nullable=False, ondelete="CASCADE"
    )
    record: Record | None = Relationship(back_populates="notes")


class RecordNotePublic(RecordNoteBase):
    id: uuid.UUID
    record_id: uuid.UUID


class RecordNotesPublic(SQLModel):
    record_id: uuid.UUID
    data: list[RecordNotePublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# OAuth2 token response (RFC 6749 §5.1)
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None
