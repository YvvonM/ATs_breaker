import os 
import sys 
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import Optional, List 
from datetime import datetime 
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from .config import PARSER_MODEL 
from .prompts import (
    PROJECT_PARSER_SYSTEM_PROMPT,
    PROJECT_PARSER_HUMAN_PROMPT
)
from .dtos import ProjectItem
from infrastructure.redis_service import redis_service

load_dotenv()

_parser_chain = None 

def _get_parser_chain(model:str):
    global _parser_chain
    if _parser_chain is None:
        llm = ChatOpenAI(
                    model=model,
                    api_key=os.getenv("EXPEREINCE_PARSER"),
                    base_url="https://openrouter.ai/api/v1",
                    temperature=0.0
                )
        chain = ChatPromptTemplate.from_messages([
                    ('system',PROJECT_PARSER_SYSTEM_PROMPT),
                    ('human', PROJECT_PARSER_HUMAN_PROMPT)
                ])
        _parser_chain = chain | llm 
    return _parser_chain

def parse_project(project_section:str, model:str = PARSER_MODEL) -> List[ProjectItem]:
    if not project_section or not project_section.strip():
        raise ValueError("project section is empty")
    chain = _get_parser_chain(model)
    try:
        raw_response = chain.invoke({'project_section': project_section})
    except Exception as e:
        raise RuntimeError(f"project parsing failed: {e}") from e
    
    print("\n" + "=" * 60)
    print("[DEBUG] Raw LLM response:")
    print("=" * 60)
    raw_text = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
    print(raw_text)
    print("=" * 60 + "\n")
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].rstrip()

    try:
        parsed = json.loads(cleaned)

    except json.JSONDecodeError as e:
        raise RuntimeError(
                    f"Failed to parse LLM JSON. Error: {e}\n\nRaw text was:\n{raw_text}"
                ) from e

    raw_projects = parsed.get("projects", [])
    if not isinstance(raw_projects, list):
        raise RuntimeError(f"LLM returned invalid 'projects' field: {type(raw_projects)}")

    projects = [
        ProjectItem(
            name= proj.get("name", ""),
            description= proj.get('description', ''),
            skills_demonstrated = proj.get('skills_demonstrated', []),
            achievements = proj.get('achievements', [])
        )
        for proj in raw_projects
        if proj.get("name") or proj.get("description")
    ]

    return projects
    