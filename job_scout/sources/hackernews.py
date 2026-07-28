import asyncio 
import re 
import json 
from datetime import datetime, timezone 
from typing import Optional, List 
from job_scout.models import JobListing, JobSource
from job_scout.crawler import Crawler
from job_scout.config import ScoutConfig
from .key_words import AI_KEYWORDS, EXTRACTION_PROMPT
from langchain_groq import ChatGroq 
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os 
from dotenv import load_dotenv
load_dotenv()

class KeyRotator:
    def __init__(self, keys: List[str], questions_per_key: int = 2):
        if not keys:
            raise ValueError("No API keys provided.")
        self.keys = keys
        self.questions_per_key = questions_per_key
        self._index = 0
        self._count = 0
    @property
    def current_key(self) -> str:
        return self.keys[self._index]

    def advance(self):
        """Call after each question is answered."""
        self._count += 1
        if self._count >= self.questions_per_key:
            self._count = 0
            self._index = (self._index + 1) % len(self.keys)
            print(f"[KeyRotator] Switched to key index {self._index}")

    def get_and_advance(self) -> str:
        """Return the current key, then advance the counter."""
        key = self.current_key
        self.advance()
        return key

rotator = KeyRotator(
    keys=[
        k for k in [
            os.getenv("Y_GROQ"),
            os.getenv("J_GROQ"),
            os.getenv("GROQ_API_KEY"),   
        ]
        if k  
    ],
    questions_per_key=2,
)

def _get_llm() -> ChatGroq:
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=rotator.get_and_advance(),
        temperature=0.0,
        #reasoning_format="hidden",
    )

_extraction_prompt = ChatPromptTemplate.from_messages(
    [
        ('system', EXTRACTION_PROMPT),
        ('human', '{text}')
    ]
)

def _clean_hn_text(raw: str) -> str:
    text = raw.replace("<p>", "\n\n").replace("</p>", "")
    text = re.sub(r'<a href="([^"]+)">[^<]+</a>', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


class LLMExtractor:
    def __init__(self):
        pass

    async def _extract(self, text:str) -> dict:
        chain = _extraction_prompt | _get_llm() 
        result = await chain.ainvoke({'text':text})
        if hasattr(result, "content"):
            raw_output = result.content
        else:
            raw_output = str(result)
        print("-" * 40)
        print(f"RAW LLM OUTPUT: {repr(raw_output[:500])}")
        print("-" * 40)
    
        if not raw_output or not raw_output.strip():
            print("WARNING: LLM returned empty output")
            return {}
        raw_output = raw_output.strip()
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:]
        if raw_output.startswith("```"):
            raw_output = raw_output[3:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip()
        
        try:
            return json.loads(raw_output)
        except json.JSONDecodeError as e:
            print(f"WARNING: Failed to parse JSON: {e}")
            print(f"Raw output: {raw_output[:500]}")
            return {}

    
class HNScraper:
    def __init__(self, config: Optional[ScoutConfig] = None):
        self.config = config or ScoutConfig()
        self.extractor = LLMExtractor()
        self.keywords = AI_KEYWORDS

    def _is_ai_role(self, text:str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in AI_KEYWORDS)

    async def _find_latest_thread(self, crawler: Crawler) -> Optional[int]:
        result = await crawler.fetch_json(self.config.hn.WHO_IS_HIRING_QUERY_URL)
        if not result.ok or not result.json_data:
            return None 

        for hit in result.json_data.get("hits", []):
            if "who is hiring" in hit.get("title", "").lower():
                return hit.get("objectID")
            return None

        
    async def _fetch_comments(self, crawler: Crawler, thread_id: int) -> List[dict]:
        result = await crawler.fetch_json(self.config.hn.ITEM_API_URL.format(thread_id))
        if not result.ok or not result.json_data:
            return []

        kids = result.json_data.get("kids", [])
        comments = []
        for kid_id in kids:
            kid_result = await crawler.fetch_json(self.config.hn.ITEM_API_URL.format(kid_id))
            if kid_result.ok and kid_result.json_data:
                comments.append(kid_result.json_data)

        return comments

    async def _parse_comment(self, comment: dict, thread_id: int) -> Optional[JobListing]:
        raw_text = comment.get("text", "")
        if not raw_text:
            return None 

        text = _clean_hn_text(raw_text)
        if not self._is_ai_role(text):
            return None 

        extracted = await self.extractor._extract(text)
        print("*"*50)
        print(extracted)
        print("*"*50)
        comment_id = comment.get("id", 0)
        posted_at = datetime.fromtimestamp(comment.get("time", 0), tz=timezone.utc)
        return JobListing(
                id=f"hn-{thread_id}-{comment_id}",
                source=JobSource.HACKER_NEWS,
                title=extracted.get("role_title") or text.splitlines()[0][:100],
                company=extracted.get("company"),
                location=extracted.get("location"),
                description=extracted.get("description_summary") or text[:500],
                url=f"https://news.ycombinator.com/item?id={comment_id}",
                posted_at=posted_at,
                raw_text=text,
                is_remote=extracted.get("is_remote", False),
                tags=[t for t in extracted.get("tech_stack", []) if t] if extracted.get("tech_stack") else [],
                salary=extracted.get("salary_range"),
            )

    async def scrape(self) -> List[JobListing]:
        async with Crawler() as crawler:
            crawler.set_domain_rate("hn.algolia.com", 0.5)
            crawler.set_domain_rate("hacker-news.firebaseio.com", 0.3)
            thread_id = await self._find_latest_thread(crawler)
            if not thread_id:
                print("No 'Who is Hiring' thread found")
                return []

            print(f"Found HN thread: {thread_id}")
            comments = await self._fetch_comments(crawler, thread_id)
            print(f"Fetched {len(comments)} comments")
            listings = []
            for i, comment in enumerate(comments):
                listing = await self._parse_comment(comment, thread_id)
                if listing:
                    listings.append(listing)
                if (i + 1) % 10 == 0:
                    print(f"  Processed {i + 1}/{len(comments)} comments...")

            print(f"Found {len(listings)} AI/ML roles")
            return listings


async def main():
    scraper = HNScraper()
    jobs = await scraper.scrape()

    print(f"\n{'='*60}")
    print(f"Total jobs: {len(jobs)}")
    print(f"{'='*60}")

    for job in jobs[:5]:
        print(f"\n--- {job.title} ---")
        print(f"Company: {job.company}")
        print(f"Location: {job.location}")
        print(f"Remote: {job.is_remote}")
        print(f"Tags: {job.tags}")
        print(f"Salary: {job.salary}")
        print(f"Description: {job.description}")
        print(f"URL: {job.url}")


if __name__ == "__main__":
    asyncio.run(main())

        





    