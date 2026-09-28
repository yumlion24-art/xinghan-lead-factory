from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from lead_factory.config_loader import CatalogConfig
from lead_factory.models import (
    ProductMatch,
    ScoreBreakdown,
    SearchTask,
    SearchTaskStatus,
)
from lead_factory.providers.ai.base import AIProvider, EnrichmentRequest
from lead_factory.providers.search.base import SearchProvider, SearchRequest
from lead_factory.schemas import AccountObservation, EvidenceInput
from lead_factory.services.budgets import BudgetExceeded, BudgetKind, BudgetLedger, BudgetLimits
from lead_factory.services.deduplication import upsert_observation
from lead_factory.services.domain import normalize_domain
from lead_factory.services.enrichment import enrich_or_fallback
from lead_factory.services.extractor import extract_company
from lead_factory.services.fetcher import Fetcher
from lead_factory.services.product_matching import match_products
from lead_factory.services.scoring import score_account
from lead_factory.services.url_safety import SafeUrl, validate_public_url


class TaskRunner:
    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        catalog: CatalogConfig,
        search_provider: SearchProvider,
        fetcher: Fetcher,
        ai_provider: AIProvider,
        url_validator: Callable[[str], SafeUrl] = validate_public_url,
    ) -> None:
        self.session_factory = session_factory
        self.catalog = catalog
        self.search_provider = search_provider
        self.fetcher = fetcher
        self.ai_provider = ai_provider
        self.url_validator = url_validator
        self._running: dict[str, asyncio.Task[None]] = {}

    def enqueue(self, task_id: str) -> None:
        if task_id not in self._running:
            task = asyncio.create_task(self.run(task_id))
            self._running[task_id] = task
            task.add_done_callback(lambda _: self._running.pop(task_id, None))

    def cancel(self, task_id: str) -> None:
        with self.session_factory() as session:
            task = session.get(SearchTask, task_id)
            if task is not None:
                task.cancel_requested = True
                session.commit()

    def recover_interrupted(self) -> int:
        with self.session_factory() as session:
            result = session.execute(
                update(SearchTask)
                .where(SearchTask.status == SearchTaskStatus.RUNNING)
                .values(
                    status=SearchTaskStatus.FAILED,
                    failure_summary="worker_interrupted: application restarted during task",
                    finished_at=datetime.now(UTC),
                )
            )
            session.commit()
            return int(getattr(result, "rowcount", 0) or 0)

    def _limits(self, task: SearchTask) -> BudgetLimits:
        values = task.limits or {}
        crawler = self.catalog.crawler
        return BudgetLimits(
            pages=min(int(values.get("max_pages", crawler.max_pages_per_task)), crawler.max_pages_per_task),
            domains=min(int(values.get("max_domains", crawler.max_domains_per_task)), crawler.max_domains_per_task),
            ai_calls=crawler.daily_ai_call_limit,
            elapsed_seconds=min(
                float(values.get("max_task_seconds", crawler.max_task_seconds)),
                crawler.max_task_seconds,
            ),
        )

    async def run(self, task_id: str) -> None:
        with self.session_factory() as session:
            task = session.get(SearchTask, task_id)
            if task is None:
                return
            if task.cancel_requested:
                task.status = SearchTaskStatus.CANCELLED
                task.finished_at = datetime.now(UTC)
                session.commit()
                return
            task.status = SearchTaskStatus.RUNNING
            task.started_at = datetime.now(UTC)
            task.progress = {"discovered": 0, "processed": 0, "succeeded": 0, "failed": 0}
            session.commit()
            request = SearchRequest(
                query=task.query,
                countries=list(task.countries),
                seed_urls=list(task.seed_urls),
                max_results=int((task.limits or {}).get("max_results", 20)),
            )
            ledger = BudgetLedger(self._limits(task))

        try:
            hits = await self.search_provider.search(request)
        except Exception as exc:  # noqa: BLE001 - provider failure is persisted as task failure
            self._finish(task_id, SearchTaskStatus.FAILED, f"search_provider_error: {exc}")
            return

        failures: list[str] = []
        succeeded = 0
        processed = 0
        with self.session_factory() as session:
            task = session.get(SearchTask, task_id)
            if task is not None:
                task.progress = {"discovered": len(hits), "processed": 0, "succeeded": 0, "failed": 0}
                session.commit()

        for hit in hits:
            with self.session_factory() as session:
                task = session.get(SearchTask, task_id)
                if task is None:
                    return
                if task.cancel_requested:
                    task.status = SearchTaskStatus.CANCELLED
                    task.finished_at = datetime.now(UTC)
                    session.commit()
                    return
            try:
                ledger.consume(BudgetKind.DOMAIN)
                safe_url = self.url_validator(hit.url)
                page = await self.fetcher.fetch(safe_url, ledger)
                page_observation = extract_company(page)
                excerpt = page_observation.visible_text[:4000]
                observation = AccountObservation(
                    display_name=page_observation.title or safe_url.hostname,
                    normalized_domain=normalize_domain(page.final_url),
                    website_url=page.final_url,
                    description=excerpt,
                    company_type=excerpt[:500],
                    scale_signals=[term for term in ("international", "multi-site", "fleet") if term in excerpt.casefold()],
                    contact_routes=page_observation.contact_routes,
                    evidence=[
                        EvidenceInput(
                            id=f"{page.content_hash}-content",
                            signal_type="company_page",
                            excerpt=excerpt,
                            source_url=page.final_url,
                        ),
                        EvidenceInput(
                            id=f"{page.content_hash}-contact",
                            signal_type="contact",
                            excerpt="Contact us " + " ".join(item["value"] for item in page_observation.contact_routes),
                            source_url=page.final_url,
                        ),
                    ],
                )
                score = score_account(observation, self.catalog)
                matches = match_products(observation, self.catalog)
                outcome = await enrich_or_fallback(
                    self.ai_provider,
                    EnrichmentRequest(
                        observation=observation,
                        deterministic_score=score.total,
                        deterministic_grade=score.grade,
                        deterministic_product_matches=matches,
                        prompt_version="company_enrichment-v1",
                    ),
                    ledger,
                )
                with self.session_factory() as session:
                    account = upsert_observation(session, observation)
                    account.score = score.total
                    account.grade = score.grade
                    account.confidence = max((item.confidence for item in observation.evidence), default=0)
                    account.calculation_version = score.calculation_version
                    account.enrichment_mode = outcome.mode
                    session.execute(delete(ScoreBreakdown).where(ScoreBreakdown.account_id == account.id))
                    session.execute(delete(ProductMatch).where(ProductMatch.account_id == account.id))
                    session.add_all(
                        [
                            ScoreBreakdown(
                                account=account,
                                rule_id=item.rule_id,
                                dimension=item.dimension,
                                points=item.points,
                                excerpt=item.excerpt,
                                source_url=item.source_url,
                                calculation_version=score.calculation_version,
                            )
                            for item in score.contributions
                        ]
                    )
                    session.add_all(
                        [
                            ProductMatch(
                                account=account,
                                family_id=item.family_id,
                                recommended_products=item.recommended_products,
                                reason=item.reason,
                                confidence=item.confidence,
                                evidence_ids=item.evidence_ids,
                            )
                            for item in matches
                        ]
                    )
                    session.commit()
                succeeded += 1
            except BudgetExceeded as exc:
                failures.append(str(exc))
                break
            except Exception as exc:  # noqa: BLE001 - one domain must not discard other results
                failures.append(f"{hit.url}: {exc}")
            finally:
                processed += 1
                self._progress(task_id, len(hits), processed, succeeded, len(failures), ledger)

        if failures and succeeded:
            status = SearchTaskStatus.PARTIALLY_COMPLETED
        elif failures:
            status = SearchTaskStatus.FAILED
        else:
            status = SearchTaskStatus.COMPLETED
        self._finish(task_id, status, "\n".join(failures) or None, ledger)

    def _progress(
        self,
        task_id: str,
        discovered: int,
        processed: int,
        succeeded: int,
        failed: int,
        ledger: BudgetLedger,
    ) -> None:
        with self.session_factory() as session:
            task = session.get(SearchTask, task_id)
            if task is not None:
                task.progress = {
                    "discovered": discovered,
                    "processed": processed,
                    "succeeded": succeeded,
                    "failed": failed,
                }
                task.budget_usage = ledger.snapshot()
                session.commit()

    def _finish(
        self,
        task_id: str,
        status: SearchTaskStatus,
        failure_summary: str | None,
        ledger: BudgetLedger | None = None,
    ) -> None:
        with self.session_factory() as session:
            task = session.get(SearchTask, task_id)
            if task is not None:
                task.status = status
                task.failure_summary = failure_summary
                task.finished_at = datetime.now(UTC)
                if ledger is not None:
                    task.budget_usage = ledger.snapshot()
                session.commit()
