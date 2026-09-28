from __future__ import annotations

from dataclasses import dataclass

from lead_factory.config_loader import CatalogConfig, ProductFamily
from lead_factory.schemas import AccountObservation


@dataclass(frozen=True)
class ProductMatchResult:
    family_id: str
    family_name: str
    recommended_products: list[str]
    reason: str
    confidence: float
    evidence_ids: list[str]


def _family_terms(family: ProductFamily) -> set[str]:
    return {term.casefold() for term in [*family.aliases, *family.buyer_signals]}


def match_products(
    observation: AccountObservation, config: CatalogConfig
) -> list[ProductMatchResult]:
    matches: list[ProductMatchResult] = []
    for family in config.products.families:
        terms = _family_terms(family)
        evidence_ids: list[str] = []
        matched_terms: set[str] = set()
        for item in observation.evidence:
            excerpt = item.excerpt.casefold()
            hits = {term for term in terms if term in excerpt}
            if hits:
                evidence_ids.append(item.id)
                matched_terms.update(hits)

        if not evidence_ids:
            continue

        confidence = min(0.95, 0.7 + 0.1 * len(matched_terms))
        term_summary = ", ".join(sorted(matched_terms)[:4])
        matches.append(
            ProductMatchResult(
                family_id=family.id,
                family_name=family.name,
                recommended_products=list(family.recommended_offerings),
                reason=f"Official-site evidence contains: {term_summary}",
                confidence=confidence,
                evidence_ids=evidence_ids,
            )
        )

    return sorted(matches, key=lambda item: (-item.confidence, item.family_id))
