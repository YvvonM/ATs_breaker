import re 
from typing import Optional
import httpx 
from models.job import Job
from bs4 import BeautifulSoup
from sources.base import JobExtractor

class SmartRecruitersExtractor(JobExtractor):

    @property
    def name(self) -> str:
        return "SmartRecruiters"

    @property
    def domain_patterns(self):
        return [
            re.compile(r"careers\.smartrecruiters\.com", re.I),
            re.compile(r"jobs\.smartrecruiters\.com", re.I),
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

        company, posting_id = parsed
        detail_url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings/{posting_id}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(detail_url)
                response.raise_for_status()
                data = response.json()

            return self._build_from_api(url, data)

        except (httpx.HTTPError, ValueError, KeyError):
            pass

        return None

    def _parse_url(self, url: str) -> Optional[tuple[str, str]]:
        match = re.match(
            r"https?://(?:careers|jobs)\.smartrecruiters\.com/([^/]+)/(\d+)",
            url,
            re.I,
        )
        if match:
            return match.group(1), match.group(2)

        match = re.match(
            r"https?://(?:www\.)?smartrecruiters\.com/([^/]+)/(\d+)",
            url,
            re.I,
        )
        if match:
            return match.group(1), match.group(2)

        return None


    def _build_from_api(self, original_url: str, data: dict) -> Job:
        title = data.get("name", "Unknown")
        company = data.get("company", {}).get("name", "Unknown")
        loc = data.get("location", {})
        location = loc.get("fullLocation")
        if not location:
            parts = [
                loc.get("city"),
                loc.get("state"),
                loc.get("country"),
            ]
            location = ", ".join(p for p in parts if p)

        is_remote = data.get("remote", False)
        remote_restrictions = None
        if loc.get("hybrid"):
            remote_restrictions = "Hybrid"
        elif not is_remote:
            remote_restrictions = "On-site"

        job_ad = data.get("jobAd", {})
        sections = job_ad.get("sections", [])
        company_desc = sections.get("companyDescription", {}).get("text", "")
        job_desc = sections.get("jobDescription", {}).get("text", "")
        qualifications = sections.get("qualifications", {}).get("text", "")
        additional = sections.get("additionalInformation", {}).get("text", "")
        description_parts = []
        if company_desc:
            description_parts.append(f"<h2>About {company}</h2>\n{company_desc}")
        if job_desc:
            description_parts.append(f"<h2>Job Description</h2>\n{job_desc}")
        if qualifications:
            description_parts.append(f"<h2>Qualifications</h2>\n{qualifications}")
        if additional:
            description_parts.append(f"<h2>Additional Information</h2>\n{additional}")

        description = "\n\n".join(description_parts) if description_parts else None
        requirements = self._split_list_items(qualifications)

        return Job(
            source=self.name,
            url=original_url,
            company=company,
            title=title,
            location=location,
            country=loc.get("country"),
            is_remote=is_remote,
            remote_restrictions=remote_restrictions,
            employment_type=data.get("typeOfEmployment"),
            seniority=data.get("experienceLevel", {}).get("label") if isinstance(data.get("experienceLevel"), dict) else None,
            description=description,
            requirements=requirements,
            apply_url=data.get("applyUrl"),
            visa_sponsorship=self._mentions_visa(description or ""),
        )

    async def _fetch(self, url: str) -> str:
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

    def _extract_from_html(self, url: str, html: str) -> Job:
        soup = BeautifulSoup(html, "html.parser")
        title = "Unknown"
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        return Job(
            source=self.name,
            url=url,
            company="Unknown",
            title=title,
            is_remote=None,
            visa_sponsorship=False,
        )


    def _split_list_items(self, text: str) -> list[str]:
        if not text:
            return []
        lines = [l.strip("-• ").strip() for l in text.split("\n") if l.strip()]
        return [l for l in lines if l and not l.lower().startswith(("about ", "job description", "qualifications"))]

    def _mentions_visa(self, description: str) -> bool:
        text = description.lower()
        signals = ("visa", "sponsorship", "sponsor", "h1b", "h-1b", "relocation", "work permit")
        return any(s in text for s in signals)
