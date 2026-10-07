from typing import Dict, List, Literal
from pydantic import BaseModel, Field


class Tier1ReviewerResponse(BaseModel):
    decision: Literal["accept", "retry"] = Field(
        ...,
        description="'accept' if the draft is good, 'retry' if it needs revision.",
    )
    scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Scores in [0,1] for: relevance, clarity, impact, keyword_coverage.",
    )
    feedback: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Feedback keyed by 'strengths', 'improvements', 'critical'.",
    )
    revision_notes: List[str] = Field(
        default_factory=list,
        description="Concrete fixes, max 5. Empty when decision='accept'.",
    )