from sqlalchemy import select
from sqlalchemy.orm import Session

from lead_factory.db import Base, get_engine
from lead_factory.demo_seed import DEMO_DOMAIN_SUFFIX, seed_demo
from lead_factory.models import Account, Evidence, LeadGrade, ProductMatch


def test_seed_demo_is_idempotent_and_creates_a_b_c_accounts() -> None:
    engine = get_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        first = seed_demo(session)
        second = seed_demo(session)
        accounts = list(session.scalars(select(Account).where(Account.is_demo.is_(True))))

        assert first.created == 3
        assert second.created == 0
        assert second.existing == 3
        assert {account.grade for account in accounts} == {
            LeadGrade.A,
            LeadGrade.B,
            LeadGrade.C,
        }
        assert all(account.display_name.startswith("[Demo]") for account in accounts)
        assert all(account.normalized_domain.endswith(DEMO_DOMAIN_SUFFIX) for account in accounts)
        assert session.scalar(select(Account).where(Account.normalized_domain == "xhanaero.com")) is None
        assert len(list(session.scalars(select(Evidence)))) >= 3
        assert len(list(session.scalars(select(ProductMatch)))) >= 3
