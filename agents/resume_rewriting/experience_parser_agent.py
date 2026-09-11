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
    EXPERIENCE_PARSER_SYSTEM_PROMPT,
    EXPERIENCE_PARSER_HUMAN_PROMPT
)
from .dtos import ExperienceItem
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
            ('system', EXPERIENCE_PARSER_SYSTEM_PROMPT),
            ('human', EXPERIENCE_PARSER_HUMAN_PROMPT)
        ])
        _parser_chain = chain | llm 
    return _parser_chain

def parse_experience(experience_section: str, model: str = PARSER_MODEL) -> List[ExperienceItem]:
    if not experience_section or not experience_section.strip():
        raise ValueError("Experience section is empty")

    chain = _get_parser_chain(model)
    try:
        raw_response = chain.invoke({'experience_section': experience_section})
    except Exception as e:
        raise RuntimeError(f"Experience parsing failed: {e}") from e

    print("\n" + "=" * 60)
    print("[DEBUG] Raw LLM response:")
    print("=" * 60)
    raw_text = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
    print(raw_text)
    print("=" * 60 + "\n")

    cleaned = raw_text.strip()

    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = cleaned.find("\n")
        cleaned = cleaned[first_newline + 1:]
        # Remove closing fence
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].rstrip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Failed to parse LLM JSON. Error: {e}\n\nRaw text was:\n{raw_text}"
        ) from e

    raw_experiences = parsed.get("experiences", [])
    if not isinstance(raw_experiences, list):
        raise RuntimeError(f"LLM returned invalid 'experiences' field: {type(raw_experiences)}")

    experiences = [
        ExperienceItem(
            company=exp.get("company", ""),
            title=exp.get("title", ""),
            duration=exp.get("duration", ""),
            location=exp.get("location"),
            bullet_points=exp.get("bullet_points", []),
            skills_demonstrated=exp.get("skills_demonstrated", []),
        )
        for exp in raw_experiences
        if exp.get("company") or exp.get("title")
    ]

    return experiences