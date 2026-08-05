from pydantic import BaseModel, HttpUrl
from typing import Optional


class JobUrl(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    source: str
    raw: Optional[dict] = None