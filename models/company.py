from datetime import datetime 
from typing import Optional 
from uuid import UUID, uuid4 
from pydantic import field_validator, AnyUrl
from sqlmodel import SQLModel, Field

class Company(SQLModel, table = True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)
    website: Optional[str] = None
    careers_url: Optional[str] = None
    linkedin_url: Optional[str] = None

    industry: Optional[str] = None
    headquarters: Optional[str] = None
    company_size: Optional[str] = None
    founded_year: Optional[str] = None
    description: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("website", "careers_url", "linkedin_url")
    @classmethod
    def _validate_url_format(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        AnyUrl(value)
        return value