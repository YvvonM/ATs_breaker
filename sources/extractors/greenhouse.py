import json 
import re 
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup 
from models.job import Job 
from sources.base import JobExtractor 

class GreenhouseExtractor(JobExtractor):
    @property
    def name(self) -> str:
        return "greenhouse"

    @property
    def domain_patterns(self):
        return [
            re.compile(r"job-boards\.greenhouse\.io", re.I),
            re.compile(r"boards\.greenhouse\.io", re.I),
            re.compile(r"boards\.eu\.greenhouse\.io", re.I),
        ]

    async def extract(self, url:str, html: Optional[str] = None) -> Job:
        if html is None:
            html = await self._fetch(url)
        soup = BeautifulSoup(html, "html.parser")
        return self._build_job(url, soup)

    async def _fetch(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout = 20) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text

    def _build_job(self, url: str, soup: BeautifulSoup) -> Job:
        title = self._extract_title(soup)
        company = self._extract_company(soup)
        location = self._extract_location(soup)
        description = self._extract_description(soup)
        return Job(
            title=title,
            source=self.name,
            url=url,
            company=company,
            title=title,
            location=location,
            description=description,
            is_remote=self._is_remote(title, location, description),
            visa_sponsorship=self._mentions_visa(description),
            employment_type=self._extract_employment_type(description),
            salary_min=None,
            salary_max=None,)


        def _extract_company(self, soup: BeautifulSoup, title: str) -> str:
            page_title = soup.find("title")
            if page_title and page_title.string:
                text = page_title.string.strip()
                if " at " in text:
                    return text.split(" at ")[-1].strip()

            
            logo = soup.select_one(".logo img")
            if logo and logo.get("alt"):
                return logo["alt"].replace(" Logo", "").replace(" logo", "").strip()

            return "Unknown"

    def _extract_location(self, soup: BeautifulSoup) -> Optional[str]:
        el = soup.select_one(".job__location")
        if el:
            return el.get_text(strip=True)
        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        el = soup.select_one(".job__description.body")
        if el:
            return str(el)
        return None

    def _is_remote(self, title: str, location: Optional[str], description: Optional[str]) -> bool:
        text = f"{title} {location or ''} {description or ''}".lower()
        return any(w in text for w in ("remote", "work from home", "wfh", "anywhere", "distributed"))

    def _mentions_visa(self, description: Optional[str]) -> bool:
        if not description:
            return False
        text = description.lower()
        signals = ("visa", "sponsorship", "sponsor", "h1b", "h-1b", "relocation", "work permit")
        return any(s in text for s in signals)

    def _extract_employment_type(self, description: Optional[str]) -> Optional[str]:
        if not description:
            return None
        text = description.lower()
        if "full-time" in text or "full time" in text:
            return "Full-time"
        if "part-time" in text or "part time" in text:
            return "Part-time"
        if "contract" in text:
            return "Contract"
        if "internship" in text:
            return "Internship"
        return None

