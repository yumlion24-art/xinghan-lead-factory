from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from lead_factory.models import LeadGrade, ReviewStatus, SearchTaskStatus


class EvidenceInput(BaseModel):
    id: str
    signal_type: str
    excerpt: str
    source_url: str
    confidence: float = Field(default=1.0, ge=0, le=1)


class AccountObservation(BaseModel):
    display_name: str
    normalized_domain: str
    website_url: str
    country: str | None = None
    industry: str | None = None
    company_type: str | None = None
    description: str = ""
    scale_signals: list[str] = Field(default_factory=list)
    contact_routes: list[dict[str, str]] = Field(default_factory=list)
    evidence: list[EvidenceInput] = Field(default_factory=list)

    def searchable_text(self) -> str:
        values = [
            self.display_name,
            self.country or "",
            self.industry or "",
            self.company_type or "",
            self.description,
            *self.scale_signals,
            *(item.excerpt for item in self.evidence),
        ]
        return " ".join(values).casefold()


class ReviewDecisionCreate(BaseModel):
    status: ReviewStatus
    note: str | None = Field(default=None, max_length=2000)
    actor: str = Field(default="local_operator", max_length=120)


class SearchTaskCreate(BaseModel):
    query: str = Field(default="", max_length=500)
    countries: list[str] = Field(default_factory=list)
    icp_ids: list[str] = Field(default_factory=list)
    seed_urls: list[HttpUrl] = Field(default_factory=list)
    max_results: int = Field(default=20, ge=1, le=100)
    max_pages_per_domain: int = Field(default=4, ge=1, le=20)


class AccountSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    normalized_domain: str
    website_url: str | None
    country: str | None
    company_type: str | None
    grade: LeadGrade | None
    score: int
    review_status: ReviewStatus
    enrichment_mode: str
    is_demo: bool
    created_at: datetime


class SearchTaskSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    query: str
    status: SearchTaskStatus
    progress: dict[str, object]
    budget_usage: dict[str, object]
    failure_summary: str | None
    created_at: datetime

