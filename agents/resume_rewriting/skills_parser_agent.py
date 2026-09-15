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
    SKILLS_PARSER_SYSTEM_PROMPT,
    SKILLS_PARSER_HUMAN_PROMPT
)

from .dtos import SkillsStructured
from infrastructure.redis_service import redis_service

load_dotenv()

_parser_chain = None
def _get_parser_chain(model: str):
    global _parser_chain
    if _parser_chain is None:
        llm = ChatOpenAI(
                    model=model,
                    api_key=os.getenv("EXPEREINCE_PARSER"),
                    base_url="https://openrouter.ai/api/v1",
                    temperature=0.0
                )
        chain = ChatPromptTemplate.from_messages([
                    ('system', SKILLS_PARSER_SYSTEM_PROMPT),
                    ('human', SKILLS_PARSER_HUMAN_PROMPT)
                ])
        _parser_chain = chain | llm 
    return _parser_chain

def parse_skills(skills_section: str, model: str = PARSER_MODEL) -> SkillsStructured:
    if not skills_section or not skills_section.strip():
        raise ValueError("skills section is empty")

    chain = _get_parser_chain(model)
    try:
        raw_response = chain.invoke({'skills_section': skills_section})
    except Exception as e:
        raise RuntimeError(f"skills parsing failed: {e}") from e

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
    
    skills = SkillsStructured(
                categories=parsed.get("categories", {}),
                total_skills=parsed.get("total_skills", 0),
                keywords_matched=parsed.get("keywords_matched", []),
                keywords_missing=parsed.get("keywords_missing", []),            
            )
    
    return skills
