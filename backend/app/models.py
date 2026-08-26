from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ScrapeRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200, description="Keyword, sentence, or business type to search for")
    location: Optional[str] = Field(None, max_length=200, description="City/region to target, e.g. 'Mumbai'")
    sources: List[str] = Field(
        default_factory=list,
        description="Which sources to use. Empty = all (Tier 1 APIs first, then Tier 2). "
                    "Options: google_places, yelp_fusion, opencorporates, hunter, mca, "
                    "duckduckgo, bing, startpage, google_maps, indiamart, tradeindia, "
                    "justdial, sulekha, zaubacorp, bbb, yelp, yellowpages, website",
    )
    max_leads: int = Field(default=50, ge=1, le=500)
    use_ai: bool = Field(default=True, description="Use Groq/NIM to generate queries & score leads")


class LeadStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Contact(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None


class Lead(BaseModel):
    id: Optional[str] = None
    name: str = ""
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    ai_score: Optional[float] = None
    ai_summary: Optional[str] = None
    rating: Optional[float] = None
    verified: bool = False
    cin: Optional[str] = None  # company registration number (MCA/registry)


class JobProgress(BaseModel):
    stage: str = "idle"
    message: str = ""
    leads_found: int = 0
    total: int = 0
    percent: int = 0


class JobInfo(BaseModel):
    id: str
    status: LeadStatus
    progress: JobProgress = JobProgress()
    request: ScrapeRequest
    error: Optional[str] = None


class JobResult(JobInfo):
    leads: List[Lead] = []
    csv_path: Optional[str] = None
    stats: dict = {}
