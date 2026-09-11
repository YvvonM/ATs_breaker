import os 
import sys 
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import Optional, List 
from datetime import datetime 
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from .config import PARSER_MODEL 
from .prompts import (
    EXPERIENCE_PARSER_SYSTEM_PROMPT,
    EXPERIENCE_PARSER_HUMAN_PROMPT
)
from dtos import ExperienceItem
from infrastructure.redis_service import redis_service

load_dotenv()

_parser_chain = None 

def _get_parser_chain(model: str):
    global _parser_chain
    if _parser_chain is None:
        llm = ChatGroq(
            model = model,
            api_key = os.getenv(""),
            temperature= 0.0
        )
        chain = ChatPromptTemplate.from_messages([
            ('system', EXPERIENCE_PARSER_SYSTEM_PROMPT),
            ('human', EXPERIENCE_PARSER_HUMAN_PROMPT)
        ])
        _parser_chain = chain| llm| JsonOutputParser()
        return _parser_chain

def parse_experience(experience_section:str, model: str = PARSER_MODEL,) -> List[ExperienceItem]:
        if not experience_section or experience_section.strip():
            raise ValueError("Experience section is empty")

        chain = _get_parser_chain(model)
        try:
            parsed = chain.invoke({'experience_section': experience_section})
        except Exception as e:
            raise RuntimeError(f"Experience parsing failed: {e}") from e

        raw_experiences = parsed.get('experience', [])
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
            if exp.get('company') or exp.get('title')
        ]
        return experiences

