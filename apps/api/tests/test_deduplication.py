from sqlalchemy.orm import Session

from lead_factory.db import Base, get_engine
from lead_factory.models import SourcePage
from lead_factory.schemas import AccountObservation, EvidenceInput
from lead_factory.services.deduplication import upsert_observation


def test_duplicate_domain_updates_one_account_and_attaches_new_source() -> None:
    engine = get_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    first = AccountObservation(
        display_name="Example Buyer",
        normalized_domain="example.com",
        website_url="https://www.example.com/about",
        description="Foodservice distributor",
        evidence=[
            EvidenceInput(
                id="one",
                signal_type="about",
                excerpt="Foodservice distributor",
                source_url="https://www.example.com/about",
            )
        ],
    )
    second = AccountObservation(
        display_name="Example Buyer Ltd",
        normalized_domain="example.com",
        website_url="https://example.com/products?utm_source=test",
        description="Food packaging products",
        evidence=[
            EvidenceInput(
                id="two",
                signal_type="product",
                excerpt="Food packaging products",
                source_url="https://example.com/products",
            )
        ],
    )

    with Session(engine) as session:
        first_account = upsert_observation(session, first)
        session.commit()
        second_account = upsert_observation(session, second)
        session.commit()

        assert second_account.id == first_account.id
        assert second_account.display_name == "Example Buyer Ltd"
        assert len(second_account.evidence) == 2
        assert session.query(SourcePage).count() == 2
