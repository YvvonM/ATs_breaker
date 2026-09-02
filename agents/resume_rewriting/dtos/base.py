from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum 
from datetime import datetime

class AgentStatus(str, Enum):
    QUEUE = "queue"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentMetadata(BaseModel):
    model_used: str = Field(..., description="The model used for the agent's task.")
    execution_time: Optional[float] = Field(None, description="Time taken for the agent to complete its task in seconds.")
    token_count: Optional[int] = Field(None, description="Number of tokens used during the agent's execution.")
    status: AgentStatus = Field(default=AgentStatus.QUEUE, description="Current status of the agent's task.")
    started_at: Optional[datetime] = Field(None, description="Timestamp when the agent's task was started.")
    completed_at: Optional[datetime] = Field(None, description="Timestamp when the agent's task was completed.")


class BaseAgentOutput(BaseModel):
    content: Any = Field(..., description="The main content or output produced by the agent.")
    structured: Optional[Dict[str, Any]] = Field(None, description="Structured representation of the output, if applicable.")
    metadata: AgentMetadata = Field(..., description="Metadata related to the agent's execution and output.")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information related to the agent's task, if any.")