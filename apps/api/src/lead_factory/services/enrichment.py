from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from lead_factory.models import LeadGrade
from lead_factory.providers.ai.base import AIProvider, EnrichmentRequest, EnrichmentResult
from lead_factory.services.budgets import BudgetExceeded, BudgetKind, BudgetLedger
from lead_factory.services.product_matching import ProductMatchResult


@dataclass(frozen=True)
class EnrichmentOutcome:
    mode: str
    deterministic_score: int
    deterministic_grade: LeadGrade
    deterministic_product_matches: list[ProductMatchResult]
    ai_result: EnrichmentResult | None
    fallback_reason: str | None


def _rules_only(request: EnrichmentRequest, reason: str) -> EnrichmentOutcome:
    return EnrichmentOutcome(
        mode="rules_only",
        deterministic_score=request.deterministic_score,
        deterministic_grade=request.deterministic_grade,
        deterministic_product_matches=request.deterministic_product_matches,
        ai_result=None,
        fallback_reason=reason,
    )


def _has_valid_evidence(result: EnrichmentResult, request: EnrichmentRequest) -> bool:
    known = {item.id for item in request.observation.evidence}
    referenced = {item.evidence_id for item in result.signals}
    referenced.update(
        evidence_id for match in result.product_matches for evidence_id in match.evidence_ids
    )
    return referenced.issubset(known)


async def enrich_or_fallback(
    provider: AIProvider,
    request: EnrichmentRequest,
    budget: BudgetLedger,
) -> EnrichmentOutcome:
    if not provider.is_available():
        return _rules_only(request, "provider_unavailable")
    try:
        budget.consume(BudgetKind.AI_CALL)
    except BudgetExceeded:
        return _rules_only(request, "ai_budget_exhausted")

    try:
        raw_result = await provider.enrich(request)
    except TimeoutError:
        return _rules_only(request, "provider_timeout")
    except Exception:
        return _rules_only(request, "provider_error")

    try:
        result = (
            raw_result
            if isinstance(raw_result, EnrichmentResult)
            else EnrichmentResult.model_validate(raw_result)
        )
    except (ValidationError, TypeError, ValueError):
        return _rules_only(request, "invalid_provider_output")

    if not _has_valid_evidence(result, request):
        return _rules_only(request, "invalid_evidence_reference")
    return EnrichmentOutcome(
        mode="ai",
        deterministic_score=request.deterministic_score,
        deterministic_grade=request.deterministic_grade,
        deterministic_product_matches=request.deterministic_product_matches,
        ai_result=result,
        fallback_reason=None,
    )

