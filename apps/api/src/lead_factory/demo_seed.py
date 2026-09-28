from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from lead_factory.db import Base, get_engine
from lead_factory.models import (
    Account,
    Evidence,
    LeadGrade,
    ProductMatch,
    ScoreBreakdown,
    SourcePage,
)
from lead_factory.settings import Settings

DEMO_DOMAIN_SUFFIX = ".lead-factory.invalid"


@dataclass(frozen=True)
class SeedSummary:
    created: int
    existing: int


DEMO_ACCOUNTS = (
    {
        "slug": "skymeal-catering",
        "name": "[Demo] SkyMeal Airline Catering",
        "grade": LeadGrade.A,
        "score": 88,
        "country": "United Arab Emirates",
        "industry": "Airline catering",
        "company_type": "Inflight caterer",
        "signal": "Operates airline meal assembly and serves 120 daily flights.",
        "family": "airline_catering",
        "products": ["Airline meal boxes", "Bagasse meal trays", "Cutlery kits"],
    },
    {
        "slug": "greenpack-distribution",
        "name": "[Demo] GreenPack Distribution",
        "grade": LeadGrade.B,
        "score": 67,
        "country": "Germany",
        "industry": "Foodservice packaging",
        "company_type": "Distributor",
        "signal": "Supplies compostable food packaging to regional hospitality buyers.",
        "family": "sustainable_packaging",
        "products": ["Bagasse containers", "PLA cutlery"],
    },
    {
        "slug": "cityserve-supplies",
        "name": "[Demo] CityServe Supplies",
        "grade": LeadGrade.C,
        "score": 39,
        "country": "United Kingdom",
        "industry": "General supplies",
        "company_type": "Wholesaler",
        "signal": "Lists disposable cups and a small foodservice consumables range.",
        "family": "foodservice_packaging",
        "products": ["Paper cups", "Disposable tableware"],
    },
)


def seed_demo(session: Session) -> SeedSummary:
    created = 0
    existing = 0
    for item in DEMO_ACCOUNTS:
        domain = f"{item['slug']}{DEMO_DOMAIN_SUFFIX}"
        found = session.scalar(select(Account).where(Account.normalized_domain == domain))
        if found is not None:
            existing += 1
            continue

        source_url = f"https://{domain}/about"
        account = Account(
            display_name=item["name"],
            normalized_domain=domain,
            website_url=f"https://{domain}",
            country=item["country"],
            industry=item["industry"],
            company_type=item["company_type"],
            description=item["signal"],
            grade=item["grade"],
            score=item["score"],
            confidence=0.82,
            calculation_version="demo-v1",
            enrichment_mode="rules_only",
            is_demo=True,
        )
        session.add(account)
        session.flush()
        page = SourcePage(
            account_id=account.id,
            url=source_url,
            canonical_url=source_url,
            title=f"About {item['name']}",
            retrieval_status="demo_fixture",
            content_hash=f"demo-{item['slug']}",
            extracted_text=item["signal"],
        )
        session.add(page)
        session.flush()
        evidence = Evidence(
            account_id=account.id,
            source_page_id=page.id,
            signal_type="demo_company_fit",
            excerpt=item["signal"],
            source_url=source_url,
            confidence=0.9,
        )
        session.add(evidence)
        session.flush()
        session.add(
            ScoreBreakdown(
                account_id=account.id,
                rule_id="demo-fit",
                dimension="ICP fit",
                points=item["score"],
                excerpt=item["signal"],
                source_url=source_url,
                calculation_version="demo-v1",
            )
        )
        session.add(
            ProductMatch(
                account_id=account.id,
                family_id=item["family"],
                recommended_products=item["products"],
                reason="Demo recommendation derived from the public company-fit signal.",
                confidence=0.84,
                evidence_ids=[evidence.id],
            )
        )
        created += 1
    session.commit()
    return SeedSummary(created=created, existing=existing)


def main() -> None:
    settings = Settings()
    engine = get_engine(settings.database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        summary = seed_demo(session)
    print(f"Demo seed complete: {summary.created} created, {summary.existing} already present.")


if __name__ == "__main__":
    main()
