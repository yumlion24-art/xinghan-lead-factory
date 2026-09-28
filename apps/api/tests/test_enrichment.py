from __future__ import annotations

import pytest

from lead_factory.models import LeadGrade
from lead_factory.providers.ai.base import EnrichmentRequest, EnrichmentResult
from lead_factory.providers.ai.disabled import DisabledAIProvider
from lead_factory.providers.ai.openai_provider import _strict_schema
from lead_factory.schemas import AccountObservation, EvidenceInput
from lead_factory.services.budgets import BudgetLedger, BudgetLimits
from lead_factory.services.enrichment import enrich_or_fallback
from lead_factory.services.product_matching import ProductMatchResult


class FakeProvider:
    def __init__(self, result=None, error: Exception | None = None, available: bool = True) -> None:
        self.result = result
        self.error = error
        self.available = available

    def is_available(self) -> bool:
        return self.available

    async def enrich(self, request: EnrichmentRequest):
        if self.error:
            raise self.error
        return self.result


def request() -> EnrichmentRequest:
    return EnrichmentRequest(
        observation=AccountObservation(
            display_name="Sky Meals",
            normalized_domain="skymeals.example",
            website_url="https://skymeals.example",
            description="Airline catering buyer",
            evidence=[
                EvidenceInput(
                    id="ev-1",
                    signal_type="product",
                    excerpt="We source meal trays.",
                    source_url="https://skymeals.example/products",
                )
            ],
        ),
        deterministic_score=82,
        deterministic_grade=LeadGrade.A,
        deterministic_product_matches=[
            ProductMatchResult(
                family_id="airline_airport",
                family_name="Airline and Airport Supplies",
                recommended_products=["Airline meal trays and meal boxes"],
                reason="Official evidence contains meal trays",
                confidence=0.9,
                evidence_ids=["ev-1"],
            )
        ],
        prompt_version="company_enrichment-v1",
    )


def budget(ai_calls: int = 1) -> BudgetLedger:
    return BudgetLedger(BudgetLimits(pages=1, domains=1, ai_calls=ai_calls, elapsed_seconds=60))


def test_openai_schema_is_recursively_strict() -> None:
    schema = _strict_schema(EnrichmentResult.model_json_schema())

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    for definition in schema["$defs"].values():
        if definition.get("type") == "object":
            assert definition["additionalProperties"] is False
            assert set(definition["required"]) == set(definition["properties"])


@pytest.mark.asyncio
async def test_valid_ai_result_enriches_summary_without_changing_score() -> None:
    result = EnrichmentResult.model_validate(
        {
            "summary": "International inflight caterer with direct meal-tray demand.",
            "icp_id": "aviation_catering",
            "confidence": 0.91,
            "signals": [{"label": "meal tray demand", "evidence_id": "ev-1"}],
            "product_matches": [
                {
                    "family_id": "airline_airport",
                    "reason": "Meal tray sourcing is explicit.",
                    "evidence_ids": ["ev-1"],
                }
            ],
            "risk_flags": [],
            "review_recommendation": "approved",
            "usage": {"input_tokens": 400, "output_tokens": 120, "estimated_cost_usd": 0.01},
        }
    )

    outcome = await enrich_or_fallback(FakeProvider(result), request(), budget())

    assert outcome.mode == "ai"
    assert outcome.deterministic_score == 82
    assert outcome.deterministic_grade is LeadGrade.A
    assert outcome.deterministic_product_matches == request().deterministic_product_matches
    assert outcome.ai_result == result
    assert outcome.fallback_reason is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "reason"),
    [
        (DisabledAIProvider(), "provider_unavailable"),
        (FakeProvider(error=TimeoutError("slow")), "provider_timeout"),
        (FakeProvider(error=RuntimeError("boom")), "provider_error"),
        (FakeProvider(result="not-json"), "invalid_provider_output"),
        (FakeProvider(result={"summary": "missing fields"}), "invalid_provider_output"),
    ],
)
async def test_provider_failures_return_rules_only(provider, reason: str) -> None:
    outcome = await enrich_or_fallback(provider, request(), budget())

    assert outcome.mode == "rules_only"
    assert outcome.fallback_reason == reason
    assert outcome.deterministic_score == 82
    assert outcome.deterministic_product_matches == request().deterministic_product_matches
    assert outcome.ai_result is None


@pytest.mark.asyncio
async def test_unknown_evidence_reference_returns_rules_only() -> None:
    result = {
        "summary": "Claim without source",
        "icp_id": "aviation_catering",
        "confidence": 0.9,
        "signals": [{"label": "large fleet", "evidence_id": "invented"}],
        "product_matches": [],
        "risk_flags": [],
        "review_recommendation": "approved",
        "usage": {},
    }

    outcome = await enrich_or_fallback(FakeProvider(result), request(), budget())

    assert outcome.mode == "rules_only"
    assert outcome.fallback_reason == "invalid_evidence_reference"


@pytest.mark.asyncio
async def test_exhausted_ai_budget_skips_provider() -> None:
    provider = FakeProvider(result={})

    outcome = await enrich_or_fallback(provider, request(), budget(ai_calls=0))

    assert outcome.mode == "rules_only"
    assert outcome.fallback_reason == "ai_budget_exhausted"
    assert provider.result == {}
