from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field

from lead_factory.models import LeadGrade, ReviewStatus
from lead_factory.schemas import AccountObservation
from lead_factory.services.product_matching import ProductMatchResult


@dataclass(frozen=True)
class EnrichmentRequest:
    observation: AccountObservation
    deterministic_score: int
    deterministic_grade: LeadGrade
    deterministic_product_matches: list[ProductMatchResult]
    prompt_version: str


class AISignal(BaseModel):
    label: str
    evidence_id: str


class AIProductMatch(BaseModel):
    family_id: str
    reason: str
    evidence_ids: list[str]


class AIUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None


class EnrichmentResult(BaseModel):
    summary: str
    icp_id: str
    confidence: float = Field(ge=0, le=1)
    signals: list[AISignal]
    product_matches: list[AIProductMatch]
    risk_flags: list[str]
    review_recommendation: ReviewStatus
    usage: AIUsage = Field(default_factory=AIUsage)


class AIProvider(Protocol):
    def is_available(self) -> bool: ...

    async def enrich(self, request: EnrichmentRequest) -> EnrichmentResult: ...


class ProviderUnavailable(RuntimeError):
    pass

