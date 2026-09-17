from __future__ import annotations
from datetime import datetime
from enum import Enum 
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

class AgentName(str, Enum):
    SUMMARY = 'summary'
    EXPERIENCE = 'experience'
    PROJECTS = 'projects'
    EDUCATION = 'education'
    SKILLS = 'skills'
    MANAGER_REVIEWER = "manager_reviewer"
    MANAGER_EDITOR = "manager_editor"

class RevisionStatus(str, Enum):
    ACCEPTED = 'accepted'
    RETRY = 'retry'
    MAX_ITERATIONS = 'max_iterations_reached'
    REVIEWER_FAILED = 'reviewer_failed'
    WRITER_FAILED = 'writer_failed'
    BUDGET_EXHAUSTED = 'budget_exhausted'
    FAILED = 'failed'

class PipelineStatus(str, Enum):
    COMPLETED = 'completed'
    COMPLETED_DEGRADED = 'completed_degraded'
    NEEDS_MANUAL_REVIEW = 'needs_manual_review'
    FAILED = 'failed'
    BUDGET_EXHAUSTED = 'budget_exhausted'

class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens