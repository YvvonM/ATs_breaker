from datetime import datetime 
from typing import Optional 
from uuid import UUID, uuid4 
from pydantic import BaseModel, HttpUrl, Field

class Company(BaseModel):
    id: UUID = Field(default_factory = uuid4)
    name:str 
    website: Optional[HttpUrl] = None
    careers_url: Optional[HttpUrl] = None
    linkedin_url: Optional[HttpUrl] = None
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    company_size: Optional[str] = None
    founded_year: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory = datetime.utcnow)
    updated_at: datetime = Field(default_factory = datetime.utcnow)