from pathlib import Path

from lead_factory.config_loader import load_catalog
from lead_factory.models import LeadGrade, ReviewStatus
from lead_factory.schemas import AccountObservation, EvidenceInput
from lead_factory.services.scoring import grade_for_score, score_account


def evidence(identifier: str, excerpt: str) -> EvidenceInput:
    return EvidenceInput(
        id=identifier,
        signal_type="official_site",
        excerpt=excerpt,
        source_url=f"https://buyer.example/{identifier}",
    )


def test_airline_caterer_scores_a_with_explainable_evidence(config_dir: Path) -> None:
    result = score_account(
        AccountObservation(
            display_name="Global Sky Catering",
            normalized_domain="globalsky.example",
            website_url="https://globalsky.example",
            country="United States",
            company_type="international inflight catering company",
            description="Airline catering procurement and sourcing for a nationwide fleet.",
            scale_signals=["international", "multi-site"],
            contact_routes=[{"type": "email", "value": "buying@globalsky.example"}],
            evidence=[
                evidence("products", "Products include inflight meal tray and cutlery kit programs."),
                evidence("contact", "Contact us about private label OEM procurement."),
            ],
        ),
        load_catalog(config_dir),
    )

    assert result.total == 100
    assert result.grade is LeadGrade.A
    assert result.review_recommendation is ReviewStatus.APPROVED
    assert {item.dimension for item in result.contributions} == {
        "icp_fit",
        "product_demand",
        "scale",
        "geography",
        "intent",
        "evidence",
    }
    meal_rule = next(item for item in result.contributions if item.rule_id == "demand-airline-meals")
    assert meal_rule.evidence_id == "products"
    assert meal_rule.source_url == "https://buyer.example/products"


def test_foodservice_distributor_scores_b(config_dir: Path) -> None:
    result = score_account(
        AccountObservation(
            display_name="Metro Pack Supply",
            normalized_domain="metropack.example",
            website_url="https://metropack.example",
            country="United Kingdom",
            company_type="foodservice distributor",
            description="Food container and food packaging catalogue.",
            evidence=[
                evidence("products", "Products for restaurant supply: food container ranges."),
                evidence("about", "About us and contact us for trade accounts."),
            ],
        ),
        load_catalog(config_dir),
    )

    assert result.total == 64
    assert result.grade is LeadGrade.B


def test_irrelevant_consumer_shop_scores_c(config_dir: Path) -> None:
    result = score_account(
        AccountObservation(
            display_name="Corner Cafe",
            normalized_domain="cornercafe.example",
            website_url="https://cornercafe.example",
            description="Local cafe. Book a table or order one meal.",
            evidence=[evidence("home", "Book a table at our local cafe.")],
        ),
        load_catalog(config_dir),
    )

    assert result.total == 0
    assert result.grade is LeadGrade.C
    assert result.negative_points == 25


def test_negative_deductions_are_capped_at_40(config_dir: Path) -> None:
    result = score_account(
        AccountObservation(
            display_name="Wrong Fit Factory",
            normalized_domain="wrongfit.example",
            website_url="https://wrongfit.example",
            description="We manufacture packaging in our packaging factory and run flight training.",
            evidence=[evidence("about", "Packaging manufacturer and flight training business.")],
        ),
        load_catalog(config_dir),
    )

    assert result.negative_points == 40
    assert sum(item.points for item in result.contributions if item.points < 0) == -40


def test_grade_boundaries_are_exact(config_dir: Path) -> None:
    scoring = load_catalog(config_dir).scoring

    assert grade_for_score(75, scoring) is LeadGrade.A
    assert grade_for_score(74, scoring) is LeadGrade.B
    assert grade_for_score(55, scoring) is LeadGrade.B
    assert grade_for_score(54, scoring) is LeadGrade.C
    assert grade_for_score(0, scoring) is LeadGrade.C


def test_insufficient_evidence_requires_review(config_dir: Path) -> None:
    result = score_account(
        AccountObservation(
            display_name="Possible Airline Buyer",
            normalized_domain="possible.example",
            website_url="https://possible.example",
            country="UAE",
            description="International airline catering procurement for meal tray sourcing.",
            scale_signals=["international"],
            evidence=[evidence("home", "Airline meal tray procurement.")],
        ),
        load_catalog(config_dir),
    )

    assert result.grade is LeadGrade.A
    assert result.review_recommendation is ReviewStatus.NEEDS_REVIEW
    assert result.review_reason == "insufficient_evidence"


def test_short_acronym_does_not_match_inside_unrelated_word(config_dir: Path) -> None:
    result = score_account(
        AccountObservation(
            display_name="Playground Operator",
            normalized_domain="playground.example",
            website_url="https://playground.example",
            description="We operate a playground platform.",
            evidence=[evidence("home", "We operate a playground platform.")],
        ),
        load_catalog(config_dir),
    )

    assert all(item.rule_id != "demand-sustainable-materials" for item in result.contributions)
