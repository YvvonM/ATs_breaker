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

