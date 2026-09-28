from __future__ import annotations

from dataclasses import dataclass

from lead_factory.config_loader import CatalogConfig, ScoreRule, ScoringConfig
from lead_factory.models import LeadGrade, ReviewStatus
from lead_factory.schemas import AccountObservation, EvidenceInput


@dataclass(frozen=True)
class ScoreContribution:
    rule_id: str
    dimension: str
    points: int
    excerpt: str
    source_url: str
    evidence_id: str | None


@dataclass(frozen=True)
class ScoreResult:
    total: int
    grade: LeadGrade
    calculation_version: str
    review_recommendation: ReviewStatus
    review_reason: str | None
    positive_points: int
    negative_points: int
    contributions: list[ScoreContribution]


def grade_for_score(score: int, config: ScoringConfig) -> LeadGrade:
    if score >= config.grade_a_min:
        return LeadGrade.A
    if score >= config.grade_b_min:
        return LeadGrade.B
    return LeadGrade.C


def _rule_evidence(
    rule: ScoreRule, observation: AccountObservation
) -> tuple[str, str, str | None] | None:
    terms = [term.casefold() for term in rule.any_terms]
    for evidence in observation.evidence:
        excerpt = evidence.excerpt.casefold()
        if any(term in excerpt for term in terms):
            return evidence.excerpt, evidence.source_url, evidence.id

    fields = [
        observation.company_type or "",
        observation.description,
        observation.country or "",
        " ".join(observation.scale_signals),
    ]
    for field in fields:
        folded = field.casefold()
        if any(term in folded for term in terms):
            return field, observation.website_url, None
    return None


def _positive_contributions(
    observation: AccountObservation, config: CatalogConfig
) -> list[ScoreContribution]:
    candidates: dict[str, ScoreContribution] = {}
    limits = config.scoring.weights.model_dump()
    for rule in config.scoring.rules:
        matched = _rule_evidence(rule, observation)
        if matched is None:
            continue
        excerpt, source_url, evidence_id = matched
        points = min(rule.points, limits[rule.dimension])
        contribution = ScoreContribution(
            rule_id=rule.id,
            dimension=rule.dimension,
            points=points,
            excerpt=excerpt,
            source_url=source_url,
            evidence_id=evidence_id,
        )
        existing = candidates.get(rule.dimension)
        if existing is None or contribution.points > existing.points:
            candidates[rule.dimension] = contribution
    return list(candidates.values())


def _negative_contributions(
    observation: AccountObservation, config: CatalogConfig
) -> list[ScoreContribution]:
    remaining = config.scoring.negative_cap
    contributions: list[ScoreContribution] = []
    for rule in config.scoring.negative_rules:
        if remaining == 0:
            break
        matched = _rule_evidence(rule, observation)
        if matched is None:
            continue
        excerpt, source_url, evidence_id = matched
        deduction = min(abs(rule.points), remaining)
        remaining -= deduction
        contributions.append(
            ScoreContribution(
                rule_id=rule.id,
                dimension=rule.dimension,
                points=-deduction,
                excerpt=excerpt,
                source_url=source_url,
                evidence_id=evidence_id,
            )
        )
    return contributions


def score_account(observation: AccountObservation, config: CatalogConfig) -> ScoreResult:
    positive = _positive_contributions(observation, config)
    negative = _negative_contributions(observation, config)
    positive_points = sum(item.points for item in positive)
    negative_points = abs(sum(item.points for item in negative))
    total = max(0, min(100, positive_points - negative_points))
    grade = grade_for_score(total, config.scoring)

    if len(observation.evidence) < 2:
        recommendation = ReviewStatus.NEEDS_REVIEW
        reason = "insufficient_evidence"
    elif grade is LeadGrade.A:
        recommendation = ReviewStatus.APPROVED
        reason = None
    elif grade is LeadGrade.C and negative_points:
        recommendation = ReviewStatus.REJECTED
        reason = "low_fit_or_excluded"
    else:
        recommendation = ReviewStatus.NEEDS_REVIEW
        reason = "operator_review"

    return ScoreResult(
        total=total,
        grade=grade,
        calculation_version=config.scoring.version,
        review_recommendation=recommendation,
        review_reason=reason,
        positive_points=positive_points,
        negative_points=negative_points,
        contributions=[*positive, *negative],
    )

