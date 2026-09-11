import re 
import os 
import json 
import traceback
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import Optional, List 
from datetime import datetime 
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from .config import MODEL
from .prompts import (
    EXPERIENCE_SYSTEM_PROMPT,
    EXPERIENCE_HUMAN_PROMPT,
)
from .dtos import (
    ExperienceAgentOutput,
    ExperienceStructured,
    ExperienceItem,
    AgentMetadata,
)
from infrastructure.redis_service import redis_service
load_dotenv()

EXPERIENCE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ('system', EXPERIENCE_SYSTEM_PROMPT),
        ('human', EXPERIENCE_HUMAN_PROMPT)
    ]
)

class ExperienceAgent:
    def __init__(self, model: str = MODEL,api_key: str = None ):
        self.model = model
        self._llm = ChatGroq(
            model=self.model,
            api_key=api_key or os.getenv("GROQ_API_KEY"),
            temperature=0.3,  
        )
        self._chain = EXPERIENCE_PROMPT|self._llm| JsonOutputParser()
        self._redis = redis_service


    def process(self, 
    job_description:str, 
    experience_section:str, 
    keywords: List[str], 
    run_id: Optional[str] = None, 
    must_have:Optional[List[str]] = None,
    nice_to_have:Optional[List[str]] = None
    ) -> ExperienceAgentOutput:
        start_time = datetime.now()
        if not job_description or not job_description.strip():
            return self._create_error_dto(
                "Job description is empty or invalid.",
                start_time
            )

        if not experience_section or not experience_section.strip():
            return self._create_error_dto(
                "Experience section is empty or invalid.",
                start_time
            )

        if run_id is None:
            run_id = self._redis.get_run_id()

        self._redis.set_job_status(run_id, "processing", "Experience agent started")
        try:
            parsed_experiences = self._parse_experience_section(experience_section)
            if not parsed_experiences:
                return self._create_error_dto(
                    "Could not parse any experiences from the experience section.",
                    start_time,
                    run_id
                )
            must_have_str = ", ".join(must_have) if must_have else "None specified"
            nice_to_have_str = ", ".join(nice_to_have) if nice_to_have else "None specified"
            keywords_str = ", ".join(keywords) if keywords else "No keywords provided"

            print(f"Calling LLM to rewrite experience section...")
            parsed = self._chain.invoke({
                "job_description": job_description,
                "experience_section": experience_section,
                "keywords": keywords_str,
                "must_have": must_have_str,
                "nice_to_have": nice_to_have_str,
            })
            experiences = []
            for exp in parsed.get("experiences", []):
                experiences.append(
                    ExperienceItem(
                        company=exp.get("company", ""),
                        title=exp.get("title", ""),
                        duration=exp.get("duration", ""),
                        location=exp.get("location"),
                        bullet_points=exp.get("bullet_points", []),
                        skills_demonstrated=exp.get("skills_demonstrated", [])
                    )
                )

            keyword_usage = parsed.get("keyword_usage", {})
            structured = ExperienceStructured(
                experiences=experiences,
                total_experiences=len(experiences),
                total_bullet_points=parsed.get("total_bullet_points", 0),
                skills_used=parsed.get("skills_used", []),
                keywords_matched=keyword_usage.get("keywords_incorporated", []),
                keywords_missing=keyword_usage.get("keywords_missing", []),
                match_score=parsed.get("match_score", 0.0)
            )

            content = self._generate_markdown(experiences)

            dto = ExperienceAgentOutput(
                content=content,
                structured=structured,
                metadata=AgentMetadata(
                    model_used=self.model,
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    token_count=0, 
                    status="completed",
                    started_at=start_time,
                    completed_at=datetime.now()
                ),
                error=None
            )
            self._store_dto(run_id, dto)
            print(f"Experience agent completed: {len(experiences)} experiences, {structured.total_bullet_points} bullet points")
            return dto
        except Exception as e:
            error_msg = f"Error during experience rewriting: {str(e)}"
            return self._create_error_dto(error_msg, start_time, run_id)


    def _parse_experience_section(self, experience_section: str) -> List[dict]:
        experiences = []
        
        if not experience_section:
            return experiences
        lines = experience_section.strip().split('\n')
        current_exp = None
        bullet_points = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if ('**' in line or '|' in line) and not line.startswith('-') and not line.startswith('*'):
                if current_exp and bullet_points:
                    current_exp['bullet_points'] = bullet_points
                    experiences.append(current_exp)
                    bullet_points = []

                current_exp = self._parse_header(line)

            elif line.startswith('- ') or line.startswith('• ') or line.startswith('* '):
                bullet = line[2:].strip() if line.startswith('- ') or line.startswith('• ') else line[2:].strip()
                if bullet:
                    bullet_points.append(bullet)

            elif current_exp and not line.startswith('-') and not line.startswith('*'):
                if '|' in line or '*' in line:
                    self._parse_header_details(current_exp, line)
        if current_exp and bullet_points:
            current_exp['bullet_points'] = bullet_points
            experiences.append(current_exp)
        
        return experiences


    def _parse_header(self, header: str) -> dict:
        exp = {
            "company": "",
            "title": "",
            "duration": "",
            "location": "",
            "bullet_points": []
        }
        
        match = re.search(r'\*\*(.+?)\*\*\s*\|\s*(.+?)(?:\n|$)', header)
        if match:
            exp['title'] = match.group(1).strip()
            exp['company'] = match.group(2).strip()
            return exp
        
        match = re.search(r'(.+?)\s*[-–]\s*(.+?)(?:\n|$)', header)
        if match:
            exp['company'] = match.group(1).strip()
            exp['title'] = match.group(2).strip()
            return exp

        match = re.search(r'(.+?)\s+at\s+(.+?)(?:\n|$)', header, re.IGNORECASE)
        if match:
            exp['title'] = match.group(1).strip()
            exp['company'] = match.group(2).strip()
            return exp
        
        exp['title'] = header.strip()
        return exp

    def _parse_header_details(self, exp: dict, line: str):
        match = re.search(r'\*([^*]+)\*', line)
        if match:
            details = match.group(1).strip()
            if '|' in details:
                parts = details.split('|')
                exp['duration'] = parts[0].strip()
                if len(parts) > 1:
                    exp['location'] = parts[1].strip()
            else:
                exp['duration'] = details

    def _generate_markdown(self, experiences: List[ExperienceItem]) -> str:
        if not experiences:
            return ""
        
        markdown = "### Professional Experience\n\n"
        for exp in experiences:
            markdown += f"**{exp.title}** | {exp.company}\n"
            duration_line = f"*{exp.duration}"
            if exp.location:
                duration_line += f" | {exp.location}"
            duration_line += "*\n"
            markdown += duration_line
            for bullet in exp.bullet_points:
                markdown += f"- {bullet}\n"
            
            markdown += "\n"
        
        return markdown

    def _store_dto(self, run_id: str, dto: ExperienceAgentOutput) -> None:
        """Store DTO in Redis."""
        self._redis.store_job_data(run_id, "experience_agent_output", dto.model_dump())
        self._redis.store_job_data(run_id, "experience_section", dto.content)
        self._redis.store_job_data(run_id, "experience_match_score", dto.structured.match_score)
        self._redis.set_job_status(
            run_id,
            "completed",
            f"Experience agent completed: {dto.structured.total_experiences} experiences"
        )
        print(f"Stored experience DTO in Redis")


    def _create_error_dto(
        self,
        error_msg: str,
        start_time: datetime,
        run_id: Optional[str] = None
    ) -> ExperienceAgentOutput:
        if run_id:
            self._redis.set_job_status(run_id, "failed", error_msg)
        return ExperienceAgentOutput(
            content="",
            structured=ExperienceStructured(
                experiences=[],
                total_experiences=0,
                total_bullet_points=0,
                skills_used=[],
                keywords_matched=[],
                keywords_missing=[],
                match_score=0.0
            ),
            metadata=AgentMetadata(
                model_used=self.model,
                execution_time=(datetime.now() - start_time).total_seconds(),
                token_count=0,
                status="failed",
                started_at=start_time,
                completed_at=datetime.now()
            ),
            error={
            "message": error_msg
        }
        )


def process_experience(
    job_description: str,
    experience_section: str,
    keywords: List[str],
    run_id: Optional[str] = None,
    must_have: Optional[List[str]] = None,
    nice_to_have: Optional[List[str]] = None,
    model: str = MODEL
) -> ExperienceAgentOutput:
    agent = ExperienceAgent(model=model)
    return agent.process(
        job_description=job_description,
        experience_section=experience_section,
        keywords=keywords,
        run_id=run_id,
        must_have=must_have,
        nice_to_have=nice_to_have,
    )