from typing import List, Optional
import httpx 
from sources.base import DiscoverySource
from models.job_url import JobUrl
import os 
from dotenv import load_dotenv

load_dotenv()
APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

if not APP_ID:
    raise ValueError("Missing Adzuna App ID!")

if not APP_KEY:
    raise ValueError("Missing Adzuna App Key!")

class AdzunaDiscovery(DiscoverySource):
    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self, country: str = "us"):
        self.app_id = os.getenv("ADZUNA_APP_ID")
        self.app_key = os.getenv("ADZUNA_APP_KEY")
        self.country = country
        if not self.app_id or not self.app_key:
            raise ValueError("AdzunaDiscovery requires ADZUNA_APP_ID and ADZUNA_APP_KEY")

    @property
    def name(self) -> str:
        return "adzuna"

    async def discover(self, query:str, country: Optional[str] =  "gb", location: Optional[str] = None,  max_days_old: int = 7, results_per_page: int = 20, **kwargs,) -> List[JobUrl]:
        url = f"{self.BASE_URL}/{country}/search/1"
        params = {
            "app_id":self.app_id,
            "app_key": self.app_key,
            "what": query,
            "results_per_page": results_per_page,
            "max_days_old": max_days_old,
            "content-type": "application/json",
        }
        if location:
            params['where'] = location

        async with httpx.AsyncClient(timeout = 30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        discovered: List[JobUrl] = []
        for raw in results:
            redirect_url = raw.get("redirect_url")
            if not redirect_url:
                continue

            title = raw.get("title", "")
            description = raw.get("description", "")
            is_remote = self._is_remote(title, description)
            location_parts = raw.get("location", {}).get("area", [])
            location_str = ", ".join(location_parts) if location_parts else None
        
            discovered.append(JobUrl(
                url=redirect_url,
                title = title.strip(),
                company=raw.get("company", {}).get("display_name", "Unknown"),
                location=location_str,
                is_remote=is_remote,
                source=self.name,
                raw=raw,
            ))

        return discovered

    def _is_remote(self, title: str, description: str) -> Optional[bool]:
        text = f"{title} {description}".lower()
        if any(w in text for w in ("remote", "work from home", "wfh", "anywhere")):
            return True 

        return None 