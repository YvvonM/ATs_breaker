import re 
from typing import Optional 
import httpx 
from bs4 import BeautifulSoup 
from models.job import Job 
from sources.base import JobExtractor

class AshbyExtractor(JobExtractor):
    @property
    def name(self) -> str:
        return "Ashby"

    @property
    def domain_patterns(self):
        return [
            re.compile(r"jobs\.ashbyhq\.com", re.I),
        ]

    async def extract(self, url: str, html: Optional[str] = None) -> Job:
        api_job = await self._try_api(url)
        if api_job:
            return api_job 

        if html is None:
            html = await self._fetch(url)
        return self._extract_from_html(url, html)

    async def _try_api(self, url:str) -> Optional[Job]:
        parsed = self._parse_url(url)
        if not parsed:
            return None 

        company, job_id = parsed
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(api_url)
                response.raise_for_status()
                data = response.json()

            job = next(
                (j for j in data.get("jobs", []) if j.get("id") == job_id),
                None
            )
            if job:
                return self._build_from_api(url, job)

        except (httpx.HTTPError, ValueError, KeyError):
            pass

        return None

    def _parse_url(self, url:str) -> Optional[tuple[str, str]]:
        match = re.match(
            r"https?://jobs\.ashbyhq\.com/([^/]+)/([0-9a-f-]{8,})(?:/application)?/?$",
            url,
            re.I,
        )
        if match:
            return match.group(1), match.group(2)

        return None

    def _build_from_api(self, original_url: str, data:dict) -> Job:
        location = data.get("location") or data.get("locationName")
        is_remote = bool(data.get("isRemote", False))
        description = data.get("descriptionHtml") or data.get("descriptionPlain")

        return Job(
            source=self.name,
            url=original_url,
            company=data.get("organizationName", "Unknown"),
            title=data.get("title", "Unknown"),
            location=location,
            is_remote=is_remote,
            employment_type=data.get("employmentType"),
            description=description,
            visa_sponsorship=self._mentions_visa(description or ""),
            apply_url=data.get("applyUrl") or data.get("jobUrl"),
        )

    async def _fetch(self, url:str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        }
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text

    def _extract_from_html(self, url:str, html: str) -> Job:
        soup = BeautifulSoup(html, "html.parser")

        title = "Unknown"
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        company = "Unknown"
        page_title = soup.find("title")
        if page_title and page_title.string and " at " in page_title.string:
            company = page_title.string.split(" at ")[-1].strip()

        description_el = soup.select_one("[class*='description']")
        description = str(description_el) if description_el else None

        return Job(
            source=self.name,
            url=url,
            company=company,
            title=title,
            description=description,
            is_remote=self._is_remote(title, description),
            visa_sponsorship=self._mentions_visa(description or ""),
        )


    def _is_remote(self, title: str, description: Optional[str]) -> bool:
        text = f"{title} {description or ''}".lower()
        return any(w in text for w in ("remote", "work from home", "wfh", "anywhere", "distributed"))

    def _mentions_visa(self,description: str) -> bool:
        text = description.lower()
        signals = ("visa", "sponsorship", "sponsor", "h1b", "h-1b", "relocation", "work permit")
        return any(w in text for w in signals)
        



