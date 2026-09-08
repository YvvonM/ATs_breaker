import json 
from typing import Optional, List, Dict, Any, Type, TypeVar, Union
from datetime import datetime 
from uuid import UUID, uuid4
from pydantic import BaseModel
from .keyword_dto import KeywordAgentOutput
from .education_dto import EducationAgentOutput
from .experience_dto import ExperienceAgentOutput
from .summary_dto import SummaryAgentOutput
from .skills_dto import SkillsAgentOutput
from .project_dto import ProjectsAgentOutput
from .manager_dto import ManagerAgentOutput
from .humanizer_dto import HumanizerAgentOutput
from .cv_generation_dto import AllAgentsOutputs

AgentOutputType = Union[
    KeywordAgentOutput,
    EducationAgentOutput,
    ExperienceAgentOutput,
    SummaryAgentOutput,
    SkillsAgentOutput,
    ProjectsAgentOutput,
    ManagerAgentOutput,
    HumanizerAgentOutput,
    AllAgentsOutputs
]

AGENT_DTO_MAP = {
    'keyword_agent': KeywordAgentOutput,
    'experience_agent': ExperienceAgentOutput,
    'education_agent': EducationAgentOutput,
    'summary_agent': SummaryAgentOutput,
    'skills_agent': SkillsAgentOutput,
    'projects_agent': ProjectsAgentOutput,
    'manager_agent' : ManagerAgentOutput,
    'humanizer_agent': HumanizerAgentOutput
}

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()

        if isinstance(obj, UUID):
            return str(obj)

        return super().default(obj)


def serialize_to_json(data: Any) -> str:
    if isinstance(data, BaseModel):
        data = data.model_dump()
        return json.dumps(data, cls = DateTimeEncoder)


def deserialize_from_json(json_str: str, model_class: Type[BaseModel]) -> BaseModel:
    data = json.loads(json_str)
    return model_class(**data)

def serialize_agent_output(agent_name: str, output: AgentOutputType) -> str:
    if not isinstance(output, BaseModel):
        raise ValueError(f"Output must be a Pydantic model, got {type(output)}")
    return serialize_to_json(output)

def deserialize_agent_output(agent_name: str, json_str: str) -> Optional[AgentOutputType]:
    if not json_str:
        return None

    dto_class = AGENT_DTO_MAP.get(agent_name)
    if not dto_class:
        return ValueError(f"Unknown agent name: {agent_name}")

    return deserialize_from_json(json_str, dto_class)

def serialize_all_agent_outputs(outputs: AllAgentsOutputs) -> str:
    return serialize_to_json(outputs)

def deserialize_all_agent_outputs(json_str: str) -> Optional[AllAgentsOutputs]:
    if not json_str:
        return None

    data = json.loads(json_str)
    agent_outputs = {}
    for agent_name, dto_class in AGENT_DTO_MAP.items():
        if agent_name in data and data[agent_name] is not None:
            agent_outputs[agent_name] = dto_class(**data[agent_name])

        else:
            agent_outputs[agent_name] = None

    return AllAgentsOutputs(**agent_outputs)

def update_agent_output_in_db(current_agent_outputs: Optional[str], agent_name: str, new_output: AgentOutputType) -> str:
    if current_agent_outputs:
        try:
            output_dict = json.loads(current_agent_outputs)

        except json.JSONDecodeError:
            output_dict = {}

    else:
        output_dict = {}

    output_dict[agent_name] = new_output.model_dump()
    return json.dumps(output_dict, cls=DateTimeEncoder)

def get_agent_output_from_db(agent_output_json: Optional[str], agent_name: str) -> Optional[AgentOutputType]:
    if not agent_output_json:
        return None 

    try:
        output_dict = json.loads(agent_output_json)

    except json.JSONDecodeError:
        return None 

    agent_data = output_dict.get(agent_name)
    if not agent_data:
        return None

    dto_class = AGENT_DTO_MAP.get(agent_name)
    if not dto_class:
        return None 

    return dto_class(**agent_data)

def extract_keywords_from_db(agent_outputs_json: Optional[str]) -> Optional[list]:
    """
    Helper to quickly extract keywords from the agent_outputs JSON.
    """
    if not agent_outputs_json:
        return None
    
    try:
        outputs_dict = json.loads(agent_outputs_json)
        keyword_data = outputs_dict.get("keyword_agent", {})
        structured = keyword_data.get("structured", {})
        return structured.get("flat_keywords", [])
    except (json.JSONDecodeError, KeyError, AttributeError):
        return None

def extract_section_from_db(
    agent_outputs_json: Optional[str],
    agent_name: str
) -> Optional[str]:
    """
    Helper to extract section content from a specific agent's output.
    """
    if not agent_outputs_json:
        return None
    
    try:
        outputs_dict = json.loads(agent_outputs_json)
        agent_data = outputs_dict.get(agent_name, {})
        return agent_data.get("content")
    except (json.JSONDecodeError, KeyError, AttributeError):
        return None

def extract_match_score_from_db(agent_outputs_json: Optional[str]) -> Optional[float]:
    """
    Helper to extract the match score from the manager agent's output.
    """
    if not agent_outputs_json:
        return None
    
    try:
        outputs_dict = json.loads(agent_outputs_json)
        manager_data = outputs_dict.get("manager_agent", {})
        structured = manager_data.get("structured", {})
        return structured.get("final_score")
    except (json.JSONDecodeError, KeyError, AttributeError):
        return None

def get_all_sections_from_db(agent_outputs_json: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Get all resume sections from agent outputs.
    """
    if not agent_outputs_json:
        return {}
    
    sections = {}
    section_agents = [
        "experience_agent",
        "education_agent", 
        "summary_agent",
        "skills_agent",
        "projects_agent"
    ]
    
    for agent_name in section_agents:
        sections[agent_name.replace("_agent", "_section")] = extract_section_from_db(
            agent_outputs_json, agent_name
        )
    
    return sections

def create_agent_output_summary(agent_outputs_json: Optional[str]) -> Dict[str, Any]:
    """
    Create a summary of all agent outputs with key metrics.
    """
    if not agent_outputs_json:
        return {"error": "No agent outputs found"}
    
    try:
        outputs_dict = json.loads(agent_outputs_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON"}
    
    summary = {
        "total_agents": 0,
        "completed_agents": 0,
        "failed_agents": 0,
        "processing_agents": 0,
        "total_execution_time": 0,
        "total_tokens": 0,
        "models_used": set(),
        "keywords_found": 0,
        "overall_score": None,
        "agent_statuses": {}
    }
    
    for agent_name, agent_data in outputs_dict.items():
        if not agent_data:
            continue
        
        summary["total_agents"] += 1
        status = agent_data.get("metadata", {}).get("status", "unknown")
        summary["agent_statuses"][agent_name] = status
        
        if status == "completed":
            summary["completed_agents"] += 1
        elif status == "failed":
            summary["failed_agents"] += 1
        elif status == "processing":
            summary["processing_agents"] += 1
        
        # Collect metrics
        metadata = agent_data.get("metadata", {})
        execution_time = metadata.get("execution_time", 0)
        if execution_time:
            summary["total_execution_time"] += execution_time
        
        token_count = metadata.get("token_count", 0)
        if token_count:
            summary["total_tokens"] += token_count
        
        model_used = metadata.get("model_used")
        if model_used:
            summary["models_used"].add(model_used)
        
        # Get keyword count from keyword agent
        if agent_name == "keyword_agent":
            structured = agent_data.get("structured", {})
            summary["keywords_found"] = structured.get("keyword_count", 0)
        
        # Get overall score from manager agent
        if agent_name == "manager_agent":
            structured = agent_data.get("structured", {})
            summary["overall_score"] = structured.get("final_score")
    
    summary["models_used"] = list(summary["models_used"])
    return summary

def validate_agent_output(agent_name: str, data: dict) -> bool:
    """
    Validate that the data matches the expected DTO for the agent.
    """
    dto_class = AGENT_DTO_MAP.get(agent_name)
    if not dto_class:
        return False
    
    try:
        dto_class(**data)
        return True
    except Exception:
        return False

def merge_agent_outputs(
    existing_json: Optional[str],
    new_outputs: Dict[str, AgentOutputType]
) -> str:
    """
    Merge multiple agent outputs into the existing agent_outputs JSON.
    """
    # Parse existing outputs
    if existing_json:
        try:
            outputs_dict = json.loads(existing_json)
        except json.JSONDecodeError:
            outputs_dict = {}
    else:
        outputs_dict = {}
    
    # Add/update new outputs
    for agent_name, output in new_outputs.items():
        if isinstance(output, BaseModel):
            outputs_dict[agent_name] = output.model_dump()
        else:
            outputs_dict[agent_name] = output
    
    return json.dumps(outputs_dict, cls=DateTimeEncoder)
