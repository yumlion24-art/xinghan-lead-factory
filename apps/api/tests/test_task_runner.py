from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from lead_factory.config_loader import load_catalog
from lead_factory.db import Base, get_engine
from lead_factory.models import Account, SearchTask, SearchTaskStatus
from lead_factory.providers.ai.disabled import DisabledAIProvider
from lead_factory.providers.search.base import SearchHit, SearchRequest
from lead_factory.services.fetcher import FetchError, FetchResult
from lead_factory.services.url_safety import SafeUrl
from lead_factory.task_runner import TaskRunner


class StaticSearchProvider:
    def __init__(self, urls: list[str]) -> None:
        self.urls = urls

    async def search(self, request: SearchRequest) -> list[SearchHit]:
        return [SearchHit(url=url, source="fixture") for url in self.urls[: request.max_results]]


class FixtureFetcher:
    def __init__(self, failing_url: str | None = None) -> None:
        self.failing_url = failing_url

    async def fetch(self, safe_url: SafeUrl, budget) -> FetchResult:
        if safe_url.url == self.failing_url:
            raise FetchError("fixture fetch failed")
        html = f"""
        <html><head><title>Sky Meals International</title></head>
        <body><h1>International inflight catering</h1>
        <p>Airline meal tray procurement, private label OEM, multi-site operations.</p>
        <a href=\"mailto:buying@{safe_url.hostname}\">Contact us</a>
        </body></html>
        """.encode()
        return FetchResult(
            status_code=200,
            headers={"content-type": "text/html"},
            content=html,
            final_url=safe_url.url,
            text=html.decode(),
            content_hash="fixture-hash",
        )


def safe(url: str) -> SafeUrl:
    hostname = url.split("//", 1)[1].split("/", 1)[0]
    return SafeUrl(url=url, hostname=hostname, resolved_ips=("93.184.216.34",))


@pytest.fixture
def runner_setup(config_dir: Path):
    engine = get_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)

    def make_runner(urls, failing_url=None):
        return TaskRunner(
            session_factory=sessions,
            catalog=load_catalog(config_dir),
            search_provider=StaticSearchProvider(urls),
            fetcher=FixtureFetcher(failing_url),
            ai_provider=DisabledAIProvider(),
            url_validator=safe,
        )

    return sessions, make_runner


@pytest.mark.asyncio
async def test_seeded_task_persists_state_before_and_after_execution(runner_setup) -> None:
    sessions, make_runner = runner_setup
    with sessions() as session:
        task = SearchTask(
            query="airline catering",
            seed_urls=["https://sky.example"],
            limits={"max_results": 5, "max_domains": 5, "max_pages_per_domain": 1},
        )
        session.add(task)
        session.commit()
        task_id = task.id
        assert task.status is SearchTaskStatus.QUEUED

    await make_runner(["https://sky.example"]).run(task_id)

    with sessions() as session:
        task = session.get(SearchTask, task_id)
        account = session.scalar(select(Account))
        assert task is not None and task.status is SearchTaskStatus.COMPLETED
        assert task.progress == {"discovered": 1, "processed": 1, "succeeded": 1, "failed": 0}
        assert account is not None
        assert account.grade is not None
        assert account.score >= 75
        assert len(account.score_breakdowns) > 0


@pytest.mark.asyncio
async def test_one_failed_domain_keeps_success_and_marks_partial(runner_setup) -> None:
    sessions, make_runner = runner_setup
    urls = ["https://good.example", "https://bad.example"]
    with sessions() as session:
        task = SearchTask(query="catering", seed_urls=urls, limits={"max_results": 5, "max_domains": 5})
        session.add(task)
        session.commit()
        task_id = task.id

    await make_runner(urls, "https://bad.example").run(task_id)

    with sessions() as session:
        task = session.get(SearchTask, task_id)
        assert task is not None and task.status is SearchTaskStatus.PARTIALLY_COMPLETED
        assert task.progress["succeeded"] == 1
        assert task.progress["failed"] == 1
        assert "bad.example" in (task.failure_summary or "")
        assert session.query(Account).count() == 1


@pytest.mark.asyncio
async def test_domain_budget_exhaustion_is_partial_and_retains_first_account(runner_setup) -> None:
    sessions, make_runner = runner_setup
    urls = ["https://first.example", "https://second.example"]
    with sessions() as session:
        task = SearchTask(query="catering", seed_urls=urls, limits={"max_results": 5, "max_domains": 1})
        session.add(task)
        session.commit()
        task_id = task.id

    await make_runner(urls).run(task_id)

    with sessions() as session:
        task = session.get(SearchTask, task_id)
        assert task is not None and task.status is SearchTaskStatus.PARTIALLY_COMPLETED
        assert task.progress["succeeded"] == 1
        assert "domains budget exhausted" in (task.failure_summary or "")
        assert session.query(Account).count() == 1


@pytest.mark.asyncio
async def test_cancelled_task_stops_before_first_fetch(runner_setup) -> None:
    sessions, make_runner = runner_setup
    with sessions() as session:
        task = SearchTask(query="catering", seed_urls=["https://sky.example"])
        session.add(task)
        session.commit()
        task_id = task.id

    runner = make_runner(["https://sky.example"])
    runner.cancel(task_id)
    await runner.run(task_id)

    with sessions() as session:
        task = session.get(SearchTask, task_id)
        assert task is not None and task.status is SearchTaskStatus.CANCELLED
        assert session.query(Account).count() == 0


def test_recovery_marks_interrupted_running_tasks_failed(runner_setup) -> None:
    sessions, make_runner = runner_setup
    with sessions() as session:
        task = SearchTask(query="catering", status=SearchTaskStatus.RUNNING)
        session.add(task)
        session.commit()
        task_id = task.id

    recovered = make_runner([]).recover_interrupted()

    with sessions() as session:
        task = session.get(SearchTask, task_id)
        assert recovered == 1
        assert task is not None and task.status is SearchTaskStatus.FAILED
        assert task.failure_summary == "worker_interrupted: application restarted during task"

