import uuid
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import ClassVar

from pydantic import BaseModel, EmailStr, HttpUrl
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


class PreviewRequest(BaseModel):
    callback_url: HttpUrl


class UserRole(str, Enum):
    member = "member"
    staff = "staff"


class Scope(StrEnum):
    """Permission vocabulary. Roles are mapped to scopes in ``app.api.deps.ROLE_SCOPES``."""

    records_read = "records:read"
    records_read_any = "records:read:any"  # cross-owner read of records and their notes
    webhooks_preview = "webhooks:preview"
    staff = "role:staff"


@dataclass(frozen=True)
class Access:
    """What a caller needs in order to see or change values of the annotated type.

    Declared on models as ``__access__``. Loaders in ``app.api.deps`` (``Owned``,
    ``AnyOwner``, ``OwnedQuery``) derive the owner filter and the scope check from
    it; ``PolicyRouter`` checks that a route's response type never needs more than
    the route's signature grants.
    """

    read: Scope
    write: Scope | None = None  # None: the type is never written through the API
    owner_field: str | None = None  # column holding the owning user's id
    read_any: Scope | None = None  # None: rows can never be widened past the owner


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


RECORD_ACCESS = Access(
    read=Scope.records_read,
    owner_field="user_id",
    read_any=Scope.records_read_any,
)


class RecordBase(SQLModel):
    __access__: ClassVar[Access] = RECORD_ACCESS

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
    __access__: ClassVar[Access] = RECORD_ACCESS

    data: list[RecordPublic]
    count: int


# A note is visible exactly when its record is, so notes share the record's access.
class RecordNoteBase(SQLModel):
    __access__: ClassVar[Access] = RECORD_ACCESS

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
    __access__: ClassVar[Access] = RECORD_ACCESS

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
