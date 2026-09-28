# Xinghan Lead Factory V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows-local B2B account discovery, evidence collection, explainable scoring, product matching, and review application for Guangdong Xinghan Industrial Co., Ltd., without automated outreach.

**Architecture:** A Next.js web client consumes a versioned FastAPI API. The API owns SQLAlchemy persistence, YAML configuration, bounded collection, domain deduplication, deterministic scoring, optional schema-validated AI enrichment, and a persisted in-process task runner. SQLite is the default database and PostgreSQL is selected only through `DATABASE_URL`.

**Tech Stack:** Python 3.12+, uv, FastAPI, Pydantic Settings, SQLAlchemy 2, Alembic, HTTPX, BeautifulSoup, tldextract, PyYAML, structlog, pytest; Node.js 20+, Next.js 16, React 19, TypeScript, TanStack Query, Vitest, Testing Library, Playwright; SQLite/PostgreSQL.

**Spec:** `docs/superpowers/specs/2026-09-28-xinghan-lead-factory-v1-design.md`

## Global Constraints

- Windows local operation is the primary delivery environment; commands must work in PowerShell.
- Core discovery, rules scoring, product matching, review, and demo operation must run without an AI API key.
- SQLite is the default; PostgreSQL must work by changing `DATABASE_URL` only.
- The application may collect public HTTP/HTTPS pages only and must not bypass authentication, paywalls, CAPTCHAs, or access restrictions.
- Automated email, WhatsApp, social messaging, and all other outbound communication are out of scope.
- Default live collection permits one active request per domain and enforces configured delay, timeout, response-size, redirect, page, task, daily, and AI budgets.
- Scores are deterministic and explainable: every contribution references a rule ID, points, excerpt, URL, and calculation version.
- Grades are A = 75-100, B = 55-74, and C = 0-54; manual review status remains independent of grade.
- AI output may add evidence-backed suggestions but may not silently override deterministic score rules.
- Synthetic demo records must always be visibly labelled and must never appear as real newly discovered leads.

## Review Focus

1. A URL that redirects or resolves to loopback, private, link-local, reserved, or metadata IP space must be blocked before content is read; Task 3 tests initial and post-redirect resolution.
2. Mixed-case, `www`, Unicode/punycode, paths, and tracking parameters for the same registrable domain must resolve to one account; Task 3 tests canonicalization and duplicate observation attachment.
3. A task reaching page, elapsed-time, daily, or AI limits must stop cleanly, retain collected accounts, and report partial completion rather than corrupting state; Tasks 3 and 5 test this transition.
4. Missing keys, timeouts, malformed JSON, invented evidence references, and provider errors must fall back to rules-only results without failing the task; Task 4 tests every fallback class.
5. One domain failing fetch or parse must not discard successful domains from the same task; Task 5 tests per-domain isolation, progress counters, and the `partially_completed` result.

---

### Task 1: Backend Foundation, Configuration, and Persistence

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/versions/0001_initial.py`
- Create: `apps/api/src/lead_factory/__init__.py`
- Create: `apps/api/src/lead_factory/settings.py`
- Create: `apps/api/src/lead_factory/config_loader.py`
- Create: `apps/api/src/lead_factory/logging.py`
- Create: `apps/api/src/lead_factory/db.py`
- Create: `apps/api/src/lead_factory/models.py`
- Create: `apps/api/src/lead_factory/schemas.py`
- Create: `apps/api/tests/conftest.py`
- Create: `apps/api/tests/test_settings.py`
- Create: `apps/api/tests/test_logging.py`
- Create: `apps/api/tests/test_persistence.py`
- Create: `config/products.yaml`
- Create: `config/icp.yaml`
- Create: `config/scoring.yaml`
- Create: `config/crawler.yaml`
- Create: `.env.example`

**Interfaces:**
- Consumes: design sections 3-7 and 12.
- Produces: `Settings`, `load_catalog(config_dir: Path) -> CatalogConfig`, `configure_logging(settings: Settings) -> None`, `get_engine(database_url: str) -> Engine`, `session_scope() -> Iterator[Session]`, SQLAlchemy entities `Account`, `SourcePage`, `Evidence`, `SearchTask`, `ScoreBreakdown`, `ProductMatch`, and `ReviewDecision`, plus Pydantic request/response schemas used by later tasks.

- [ ] **Step 1: Write failing configuration and persistence tests**

Test that the checked-in YAML loads four product families, grades have boundaries 75/55/0, invalid weights fail with a field-level message, structured JSON logs include timestamp/level/component/event/request ID while redacting configured secrets, SQLite creates all tables, normalized domain uniqueness rejects a second account, and review decisions retain history.

- [ ] **Step 2: Verify the tests fail because the backend package and schema do not exist**

Run: `uv run --project apps/api pytest apps/api/tests/test_settings.py apps/api/tests/test_logging.py apps/api/tests/test_persistence.py -v`

Expected: collection/import failure for `lead_factory`.

- [ ] **Step 3: Implement configuration models, settings, database lifecycle, entities, initial migration, and the four Xinghan configuration files**

Use SQLAlchemy 2 typed mappings, UTC timestamps, explicit enums, JSON columns only for bounded structured metadata, and portable column types accepted by SQLite and PostgreSQL.

- [ ] **Step 4: Run focused and full backend tests**

Run: `uv run --project apps/api pytest apps/api/tests/test_settings.py apps/api/tests/test_logging.py apps/api/tests/test_persistence.py -v`

Expected: all tests pass with no warnings.

- [ ] **Step 5: Commit the foundation**

```powershell
git add apps/api config .env.example
git commit -m "feat: add lead factory backend foundation"
```

### Task 2: Explainable Scoring and Product Matching

**Files:**
- Create: `apps/api/src/lead_factory/services/scoring.py`
- Create: `apps/api/src/lead_factory/services/product_matching.py`
- Create: `apps/api/tests/test_scoring.py`
- Create: `apps/api/tests/test_product_matching.py`
- Modify: `config/products.yaml`
- Modify: `config/icp.yaml`
- Modify: `config/scoring.yaml`

**Interfaces:**
- Consumes: `CatalogConfig`, account observations, and persistence schemas from Task 1.
- Produces: `score_account(observation: AccountObservation, config: CatalogConfig) -> ScoreResult` and `match_products(observation: AccountObservation, config: CatalogConfig) -> list[ProductMatchResult]` where `ScoreResult` contains total, grade, calculation version, review recommendation, and rule contributions with evidence references.

- [ ] **Step 1: Write failing tests for score boundaries, negative caps, evidence, and product matches**

Include an airline caterer scoring A with meal-tray evidence, a foodservice distributor scoring B, an irrelevant consumer shop scoring C, exact 75/55 boundaries, deductions capped at 40, insufficient evidence yielding Needs Review, and sustainable signals matching bagasse/PLA products without matching unrelated boarding passes.

- [ ] **Step 2: Verify the scoring tests fail for missing service modules**

Run: `uv run --project apps/api pytest apps/api/tests/test_scoring.py apps/api/tests/test_product_matching.py -v`

Expected: import failure for `lead_factory.services.scoring` and `product_matching`.

- [ ] **Step 3: Implement normalized text signal evaluation and deterministic product matching**

Keep rule IDs and weights in YAML. Match only excerpts already present in `AccountObservation`; never fabricate evidence or add points from an unsupported label.

- [ ] **Step 4: Run the focused tests and full backend suite**

Run: `uv run --project apps/api pytest apps/api/tests/test_scoring.py apps/api/tests/test_product_matching.py -v`

Run: `uv run --project apps/api pytest -q`

Expected: both commands exit 0.

- [ ] **Step 5: Commit scoring and matching**

```powershell
git add apps/api/src/lead_factory/services apps/api/tests config
git commit -m "feat: add explainable lead scoring and product matching"
```

### Task 3: Safe Collection, Extraction, Budgets, and Deduplication

**Files:**
- Create: `apps/api/src/lead_factory/services/url_safety.py`
- Create: `apps/api/src/lead_factory/services/domain.py`
- Create: `apps/api/src/lead_factory/services/robots.py`
- Create: `apps/api/src/lead_factory/services/fetcher.py`
- Create: `apps/api/src/lead_factory/services/extractor.py`
- Create: `apps/api/src/lead_factory/services/budgets.py`
- Create: `apps/api/src/lead_factory/services/deduplication.py`
- Create: `apps/api/src/lead_factory/providers/search/base.py`
- Create: `apps/api/src/lead_factory/providers/search/seed.py`
- Create: `apps/api/src/lead_factory/providers/search/public_search.py`
- Create: `apps/api/tests/fixtures/company_sites/`
- Create: `apps/api/tests/test_url_safety.py`
- Create: `apps/api/tests/test_domain.py`
- Create: `apps/api/tests/test_collection.py`
- Create: `apps/api/tests/test_budgets.py`
- Create: `apps/api/tests/test_deduplication.py`
- Modify: `config/crawler.yaml`

**Interfaces:**
- Consumes: settings, entities, and `AccountObservation` from Task 1.
- Produces: `validate_public_url(url: str, resolver: Resolver) -> SafeUrl`, `normalize_domain(url: str) -> str`, `Fetcher.fetch(url: SafeUrl, budget: BudgetLedger) -> FetchResult`, `extract_company(page: FetchResult) -> CompanyPageObservation`, `BudgetLedger.consume(kind: BudgetKind, amount: int = 1) -> None`, `upsert_observation(session: Session, observation: AccountObservation) -> Account`, and async `SearchProvider.search(request: SearchRequest) -> list[SearchHit]` implementations for seed URLs and light no-key public search.

- [ ] **Step 1: Write failing safety, normalization, budget, collection, and deduplication tests**

Cover direct and redirected private IPs, DNS rebinding between validation and connection, invalid schemes, oversized/decompression responses, robots denial, per-domain delay, transient retry caps, registrable-domain normalization including IDN, content hashing, duplicate attachment, and every configured budget exhaustion path.

- [ ] **Step 2: Verify all new tests fail because collection services are absent**

Run: `uv run --project apps/api pytest apps/api/tests/test_url_safety.py apps/api/tests/test_domain.py apps/api/tests/test_collection.py apps/api/tests/test_budgets.py apps/api/tests/test_deduplication.py -v`

Expected: import failures for the new services.

- [ ] **Step 3: Implement the safe collector and deterministic fixture-backed adapters**

Pin the resolved public address through each request, revalidate redirects, stream responses up to the configured byte limit, accept HTML only, use same-domain link discovery, store bounded visible text, and isolate search-provider details behind `SearchProvider`.

- [ ] **Step 4: Run focused tests and the backend suite**

Run: `uv run --project apps/api pytest apps/api/tests/test_url_safety.py apps/api/tests/test_domain.py apps/api/tests/test_collection.py apps/api/tests/test_budgets.py apps/api/tests/test_deduplication.py -v`

Run: `uv run --project apps/api pytest -q`

Expected: both commands exit 0 without live network access.

- [ ] **Step 5: Commit collection services**

```powershell
git add apps/api/src/lead_factory/services apps/api/src/lead_factory/providers apps/api/tests config/crawler.yaml
git commit -m "feat: add safe public web collection"
```

### Task 4: Optional AI Enrichment with Rules-Only Fallback

**Files:**
- Create: `apps/api/src/lead_factory/providers/ai/base.py`
- Create: `apps/api/src/lead_factory/providers/ai/disabled.py`
- Create: `apps/api/src/lead_factory/providers/ai/openai_provider.py`
- Create: `apps/api/src/lead_factory/services/enrichment.py`
- Create: `apps/api/tests/test_enrichment.py`
- Create: `config/prompts/company_enrichment-v1.md`
- Modify: `.env.example`

**Interfaces:**
- Consumes: `AccountObservation`, evidence identifiers, product configuration, `BudgetLedger`, and scoring/matching results.
- Produces: async `AIProvider.enrich(request: EnrichmentRequest) -> EnrichmentResult` and `enrich_or_fallback(provider: AIProvider, request: EnrichmentRequest, budget: BudgetLedger) -> EnrichmentOutcome`; the outcome always contains a mode (`ai` or `rules_only`), validated evidence references, usage/cost fields, and a safe fallback reason.

- [ ] **Step 1: Write failing tests for successful enrichment and all fallbacks**

Test no key, provider timeout, provider exception, malformed JSON, missing required fields, evidence IDs not present in the request, and exhausted AI budget. Assert that each returns the original deterministic score/matches, `rules_only`, and a categorized reason; valid structured output may enrich summary and match explanations but not score contributions.

- [ ] **Step 2: Verify the tests fail for missing AI provider interfaces**

Run: `uv run --project apps/api pytest apps/api/tests/test_enrichment.py -v`

Expected: import failure for `lead_factory.services.enrichment`.

- [ ] **Step 3: Implement provider selection, strict schema validation, usage logging, and fallback**

Keep the prompt versioned, send only bounded public text, never log secrets, and use the official provider client only inside `openai_provider.py`.

- [ ] **Step 4: Run focused and full backend tests**

Run: `uv run --project apps/api pytest apps/api/tests/test_enrichment.py -v`

Run: `uv run --project apps/api pytest -q`

Expected: both commands exit 0.

- [ ] **Step 5: Commit AI enhancement**

```powershell
git add apps/api config/prompts .env.example
git commit -m "feat: add optional AI account enrichment"
```

### Task 5: Search Task Runner and Versioned API

**Files:**
- Create: `apps/api/src/lead_factory/task_runner.py`
- Create: `apps/api/src/lead_factory/api/errors.py`
- Create: `apps/api/src/lead_factory/api/dependencies.py`
- Create: `apps/api/src/lead_factory/api/health.py`
- Create: `apps/api/src/lead_factory/api/dashboard.py`
- Create: `apps/api/src/lead_factory/api/accounts.py`
- Create: `apps/api/src/lead_factory/api/search_tasks.py`
- Create: `apps/api/src/lead_factory/api/configuration.py`
- Create: `apps/api/src/lead_factory/main.py`
- Create: `apps/api/tests/test_task_runner.py`
- Create: `apps/api/tests/test_api.py`

**Interfaces:**
- Consumes: all backend interfaces from Tasks 1-4.
- Produces: `TaskRunner.enqueue(task_id: UUID) -> None`, `TaskRunner.cancel(task_id: UUID) -> None`, async `TaskRunner.run(task_id: UUID) -> None`, and `/api/v1` endpoints for health, readiness, dashboard, accounts, review decisions, search tasks, cancellation, and display-safe configuration.

- [ ] **Step 1: Write failing task-runner and API contract tests**

Test a full seeded task, task state persisted before execution, cancellation between fetches, one failed domain producing partial completion with successful accounts retained, budget exhaustion producing partial completion, restart recovery of `running` tasks to `failed` with an interruption code, list pagination maximums, filters/sorts, review history, 404s, validation errors, and the request-ID error envelope.

- [ ] **Step 2: Verify the tests fail for missing runner and app**

Run: `uv run --project apps/api pytest apps/api/tests/test_task_runner.py apps/api/tests/test_api.py -v`

Expected: import failure for `TaskRunner` and `lead_factory.main`.

- [ ] **Step 3: Implement orchestration and the API**

Use FastAPI lifespan to initialize configuration, logging, database readiness, and one bounded in-process worker. Persist progress after each domain. API responses must use Pydantic DTOs and never serialize ORM instances directly.

- [ ] **Step 4: Run backend verification**

Run: `uv run --project apps/api pytest -q`

Run: `uv run --project apps/api ruff check .`

Run: `uv run --project apps/api pyright apps/api/src`

Expected: every command exits 0.

- [ ] **Step 5: Commit the backend API**

```powershell
git add apps/api
git commit -m "feat: add search task orchestration and API"
```

### Task 6: Web Foundation, Dashboard, and Account Lists

**Files:**
- Create: `package.json`
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/globals.css`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/app/accounts/page.tsx`
- Create: `apps/web/src/app/leads/[grade]/page.tsx`
- Create: `apps/web/src/components/app-shell.tsx`
- Create: `apps/web/src/components/dashboard.tsx`
- Create: `apps/web/src/components/account-table.tsx`
- Create: `apps/web/src/components/status-badge.tsx`
- Create: `apps/web/src/lib/api-client.ts`
- Create: `apps/web/src/lib/types.ts`
- Create: `apps/web/src/test/setup.ts`
- Create: `apps/web/src/components/dashboard.test.tsx`
- Create: `apps/web/src/components/account-table.test.tsx`

**Interfaces:**
- Consumes: Task 5 JSON contracts; `ApiClient` methods use generated/manual TypeScript DTOs that match backend schemas exactly.
- Produces: responsive application shell, Dashboard route, Accounts route, `/leads/A`, `/leads/B`, `/leads/C`, `Dashboard`, and `AccountTable` with server-side query parameters for page, page size, search, country, ICP, grade, review status, and sort.

- [ ] **Step 1: Create test configuration and write failing component tests**

Test loading/error/empty/data states, metric cards, budget display, recent accounts, grade navigation, filter query serialization, pagination, accessible table naming, score explanations, and synthetic-data labels.

- [ ] **Step 2: Verify tests fail because components and client do not exist**

Run: `npm --prefix apps/web test -- --run`

Expected: module resolution failures for the new components.

- [ ] **Step 3: Implement the web foundation and list screens**

Use semantic HTML, visible keyboard focus, reduced-motion support, responsive table fallback, localized date/number formatting, and a compact operations-workspace visual system in `globals.css` without a large UI framework.

- [ ] **Step 4: Run frontend tests, lint, and production build**

Run: `npm --prefix apps/web test -- --run`

Run: `npm --prefix apps/web run lint`

Run: `npm --prefix apps/web run build`

Expected: all commands exit 0 with no type errors.

- [ ] **Step 5: Commit dashboard and lists**

```powershell
git add package.json apps/web
git commit -m "feat: add lead dashboard and account lists"
```

### Task 7: Search Tasks, Account Detail, and Review Workflow

**Files:**
- Create: `apps/web/src/app/search-tasks/page.tsx`
- Create: `apps/web/src/app/search-tasks/[id]/page.tsx`
- Create: `apps/web/src/app/accounts/[id]/page.tsx`
- Create: `apps/web/src/components/search-task-form.tsx`
- Create: `apps/web/src/components/search-task-list.tsx`
- Create: `apps/web/src/components/account-detail.tsx`
- Create: `apps/web/src/components/score-breakdown.tsx`
- Create: `apps/web/src/components/evidence-list.tsx`
- Create: `apps/web/src/components/review-actions.tsx`
- Create: `apps/web/src/components/search-task-form.test.tsx`
- Create: `apps/web/src/components/account-detail.test.tsx`
- Create: `apps/web/src/components/review-actions.test.tsx`

**Interfaces:**
- Consumes: Task 6 shell/client/types and Task 5 task/detail/review endpoints.
- Produces: validated task creation, progress and budget views, partial-failure display, cancellation action, account evidence/detail view, and mutation functions `submitReview(accountId, status, note)` for Approved, Rejected, and Needs Review.

- [ ] **Step 1: Write failing workflow component tests**

Test required search criteria, numeric limit bounds, optional seed URL validation, submitting configured ICP/country values, task progress and failure summary, cancellation availability by state, score contributions with source links, product-match confidence, rules-only/AI mode, and all three review transitions with history refresh.

- [ ] **Step 2: Verify the tests fail because workflow components are absent**

Run: `npm --prefix apps/web test -- --run`

Expected: module resolution failures for the new components.

- [ ] **Step 3: Implement task and account-detail workflows**

Keep mutations explicit, disable duplicate submissions, announce completion/errors through accessible live regions, and preserve user-entered task form values after recoverable API errors.

- [ ] **Step 4: Run complete frontend verification**

Run: `npm --prefix apps/web test -- --run`

Run: `npm --prefix apps/web run lint`

Run: `npm --prefix apps/web run build`

Expected: all commands exit 0.

- [ ] **Step 5: Commit workflow screens**

```powershell
git add apps/web
git commit -m "feat: add search tasks and account review workflow"
```

### Task 8: Demo Seed, End-to-End Verification, Windows Scripts, and Documentation

**Files:**
- Create: `apps/api/src/lead_factory/demo_seed.py`
- Create: `apps/api/tests/test_demo_seed.py`
- Create: `apps/web/e2e/lead-factory.spec.ts`
- Create: `apps/web/playwright.config.ts`
- Create: `scripts/setup.ps1`
- Create: `scripts/dev.ps1`
- Create: `scripts/seed-demo.ps1`
- Create: `scripts/verify.ps1`
- Create: `README.md`
- Create: `.gitignore`
- Modify: `apps/api/pyproject.toml`
- Modify: `apps/web/package.json`

**Interfaces:**
- Consumes: the complete application from Tasks 1-7.
- Produces: idempotent `seed_demo(session: Session) -> SeedSummary`, synthetic dashboard records, Windows setup/dev/seed/verification commands, Playwright workflow coverage, and the final operator documentation.

- [ ] **Step 1: Write failing demo-seed and end-to-end tests**

Backend test asserts idempotency, visible synthetic labels, A/B/C coverage, evidence/product matches, and no collision with live domains. Browser test creates a fixture-backed task, waits for completion, filters the resulting account, opens its evidence and score, marks it Approved, and verifies history.

- [ ] **Step 2: Verify the demo test fails and the browser workflow is unavailable**

Run: `uv run --project apps/api pytest apps/api/tests/test_demo_seed.py -v`

Run: `npm --prefix apps/web run test:e2e`

Expected: the first fails for missing `seed_demo`; the second fails for missing Playwright configuration or test target.

- [ ] **Step 3: Implement seed data, scripts, ignore rules, and README**

README must document prerequisites, one-time setup, environment configuration, rules-only versus AI mode, database switching, demo reset/seed, development startup, verification, logs, collection ethics/safety, cost controls, troubleshooting, and the explicit no-outreach boundary.

- [ ] **Step 4: Run fresh full verification and smoke startup**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`

Run: `powershell -ExecutionPolicy Bypass -File scripts/seed-demo.ps1`

Run both services with `scripts/dev.ps1`, then verify `/api/v1/health`, `/api/v1/readiness`, the Dashboard, Accounts, A/B/C Leads, Search Tasks, and one Account Detail page. Stop both services cleanly after the smoke test.

Expected: all automated checks exit 0; both services answer locally; each required page renders; the logs contain no unhandled exception or exposed secret.

- [ ] **Step 5: Inspect repository state and commit delivery assets**

Run: `git status --short`

Confirm only intended project files are present and runtime databases, logs, caches, `.env`, and dependencies are ignored.

```powershell
git add README.md .gitignore scripts apps/api apps/web
git commit -m "docs: complete local lead factory delivery"
```

### Final Delivery Gate

- [ ] Re-read the design spec and map every success criterion and out-of-scope boundary to implemented code or documentation.
- [ ] Run `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1` again from a clean process state.
- [ ] Confirm `git status --short` is empty.
- [ ] Record exact test counts, build results, local URLs, rules-only behavior, optional credentials still needed, and any known limitation in the handoff.
