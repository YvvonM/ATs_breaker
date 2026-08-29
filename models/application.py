from datetime import datetime 
from pydantic import BaseModel, Field
from uuid import UUID, uuid4 
from typing import Optional 

class Application(BaseModel):
    id: UUID = Field(default_factory = uuid4)
    job_id: UUID 
    company_id: UUID 
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    status: str = "Not Applied"
    applied_at: Optional[datetime] = None
    last_updated: datetime = Field(
        default_factory = datetime.utcnow
    )
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    interview_date: Optional[datetime] = None
    notes: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    offer_received: bool = False
    accepted: bool = False