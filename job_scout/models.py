from dataclasses import dataclass
from datetime import datetime 
from typing import List, Optional
from enum import Enum, auto

class JobSource(Enum):
    HACKER_NEWS = auto()
    INDEED = auto()
    GOOGLE_JOBS = auto()
    WELLFOUND = auto()

@dataclass(frozen=True)
class JobListing:
    id: str
    source: JobSource 
    title: str 
    company: Optional[str]
    location: Optional[str]
    description: Optional[str]
    url: Optional[str]
    posted_at: Optional[datetime]
    raw_text: str 
    salary: Optional[str] = None
    is_remote: Optional[bool] = None
    tags: List[str] = None  

    def __post_init__(self):
            if self.tags is None:
                object.__setattr__(self, 'tags', [])