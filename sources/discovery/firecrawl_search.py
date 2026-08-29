import os 
import httpx 
from typing import Optional, List 
from models.job_url import JobUrl
from sources.base import DiscoverySource
from dotenv import load_dotenv
load_dotenv()

class FirecrawlSearchDiscovery(DiscoverySource):
    BASE_URL = "https://api.firecrawl.dev/v1/search"

    
    def __init__(self):
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError("Firecrawl Search requires FIRECRAWL_API_KEY")

    @property 
    def name(self) -> str:
        return "firecrawl_search"
    

    async def discover(self, query:str, limit: int = 10, lang: str = 'en', country: str = "us", **kwargs) -> List[JobUrl]:
        payload = {
            "query": query,
            "limit": limit,
            "lang": lang,
            "country": country,
            "scrapeOptions": {"formats": ["url"]}
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout = 60) as client:
            response = await client.post(self.BASE_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                raise RuntimeError(f"Firecrawl search failed: {data.get('error', 'unknown')}")

            discovered: List[JobUrl] = []
            for result in data.get("data", []):
                url = result.get("url") or result.get("metadata", {}).get("sourceURL")
                if url:
                    discovered.append(JobUrl(
                    url=url,
                    title=result.get("metadata", {}).get("title"),
                    source=self.name,
                    raw=result,
                ))
            return discovered





    

    