import re
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from models.job import Job
from sources.base import JobExtractor

class WorkableExtractor(JobExtractor):
    @property
    def name(self) -> str:
        return "Workable"

    @property
    def domain_patterns(self):
        return [
            re.compile(r"apply\.workable\.com", re.I),
        ]

    async def extract(self, url: str, html: Optional[str] = None) -> Job:
        api_job = await self._try_api(url)
        if api_job:
            return api_job

        if html is None:
            html = await self._fetch(url)

        return self._extract_from_html(url, html)


    async def _try_api(self, url: str) -> Optional[Job]:
        parsed = self._parse_url(url)
        if not parsed:
            return None

        company, job_id = parsed
        api_url = f"https://apply.workable.com/api/v1/widget/accounts/{company}?details=true"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(api_url)
                response.raise_for_status()
                data = response.json()

            job = next(
                (j for j in data.get("jobs", []) if j.get("shortcode") == job_id),
                None
            )
            if job:
                return self._build_from_api(url, job, company)

            
        except (httpx.HTTPError, ValueError, KeyError, StopIteration):
            pass

        return None 


    def pass_url(self, url: str) -> Optional[tuple[str, str]]:
        match = re.match(
            r"https?://apply\.workable\.com/([^/]+)/j/([A-Z0-9]+)(?:/apply)?/?$",
            url,
            re.I,
        )
        if match:
            return match.group(1), match.group(2)

        match = re.match(
            r"https?://apply\.workable\.com/j/([A-Z0-9]+)(?:/apply)?/?$",
            url,
            re.I,
        )
        if match:
            return None

        return None 


    def _build_from_api(self, url: str, data: dict, company_slug: Optional[str] = None) -> Job:
        location_parts = []
        city = data.get("city")
        state = data.get("state")
        country = data.get("country")
        if city:
            location_parts.append(city)
        if state and state != city:
            location_parts.append(state)
        if country and country not in location_parts:
            location_parts.append(country)

        location = ", ".join(location_parts) if location_parts else None

        locations = data.get("locations", [])
        if locations and len(locations) > 0:
            location = f"{location} (and {len(locations) - 1} other locations)"

        is_remote = data.get("telecommuting", False)
        return Job(
            source=self.name,
            url=url,
            company=company_slug.replace("-", " ").title(),  
            title=data.get("title", "Unknown"),
            location=location,
            country=country,
            is_remote=is_remote,
            employment_type=data.get("employment_type"),
            description=data.get("description"),
            apply_url=data.get("application_url"),
            visa_sponsorship=self._mentions_visa(data.get("description", "")),
        )

    async def _fetch(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        async with httpx.AsyncClient(timeout=20, follow_redirect = True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def _extract_from_html(self, url: str, html: str) -> Job:
        soup = BeautifulSoup(html, "html.parser")

        title = "Unknown"
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
        company = "Unknown"
        page_title = soup.find("title")
        if page_title and page_title.string:
            text = page_title.string.strip()
            if " at " in text:
                company = text.split(" at ")[-1].strip()

        return Job(
            source=self.name,
            url=url,
            company=company,
            title=title,
            is_remote=None,
            visa_sponsorship=False,
        )

    def _mentions_visa(self, description: str) -> bool:
        text = description.lower()
        signals = ("visa", "sponsorship", "sponsor", "h1b", "h-1b", "relocation", "work permit")
        return any(s in text for s in signals)
        
        