import re
from typing import Optional 
import httpx 
from bs4 import BeautifulSoup 
from models.job import Job
from sources.base import JobExtractor

class LevelExtractor(JobExtractor):
    @property
    def name(self) -> str:
        return "lever"

    @property
    def domain_patterns(self):
        return [
            re.compile(r"jobs\.lever\.co", re.I),
        ]

    async def extract(self, url: str, html: Optional[str] = None) -> Job:
        api_jobs = await self._try_api(url)
        if api_jobs:
            return api_jobs 

        if html is None:
            html = await self._fetch(url)
        return self._extract_from_html(url, html)

    async def _try_api(self, url: str) -> Optional[Job]:
        parsed = self._parse_url(url)
        if not parsed:
            return None
        company, job_id = parsed
        api_url = f"https://api.lever.co/v0/postings/{company}/{job_id}?mode=json"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(api_url)
                response.raise_for_status()
                data = response.json()
                return self._build_from_api(url, data)
        except (httpx.HTTPError, ValueError, KeyError):
            return None

    def _parse_url(self, url:str) -> Optional[tuple[str, str]]:
        match = re.match(
            r"https?://jobs\.lever\.co/([^/]+)/([a-f0-9-]+)(?:/apply)?/?$",
            url,
            re.I,
        )
        if match:
            return match.group(1), match.group(2)
        return None

    def _build_from_api(self, original_url: str, data:dict) ->Job:
        categories = data.get("categories", {})
        salary_min, salary_max = None, None
        salary_range = categories.get("salaryRange")
        if salary_range:
            salary_min = salary_range.get("min")
            salary_max = salary_range.get("max")
            responsibilities, requirements, preferred = [], [], []
        for lst in data.get('list', []):
            list_text = lst.get('text', '').lower()
            content = self._strip_html(lst.get('content', ''))
            if any(w in list_text for w in ["requirement", "must have", "qualification"]):
                requirements.extend(self._split_list_items(content))
            elif any(w in list_text for w in ["responsibilit", "what you'll do", "role"]):
                responsibilities.extend(self._split_list_items(content))
            else:
                preferred.extend(self._split_list_items(content))

        workplace = data.get("workplaceType", "unspecified")
        is_remote = workplace.lower() == "remote"
        return Job(
            source = self.name,
            url = original_url,
            company=data.get("text", "").split("|")[0].strip() if "|" in data.get("text", "") else "Unknown",
            title = data.get("text", "unknown"),
            location = categories.get("location"),
            country = data.get("country"),
            is_remote = is_remote,
            remote_restrictions = None,
            employment_type = categories.get("commitment"),
            salary_min=salary_min,
            salary_max=salary_max,
            description=data.get("description"),
            responsibilities=responsibilities,
            requirements=requirements,
            preferred_qualifications=preferred,
            visa_sponsorship=self._mentions_visa(data.get("description", "")),
            apply_url=data.get("applyUrl"),
            )

    async def _fetch(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers = headers)
            response.raise_for_status()
            return response.text

    def _extract_from_html(self, url: str, html: str) -> Job:
        soup = BeautifulSoup(html, "html.parser")
        title = self._extract_title(soup)
        company = self._extract_company(soup, title)
        location = self._extract_location(soup)
        description = self._extract_description(soup)
        return Job(
            source=self.name,
            url=url,
            company=company,
            title=title,
            location=location,
            description=description,
            is_remote=self._is_remote(title, location, description),
            visa_sponsorship=self._mentions_visa(description),
            employment_type=self._extract_employment_type(description),
        )


    def _extract_company(self, soup: BeautifulSoup, title: str) -> str:
        page_title = soup.find("title")
        if page_title and page_title.string and " at " in page_title.string:
            return page_title.string.split(" at ")[-1].strip()
        return "Unknown"

    def _extract_location(self, soup: BeautifulSoup) -> Optional[str]:
        el = soup.select_one(".posting-categories .location")
        if el:
            return el.get_text(strip=True)
        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        el = soup.select_one(".content")
        if el:
            return str(el)
        return None
    def _strip_html(self, text: Optional[str]) -> str:
        if not text:
            return ""
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text(separator="\n", strip=True)

    def _split_list_items(self, text: str) -> list[str]:
        lines = [l.strip("-• ").strip() for l in text.split("\n") if l.strip()]
        return [l for l in lines if l]

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

        
