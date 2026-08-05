import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
import html
import pytest
from sources.discovery.adzuna import AdzunaDiscovery, APP_ID, APP_KEY

from models.job_url import JobUrl
from sources.discovery import (
    AdzunaDiscovery,
    FirecrawlSearchDiscovery,
    HackerNewsDiscovery,
    RemoteOKDiscovery,
    RemotiveDiscovery,
    YCJobsDiscovery,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _mock_response(status: int = 200, json_data=None, text: str = ""):
    """Build a mock httpx.Response-like object."""
    resp = MagicMock()
    resp.status_code = status
    resp.json = AsyncMock(return_value=json_data if json_data is not None else {})
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status >= 400:
        from httpx import HTTPStatusError
        resp.raise_for_status.side_effect = HTTPStatusError(
            f"HTTP {status}", request=MagicMock(), response=resp
        )
    return resp


def _mock_async_client(responses):
    class MockClient:
        def __init__(self, *args, **kwargs):
            self._responses = iter(responses)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args, **kwargs):
            pass

        async def get(self, *args, **kwargs):
            return next(self._responses)

        async def post(self, *args, **kwargs):
            return next(self._responses)

    return MockClient



class TestAdzunaDiscovery:
    def test_init_defaults(self):
        src = AdzunaDiscovery()
        assert src.country == "us"
        # app_id/app_key come from env/module globals
        assert src.app_id == APP_ID

    def test_init_custom_country(self):
        src = AdzunaDiscovery(country="gb")
        assert src.country == "gb"

    @pytest.mark.asyncio
    async def test_discover_returns_job_urls(self):
        src = AdzunaDiscovery(country="gb")
        api_response = {
            "results": [
                {
                    "redirect_url": "https://adzuna.com/1",
                    "title": "Senior Python Dev",
                    "company": {"display_name": "Acme"},
                    "location": {"area": ["London", "England", "UK"]},
                    "description": "Remote friendly",
                },
            ]
        }
        mock_resp = _mock_response(json_data=api_response)

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            jobs = await src.discover(query="python")


        assert len(jobs) == 2
        assert all(isinstance(j, JobUrl) for j in jobs)
        assert jobs[0].url == "https://adzuna.com/1"
        assert jobs[0].title == "Senior Python Dev"
        assert jobs[0].company == "Acme"
        assert jobs[0].location == "London, England, UK"
        assert jobs[0].is_remote is True
        assert jobs[0].source == "adzuna"
        assert jobs[0].raw is not None

        assert jobs[1].location is None
        assert jobs[1].is_remote is None

    @pytest.mark.asyncio
    async def test_discover_empty_results(self):
        src = AdzunaDiscovery(app_id="id", app_key="key")
        mock_resp = _mock_response(json_data={"results": []})

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            jobs = await src.discover(query="nonsense")

        assert jobs == []

    @pytest.mark.asyncio
    async def test_discover_api_error(self):
        src = AdzunaDiscovery(app_id="id", app_key="key")
        mock_resp = _mock_response(status=403, json_data={"error": "bad key"})

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            with pytest.raises(Exception):
                await src.discover(query="python")



    @pytest.mark.asyncio
    async def test_discover_returns_job_urls(self):
        src = RemotiveDiscovery()
        api_response = {
            "jobs": [
                {
                    "url": "https://remotive.com/job/1",
                    "title": "  Django Developer  ",
                    "company_name": "  WidgetCo  ",
                    "candidate_required_location": "Worldwide",
                },
                {
                    "url": "https://remotive.com/job/2",
                    "title": "React Engineer",
                    "company_name": "StartupX",
                    "candidate_required_location": "USA only",
                },
            ]
        }
        mock_resp = _mock_response(json_data=api_response)

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            jobs = await src.discover(query="python")

        assert len(jobs) == 2
        assert jobs[0].url == "https://remotive.com/job/1"
        assert jobs[0].title == "Django Developer"
        assert jobs[0].company == "WidgetCo"
        assert jobs[0].location == "Worldwide"
        assert jobs[0].is_remote is True
        assert jobs[0].source == "remotive"

    @pytest.mark.asyncio
    async def test_discover_skips_missing_urls(self):
        src = RemotiveDiscovery()
        api_response = {
            "jobs": [
                {"url": "", "title": "Bad", "company_name": "X"},
                {"url": "https://remotive.com/good", "title": "Good", "company_name": "Y"},
            ]
        }
        mock_resp = _mock_response(json_data=api_response)

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            jobs = await src.discover(query="python")

        assert len(jobs) == 1
        assert jobs[0].url == "https://remotive.com/good"



class TestRemoteOKDiscovery:
    @pytest.mark.asyncio
    async def test_discover_filters_client_side(self):
        src = RemoteOKDiscovery()
        # First element is metadata per RemoteOK API contract
        api_response = [
            {"legal": "RemoteOK API"},
            {
                "url": "https://remoteok.com/tracked/1",
                "originalUrl": "https://example.com/job/1",
                "position": "Python Backend Engineer",
                "company": "Alpha",
                "location": "Worldwide",
                "tags": ["python", "aws"],
            },
            {
                "url": "https://remoteok.com/tracked/2",
                "originalUrl": None,
                "position": "Marketing Manager",
                "company": "Beta",
                "location": "USA",
                "tags": ["seo"],
            },
        ]
        mock_resp = _mock_response(json_data=api_response)

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            jobs = await src.discover(query="python", limit=10)

        assert len(jobs) == 1
        assert jobs[0].title == "Python Backend Engineer"
        assert jobs[0].company == "Alpha"
        assert jobs[0].url == "https://example.com/job/1"  # prefers originalUrl
        assert jobs[0].is_remote is True

    @pytest.mark.asyncio
    async def test_discover_respects_limit(self):
        src = RemoteOKDiscovery()
        api_response = [{"legal": ""}] + [
            {
                "url": f"https://remoteok.com/{i}",
                "position": f"Python Job {i}",
                "company": f"Co{i}",
                "tags": ["python"],
            }
            for i in range(5)
        ]
        mock_resp = _mock_response(json_data=api_response)

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            jobs = await src.discover(query="python", limit=3)

        assert len(jobs) == 3



class TestYCJobsDiscovery:
    def _build_html(self, jobs_json: list) -> str:
        """Build a fake workatastartup.com HTML page with embedded jobs JSON."""
        payload = json.dumps(jobs_json, separators=(",", ":"))
        escaped = html.escape(payload)
        return f"""
        <html>
        <head><title>YC Jobs</title></head>
        <body>
        <script>
        window.__DATA__ = {{"jobs":{escaped},"total":{len(jobs_json)}}};
        </script>
        </body>
        </html>
        """

    @pytest.mark.asyncio
    async def test_discover_extracts_jobs(self):
        src = YCJobsDiscovery()
        jobs_data = [
            {
                "id": 123,
                "title": "Full Stack Engineer",
                "companyName": "Stripe",
                "location": "Remote (Worldwide)",
                "roleType": "Full stack",
                "jobType": "Fulltime",
                "salary": "$150K - $200K",
            },
            {
                "id": 456,
                "title": "Backend Engineer",
                "companyName": "Notion",
                "location": "San Francisco, CA",
                "roleType": "Backend",
                "jobType": "Fulltime",
                "salary": None,
            },
        ]
        html_text = self._build_html(jobs_data)
        mock_resp = _mock_response(text=html_text)

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            jobs = await src.discover(query="engineer")

        assert len(jobs) == 2
        assert jobs[0].url == "https://www.workatastartup.com/jobs/123"
        assert jobs[0].title == "Full Stack Engineer"
        assert jobs[0].company == "Stripe"
        assert jobs[0].is_remote is True
        assert jobs[0].source == "yc_jobs"

    @pytest.mark.asyncio
    async def test_discover_filters_by_role_type(self):
        src = YCJobsDiscovery()
        jobs_data = [
            {
                "id": 1,
                "title": "Frontend Dev",
                "companyName": "A",
                "location": "Remote",
                "roleType": "Frontend",
                "jobType": "Fulltime",
            },
            {
                "id": 2,
                "title": "Backend Dev",
                "companyName": "B",
                "location": "Remote",
                "roleType": "Backend",
                "jobType": "Fulltime",
            },
        ]
        html_text = self._build_html(jobs_data)
        mock_resp = _mock_response(text=html_text)

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            jobs = await src.discover(query="dev", role_type="Backend")

        assert len(jobs) == 1
        assert jobs[0].title == "Backend Dev"

    @pytest.mark.asyncio
    async def test_discover_filters_visa_unfriendly(self):
        src = YCJobsDiscovery()
        jobs_data = [
            {
                "id": 1,
                "title": "US Only Job",
                "companyName": "A",
                "location": "Palo Alto, CA, US",
                "roleType": "Full stack",
                "jobType": "Fulltime",
            },
            {
                "id": 2,
                "title": "UK Job",
                "companyName": "B",
                "location": "London, England, GB",
                "roleType": "Backend",
                "jobType": "Fulltime",
            },
            {
                "id": 3,
                "title": "Remote Worldwide",
                "companyName": "C",
                "location": "Remote (Worldwide)",
                "roleType": "Full stack",
                "jobType": "Fulltime",
            },
        ]
        html_text = self._build_html(jobs_data)
        mock_resp = _mock_response(text=html_text)

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            jobs = await src.discover(query="job", visa_friendly_only=True)

        titles = {j.title for j in jobs}
        assert "US Only Job" in titles
        assert "UK Job" in titles
        assert "Remote Worldwide" in titles

    @pytest.mark.asyncio
    async def test_discover_no_jobs_found(self):
        src = YCJobsDiscovery()
        html_text = "<html><body>No jobs here</body></html>"
        mock_resp = _mock_response(text=html_text)

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            jobs = await src.discover(query="engineer")

        assert jobs == []



class TestHackerNewsDiscovery:
    @pytest.mark.asyncio
    async def test_discover_full_flow(self):
        src = HackerNewsDiscovery()

        
        user_resp = _mock_response(json_data={
            "submitted": [400000, 399999]
        })

        
        item_not_hiring = _mock_response(json_data={
            "id": 400000,
            "title": "Show HN: My project",
            "type": "story",
        })

        
        thread_resp = _mock_response(json_data={
            "id": 399999,
            "title": "Ask HN: Who is hiring? (July 2026)",
            "type": "story",
            "kids": [500001, 500002, 500003],
        })

        
        comment_good = _mock_response(json_data={
            "id": 500001,
            "by": "founder1",
            "text": "<p>AcmeCorp | Senior Python Engineer | San Francisco | <a href=\"https://acme.com/jobs\">https://acme.com/jobs</a></p><p>We build widgets. Visa sponsorship and relocation available. Remote OK.</p>",
            "type": "comment",
        })
        comment_bad = _mock_response(json_data={
            "id": 500002,
            "by": "founder2",
            "text": "<p>LocalOnly | Junior Dev | Smalltown, USA | No remote, locals only</p>",
            "type": "comment",
        })
        comment_deleted = _mock_response(json_data={
            "id": 500003,
            "deleted": True,
            "type": "comment",
        })

        responses = [
            user_resp,
            item_not_hiring,
            thread_resp,
            comment_good,
            comment_bad,
            comment_deleted,
        ]

        with patch("httpx.AsyncClient", _mock_async_client(responses)):
            jobs = await src.discover(query="python", limit=10)

        assert len(jobs) == 1
        job = jobs[0]
        assert job.company == "AcmeCorp"
        assert job.title == "Senior Python Engineer"
        assert job.location == "San Francisco"
        assert job.url == "https://acme.com/jobs"
        assert job.is_remote is True
        assert job.source == "hackernews"
        assert job.raw["visa_sponsorship"] is True

    @pytest.mark.asyncio
    async def test_discover_no_hiring_thread(self):
        src = HackerNewsDiscovery()
        user_resp = _mock_response(json_data={"submitted": []})

        with patch("httpx.AsyncClient", _mock_async_client([user_resp])):
            jobs = await src.discover(query="python")

        assert jobs == []

    @pytest.mark.asyncio
    async def test_discover_query_filter(self):
        src = HackerNewsDiscovery()

        user_resp = _mock_response(json_data={"submitted": [1]})
        thread_resp = _mock_response(json_data={
            "id": 1,
            "title": "Who is hiring?",
            "kids": [10, 11],
        })
        comment_python = _mock_response(json_data={
            "id": 10,
            "by": "a",
            "text": "Co | Python Dev | Remote | <a href=\"https://co.com\">apply</a>",
        })
        comment_rust = _mock_response(json_data={
            "id": 11,
            "by": "b",
            "text": "Co | Rust Dev | Remote | <a href=\"https://co.com\">apply</a>",
        })

        with patch("httpx.AsyncClient", _mock_async_client([
            user_resp, thread_resp, comment_python, comment_rust
        ])):
            jobs = await src.discover(query="python")

        assert len(jobs) == 1
        assert "Python" in jobs[0].title



class TestFirecrawlSearchDiscovery:
    def test_init_missing_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Firecrawl Search requires"):
                FirecrawlSearchDiscovery()

    @pytest.mark.asyncio
    async def test_discover_returns_job_urls(self):
        src = FirecrawlSearchDiscovery(api_key="fc_key")
        api_response = {
            "success": True,
            "data": [
                {
                    "url": "https://example.com/job/1",
                    "metadata": {"title": "Job One", "sourceURL": "https://example.com/job/1"},
                },
                {
                    "url": None,
                    "metadata": {"sourceURL": "https://example.com/job/2"},
                },
            ]
        }
        mock_resp = _mock_response(json_data=api_response)

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            jobs = await src.discover(query="python developer", limit=5)

        assert len(jobs) == 2
        assert jobs[0].url == "https://example.com/job/1"
        assert jobs[1].url == "https://example.com/job/2"
        assert jobs[0].source == "firecrawl_search"

    @pytest.mark.asyncio
    async def test_discover_api_failure(self):
        src = FirecrawlSearchDiscovery(api_key="fc_key")
        api_response = {
            "success": False,
            "error": "Rate limit exceeded",
        }
        mock_resp = _mock_response(json_data=api_response)

        with patch("httpx.AsyncClient", _mock_async_client([mock_resp])):
            with pytest.raises(RuntimeError, match="Rate limit exceeded"):
                await src.discover(query="python")



class TestDiscoverySourceContract:
    """Ensure every source satisfies the abstract base class."""

    def test_all_sources_have_name(self):
        sources = [
            AdzunaDiscovery(app_id="a", app_key="b"),
            RemotiveDiscovery(),
            RemoteOKDiscovery(),
            YCJobsDiscovery(),
            HackerNewsDiscovery(),
            FirecrawlSearchDiscovery(api_key="k"),
        ]
        for src in sources:
            assert isinstance(src.name, str)
            assert src.name != ""