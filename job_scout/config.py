from dataclasses import dataclass 

@dataclass(frozen=True)
class HNConfig:
    WHO_IS_HIRING_QUERY_URL = (
        "https://hn.algolia.com/api/v1/search?"
        "tags=story&query=who%20is%20hiring"
    )
    ITEM_API_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"
    COMMENTS_PER_PAGE = 100

@dataclass(frozen=True)
class IndeedConfig:
    RSS_BASE_URL = "https://rss.indeed.com/rss"
    QUERY = "AI engineer"
    LOCATION = "remote"

@dataclass(frozen=True)
class GoogleJobsConfig:
    SEARCH_URL = "https://www.google.com/search"
    QUERY = "AI engineer"
    LOCATION = "remote"
    UDM = 25  
    NUM_RESULTS = 20

@dataclass(frozen=True)
class WellfoundConfig:
    API_BASE_URL = "https://api.angel.co/1"
    JOBS_URL = "https://wellfound.com/jobs"
    QUERY = "AI engineer"
    REMOTE_ONLY = True

@dataclass(frozen=True)
class ScoutConfig:
    hn = HNConfig()
    indeed = IndeedConfig()
    google_jobs = GoogleJobsConfig()
    wellfound = WellfoundConfig()
    max_age_days = 30
    request_timeout = 30

