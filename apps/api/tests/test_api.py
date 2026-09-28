from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from lead_factory.db import Base, get_engine
from lead_factory.main import create_app
from lead_factory.models import Account, LeadGrade, SearchTask, SearchTaskStatus
from lead_factory.settings import Settings


class RecordingRunner:
    def __init__(self) -> None:
        self.enqueued: list[str] = []
        self.cancelled: list[str] = []

    def enqueue(self, task_id: str) -> None:
        self.enqueued.append(task_id)

    def cancel(self, task_id: str) -> None:
        self.cancelled.append(task_id)

    def recover_interrupted(self) -> int:
        return 0


@pytest.fixture
def api(config_dir: Path):
    engine = get_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    runner = RecordingRunner()
    app = create_app(
        settings=Settings(_env_file=None, config_dir=config_dir, database_url="sqlite+pysqlite:///:memory:"),
        engine=engine,
        runner=runner,
    )
    with Session(engine) as session:
        session.add_all(
            [
                Account(
                    display_name="A Buyer",
                    normalized_domain="a.example",
                    website_url="https://a.example",
                    country="UAE",
                    grade=LeadGrade.A,
                    score=88,
                ),
                Account(
                    display_name="B Buyer",
                    normalized_domain="b.example",
                    website_url="https://b.example",
                    country="UK",
                    grade=LeadGrade.B,
                    score=63,
                    is_demo=True,
                ),
            ]
        )
        session.commit()
    with TestClient(app) as client:
        yield client, engine, runner


def test_health_readiness_and_dashboard(api) -> None:
    client, _, _ = api

    assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert client.get("/api/v1/readiness").json()["status"] == "ready"
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["accounts_total"] == 2
    assert dashboard["grades"] == {"A": 1, "B": 1, "C": 0}


def test_account_list_filters_paginates_and_sorts(api) -> None:
    client, _, _ = api

    response = client.get("/api/v1/accounts", params={"grade": "A", "sort": "score_desc"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["display_name"] == "A Buyer"


def test_validation_and_not_found_use_request_id_error_envelope(api) -> None:
    client, _, _ = api

    invalid = client.get("/api/v1/accounts?page_size=101")
    missing = client.get("/api/v1/accounts/missing")

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert invalid.json()["error"]["request_id"]
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "account_not_found"
    assert missing.json()["error"]["request_id"]


def test_review_action_updates_latest_status_and_retains_history(api) -> None:
    client, engine, _ = api
    with Session(engine) as session:
        account_id = session.query(Account).filter(Account.normalized_domain == "a.example").one().id

    first = client.post(
        f"/api/v1/accounts/{account_id}/review",
        json={"status": "needs_review", "note": "Check procurement evidence"},
    )
    second = client.post(
        f"/api/v1/accounts/{account_id}/review",
        json={"status": "approved", "note": "Evidence verified"},
    )
    detail = client.get(f"/api/v1/accounts/{account_id}").json()

    assert first.status_code == 201 and second.status_code == 201
    assert detail["review_status"] == "approved"
    assert [item["status"] for item in detail["review_history"]] == [
        "needs_review",
        "approved",
    ]


def test_search_task_is_persisted_before_enqueue_and_can_be_cancelled(api) -> None:
    client, engine, runner = api

    created = client.post(
        "/api/v1/search-tasks",
        json={
            "query": "airline catering UAE",
            "countries": ["UAE"],
            "icp_ids": ["aviation_catering"],
            "seed_urls": ["https://example.com"],
            "max_results": 10,
            "max_pages_per_domain": 2,
        },
    )
    task_id = created.json()["id"]

    with Session(engine) as session:
        task = session.get(SearchTask, task_id)
        assert task is not None and task.status is SearchTaskStatus.QUEUED
    assert runner.enqueued == [task_id]

    cancelled = client.post(f"/api/v1/search-tasks/{task_id}/cancel")
    assert cancelled.status_code == 202
    assert runner.cancelled == [task_id]
