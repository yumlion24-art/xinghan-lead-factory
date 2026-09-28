from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lead_factory.db import Base, get_engine
from lead_factory.models import Account, ReviewDecision, ReviewStatus


def test_sqlite_creates_all_v1_tables() -> None:
    engine = get_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    assert set(inspect(engine).get_table_names()) == {
        "accounts",
        "evidence",
        "product_matches",
        "review_decisions",
        "score_breakdowns",
        "search_tasks",
        "source_pages",
    }


def test_normalized_domain_is_unique() -> None:
    engine = get_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(Account(display_name="First", normalized_domain="example.com"))
        session.commit()
        session.add(Account(display_name="Duplicate", normalized_domain="example.com"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_review_decisions_retain_history() -> None:
    engine = get_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime(2026, 9, 28, tzinfo=UTC)

    with Session(engine) as session:
        account = Account(display_name="Sky Caterer", normalized_domain="sky.example")
        account.review_status = ReviewStatus.NEEDS_REVIEW
        account.review_decisions.extend(
            [
                ReviewDecision(
                    status=ReviewStatus.NEEDS_REVIEW,
                    note="Evidence is incomplete",
                    actor="operator",
                    created_at=now,
                ),
                ReviewDecision(
                    status=ReviewStatus.APPROVED,
                    note="Procurement page verified",
                    actor="operator",
                    created_at=now,
                ),
            ]
        )
        account.review_status = ReviewStatus.APPROVED
        session.add(account)
        session.commit()
        session.refresh(account)

        assert account.review_status is ReviewStatus.APPROVED
        assert [decision.status for decision in account.review_decisions] == [
            ReviewStatus.NEEDS_REVIEW,
            ReviewStatus.APPROVED,
        ]
        assert account.review_decisions[0].note == "Evidence is incomplete"
