from pydantic import field_validator, AnyUrl
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, JSON
from datetime import datetime
from typing import Optional


class JobUrl(SQLModel, table = True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    status: str = Field(
        default="pending",
        description="pending | extracted | failed",
    )
    extracted_job_id: Optional[UUID] = Field(default=None, foreign_key="job.id")
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    url: str = Field(unique=True, index=True)

    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    source: str
    raw: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    @field_validator("url")
    @classmethod
    def _validate_url_format(cls, value: str) -> str:
        AnyUrl(value)
        return value