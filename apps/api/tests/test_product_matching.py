from pathlib import Path

from lead_factory.config_loader import load_catalog
from lead_factory.schemas import AccountObservation, EvidenceInput
from lead_factory.services.product_matching import match_products


def test_sustainable_signals_match_bagasse_and_pla_only(config_dir: Path) -> None:
    observation = AccountObservation(
        display_name="Eco Catering Imports",
        normalized_domain="ecocatering.example",
        website_url="https://ecocatering.example",
        company_type="sustainable packaging importer",
        description="We distribute compostable packaging to foodservice operators.",
        evidence=[
            EvidenceInput(
                id="catalog",
                signal_type="product",
                excerpt="Our buyers source bagasse meal trays and PLA cutlery kits.",
                source_url="https://ecocatering.example/catalog",
            )
        ],
    )

    matches = match_products(observation, load_catalog(config_dir))

    sustainable = next(item for item in matches if item.family_id == "sustainable_packaging")
    assert sustainable.recommended_products == [
        "Bagasse meal trays",
        "PLA and wooden cutlery kits",
        "PLA-coated cups and PLA/PBAT bags",
    ]
    assert sustainable.evidence_ids == ["catalog"]
    assert sustainable.confidence >= 0.8
    assert all(item.family_id != "airline_airport" for item in matches)
    assert all("Boarding" not in product for item in matches for product in item.recommended_products)


def test_product_matches_never_claim_unseen_evidence(config_dir: Path) -> None:
    observation = AccountObservation(
        display_name="Generic Trading",
        normalized_domain="generic.example",
        website_url="https://generic.example",
        description="International sourcing company.",
        evidence=[],
    )

    assert match_products(observation, load_catalog(config_dir)) == []


def test_product_match_does_not_match_pla_inside_playground(config_dir: Path) -> None:
    observation = AccountObservation(
        display_name="Playground Operator",
        normalized_domain="playground.example",
        website_url="https://playground.example",
        evidence=[
            EvidenceInput(
                id="home",
                signal_type="official_site",
                excerpt="We operate a playground platform.",
                source_url="https://playground.example",
            )
        ],
    )

    assert match_products(observation, load_catalog(config_dir)) == []
