from typing import List, Optional
import httpx 
from sources.base import DiscoverySource
import os 
from dotenv import load_dotenv
load_dotenv()
APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")
BASE_URL = "https://api.adzuna.com/v1/api/jobs"
if not APP_ID:
    raise ValueError("Missing Adzuna App ID!")

if not APP_KEY:
    raise ValueError("Missing Adzuna App Key!")

class AdzunaSource(DiscoverySource):
    def __init__(self, country: str = "us"):
        self.app_id = APP_ID
        self.app_key = APP_KEY
        self.country = country

    @property
    def name(self) -> str:
        return "adzuna"

    async def discover(self, query: str, location: Optional[str] = None,
    limit: int =50, salary_min: Optional[int] = None, salary_min: Optional[int] = None, salary_max: Optional[int] = None, full_time: Optional[bool] = None,
    permanent: Optional[bool] = None) -> List[str]:

        params = {
            "app_id":self.app_id,
            "app_key": self.app_key,
            "what": query,
            "results_per_page": min(limit, 50),
            "content-type": "application/json",
        }
        if location:
            params['where'] = location

        if salary_min is not None:
            params["salary_min"] = salary_min
        if salary_max is not None:
            params["salary_max"] = salary_max

        if full_time is True:
            params["full_time"] = 1

        if permanent is True:
            params["permanent"] = 1

        url = f"{BASE_URL}/{self.country}/search/1"
        async with httpx.AsyncClient(timeout = 30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        urls = [r["redirect_url"] for r in results if r.get("redirect_url")]

        return urls[:limit]


        


        