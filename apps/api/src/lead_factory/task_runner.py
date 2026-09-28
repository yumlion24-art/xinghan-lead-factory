from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from lead_factory.config_loader import CatalogConfig
from lead_factory.models import (
    Evidence,
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
from lead_factory.services.fetcher import Fetcher, FetchError
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
        self._task_semaphore = asyncio.Semaphore(1)

    def enqueue(self, task_id: str) -> None:
        if task_id not in self._running:
            task = asyncio.create_task(self._run_bounded(task_id))
            self._running[task_id] = task
            task.add_done_callback(lambda _: self._running.pop(task_id, None))

    async def _run_bounded(self, task_id: str) -> None:
        async with self._task_semaphore:
            await self.run(task_id)

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

    def _limits(self, task: SearchTask, session: Session) -> BudgetLimits:
        values = task.limits or {}
        crawler = self.catalog.crawler
        today = datetime.now(UTC).date()
        used_today = {"pages": 0, "ai_calls": 0}
        for prior in session.scalars(select(SearchTask)).all():
            if prior.id != task.id and prior.created_at.date() == today:
                used_today["pages"] += int((prior.budget_usage or {}).get("pages", 0))
                used_today["ai_calls"] += int((prior.budget_usage or {}).get("ai_calls", 0))
        return BudgetLimits(
            pages=max(
                0,
                min(
                    int(values.get("max_pages", crawler.max_pages_per_task)),
                    crawler.max_pages_per_task,
                    crawler.daily_page_limit - used_today["pages"],
                ),
            ),
            domains=min(int(values.get("max_domains", crawler.max_domains_per_task)), crawler.max_domains_per_task),
            ai_calls=max(0, crawler.daily_ai_call_limit - used_today["ai_calls"]),
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
            ledger = BudgetLedger(self._limits(task, session))

        try:
            hits = await self.search_provider.search(request)
        except Exception as exc:  # noqa: BLE001 - provider failure is persisted as task failure
            self._finish(task_id, SearchTaskStatus.FAILED, f"search_provider_error: {exc}")
            return

        unique_hits = {}
        for hit in hits:
            try:
                unique_hits.setdefault(normalize_domain(hit.url), hit)
            except ValueError:
                failures_key = hit.url
                unique_hits.setdefault(failures_key, hit)
        hits = list(unique_hits.values())

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
                robots_check = getattr(self.fetcher, "allowed_by_robots", None)
                if robots_check is not None and not await robots_check(
                    safe_url, ledger, self.catalog.crawler.user_agent
                ):
                    raise FetchError("robots policy disallows collection")
                page = await self.fetcher.fetch(safe_url, ledger)
                page_observations = [(page, extract_company(page))]
                max_pages = min(
                    int((task.limits or {}).get("max_pages_per_domain", 1)),
                    self.catalog.crawler.max_pages_per_domain,
                )
                useful_paths = ("about", "product", "solution", "industry", "contact", "sustain", "tender")
                for link in page_observations[0][1].same_domain_links:
                    if len(page_observations) >= max_pages:
                        break
                    if not any(keyword in link.casefold() for keyword in useful_paths):
                        continue
                    linked_safe = self.url_validator(link)
                    linked_page = await self.fetcher.fetch(linked_safe, ledger)
                    page_observations.append((linked_page, extract_company(linked_page)))

                excerpt = " ".join(item.visible_text for _, item in page_observations)[:12000]
                contacts = list(
                    {
                        (route["type"], route["value"]): route
                        for _, item in page_observations
                        for route in item.contact_routes
                    }.values()
                )
                evidence = [
                    EvidenceInput(
                        id=f"{source.content_hash}-content",
                        signal_type="company_page",
                        excerpt=item.visible_text[:4000],
                        source_url=source.final_url,
                    )
                    for source, item in page_observations
                    if item.visible_text
                ]
                if contacts:
                    evidence.append(
                        EvidenceInput(
                            id=f"{page.content_hash}-contact",
                            signal_type="contact",
                            excerpt="Contact us "
                            + " ".join(item["value"] for item in contacts),
                            source_url=page.final_url,
                        )
                    )
                observation = AccountObservation(
                    display_name=(page_observations[0][1].title or safe_url.hostname)[:255],
                    normalized_domain=normalize_domain(page.final_url),
                    website_url=page.final_url,
                    description=excerpt,
                    company_type=excerpt[:255],
                    scale_signals=[term for term in ("international", "multi-site", "fleet") if term in excerpt.casefold()],
                    contact_routes=contacts,
                    evidence=evidence,
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
                    account = upsert_observation(session, observation, search_task_id=task_id)
                    persisted_ids: dict[str, str] = {}
                    for item in observation.evidence:
                        persisted = session.scalar(
                            select(Evidence).where(
                                Evidence.account_id == account.id,
                                Evidence.source_url == item.source_url,
                                Evidence.excerpt == item.excerpt,
                            )
                        )
                        if persisted is not None:
                            persisted_ids[item.id] = persisted.id
                    account.score = score.total
                    account.grade = score.grade
                    account.confidence = max((item.confidence for item in observation.evidence), default=0)
                    account.calculation_version = score.calculation_version
                    account.enrichment_mode = outcome.mode
                    if outcome.ai_result is not None:
                        account.description = (
                            f"{account.description or ''}\n\nAI summary: {outcome.ai_result.summary}"
                        ).strip()
                        account.scale_signals = list(
                            dict.fromkeys(
                                [
                                    *account.scale_signals,
                                    *(f"AI risk: {flag}" for flag in outcome.ai_result.risk_flags),
                                ]
                            )
                        )
                    elif outcome.fallback_reason:
                        account.scale_signals = list(
                            dict.fromkeys(
                                [*account.scale_signals, f"AI fallback: {outcome.fallback_reason}"]
                            )
                        )
                    session.execute(delete(ScoreBreakdown).where(ScoreBreakdown.account_id == account.id))
                    session.execute(delete(ProductMatch).where(ProductMatch.account_id == account.id))
                    ai_reasons = {
                        item.family_id: item.reason
                        for item in (outcome.ai_result.product_matches if outcome.ai_result else [])
                    }
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
                                reason=(
                                    f"{item.reason} AI corroboration: {ai_reasons[item.family_id]}"
                                    if item.family_id in ai_reasons
                                    else item.reason
                                ),
                                confidence=item.confidence,
                                evidence_ids=[
                                    persisted_ids[evidence_id]
                                    for evidence_id in item.evidence_ids
                                    if evidence_id in persisted_ids
                                ],
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
