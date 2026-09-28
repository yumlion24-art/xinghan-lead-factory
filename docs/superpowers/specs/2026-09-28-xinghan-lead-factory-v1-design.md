# Xinghan Lead Factory V1 Design

## 1. Purpose

Xinghan Lead Factory V1 is a Windows-local B2B account discovery and qualification system for Guangdong Xinghan Industrial Co., Ltd. It helps an operator find overseas companies, collect evidence from public company websites, remove duplicates, score account fit, match Xinghan product families, and make an explicit review decision.

V1 stops before outreach. It does not send email, WhatsApp messages, social messages, or any other communication.

## 2. Success Criteria

The delivered repository must:

1. Start locally on Windows with documented commands.
2. Provide a Next.js/React interface and a FastAPI API.
3. Use SQLite by default and accept a PostgreSQL `DATABASE_URL` without changing application code.
4. Create and run bounded public-web search tasks.
5. Normalize and deduplicate accounts by registrable domain.
6. Produce an explainable 0-100 score, A/B/C grade, evidence list, and Xinghan product matches.
7. Run without an AI API key in rules-only mode and enhance results when a supported key is configured.
8. Let an operator mark accounts Approved, Rejected, or Needs Review and preserve the decision history.
9. Expose Dashboard, Accounts, A/B/C Leads, Search Tasks, and Account Detail screens.
10. Include configuration, logs, error handling, tests, `.env.example`, and a practical README.

## 3. Xinghan Positioning Used by the System

The initial product taxonomy is derived from Xinghan's public website and is stored as editable configuration rather than hard-coded application logic.

### Product families

- Airline and airport supplies: meal trays and boxes, cutlery kits, refreshing towels and wet wipes, airsickness bags, cabin waste bags, boarding passes, labels, and security seals.
- Foodservice packaging: aluminum and plastic meal containers, paper food boxes and bags, cups, cling film, foil sheets, labels, and catering consumables.
- Biodegradable and compostable products: bagasse trays, PLA or wooden cutlery kits, PLA-coated cups, and PLA/PBAT bags.
- Flexible packaging: heat-seal films, printed films, lidding films, cling film, and custom packaging rolls.

### Selling signals

- Airline, airport, inflight catering, central kitchen, foodservice, supermarket, and distribution use cases.
- OEM/ODM, custom dimensions, printing, artwork, materials, packing, and recurring bulk production.
- Food-contact and management-system compliance, quality controls, batch consistency, export coordination, and tender experience.

The product configuration records each family, its aliases, buyer signals, exclusions, and recommended Xinghan offerings. Operators may change it without rebuilding the application.

## 4. Initial ICP

### ICP 1: Aviation catering and supply chain

Airlines, inflight caterers, airport caterers, airport operators, ground-service suppliers, aviation consumables distributors, duty-free suppliers, and institutional catering partners.

High-value signals include inflight meals, airline catering, cabin service, galley equipment, boarding documents, tamper evidence, airport procurement, tenders, and high-volume food operations.

### ICP 2: Foodservice packaging distribution

Importers, wholesalers, distributors, food packaging suppliers, restaurant-supply companies, hotel-supply companies, central kitchens, meal-prep operators, supermarket suppliers, and institutional foodservice operators.

High-value signals include wholesale, distribution, private label, custom printing, container loads, multiple locations, food packaging catalogues, and commercial kitchen supply.

### ICP 3: Sustainable packaging buyers

Distributors, importers, food brands, caterers, hospitality groups, retailers, and packaging companies actively purchasing compostable or biodegradable foodservice products.

High-value signals include bagasse, sugarcane fibre, compostable, PLA, PBAT, plastic reduction, sustainable procurement, and certified food-contact packaging.

### Explicit low-fit or excluded profiles

- Consumer-only shops and very small local restaurants with no wholesale or multi-site evidence.
- Direct competing manufacturers whose main business overlaps Xinghan manufacturing.
- Job boards, news pages, directories with no identifiable target company, parked domains, and inaccessible sites.
- Companies with no evidence connecting them to the configured ICP or products.

Competitors are retained only when an operator explicitly requests market research; they are not treated as leads.

## 5. Lead Score

The deterministic score is the system of record. AI may supply structured evidence and suggestions but may not silently override scoring rules.

| Dimension | Maximum | Meaning |
| --- | ---: | --- |
| ICP industry fit | 25 | How closely the company type matches one of the three ICPs |
| Product demand signals | 25 | Evidence that the company buys, uses, distributes, or specifies relevant products |
| Scale and purchasing capacity | 15 | Multi-site, fleet, distribution footprint, institutional volume, or other credible scale indicators |
| Geography and import fit | 10 | Overseas market, import activity, suitable service region, and accessible public presence |
| OEM, wholesale, import, or tender intent | 15 | Procurement, tender, wholesale, private-label, custom-product, or sourcing language |
| Evidence and contact completeness | 10 | Official website, identifiable company, useful contact route, and source coverage |

Negative rules can deduct up to 40 points. Direct competitor evidence, consumer-only operations, irrelevant industry, weak identity, or an inaccessible/parked domain are negative signals.

Grades are:

- A: 75-100
- B: 55-74
- C: 0-54

An account is automatically marked Needs Review when evidence is insufficient, identity is ambiguous, the rules and AI recommendation materially conflict, or extraction confidence is below the configured threshold. Manual status is independent of grade.

Every score stores the contributing rule ID, points, evidence excerpt, source URL, and calculation version.

## 6. Architecture

The repository is a small monorepo:

```text
apps/
  api/       FastAPI, SQLAlchemy, migrations, collection and scoring services
  web/       Next.js, TypeScript, React UI
config/      product catalogue, ICP, scoring rules, prompts, crawler budgets
scripts/     Windows-friendly setup, development, seed, and verification helpers
docs/        product and operating documentation
```

The web application communicates only with the API. The API owns validation, persistence, scoring, task execution, logs, and provider abstractions.

Long-running search tasks execute in a bounded in-process worker for V1. Task state is persisted before work begins. The design keeps a `TaskRunner` boundary so a later release can replace the worker with Celery, RQ, or a managed queue without changing HTTP endpoints or the UI.

## 7. Data Model

### Account

Stores legal/display name, normalized domain, website URL, country, industry label, company type, description, scale signals, contact routes, lifecycle status, grade, score, confidence, timestamps, and calculation version.

The normalized registrable domain is unique. A manual merge mechanism is not required in V1, but duplicate observations attach to the existing account.

### Source and Evidence

`SourcePage` stores URL, canonical URL, page title, retrieval status, content hash, retrieval time, and bounded extracted text. `Evidence` links an excerpt and signal type to an account, source page, scoring rule, or product match.

### SearchTask

Stores query, countries, ICP selection, seed URLs, limits, status, progress counters, budget consumption, timestamps, and a human-readable failure summary. Status values are queued, running, completed, partially_completed, cancelled, and failed.

### Score and ProductMatch

`ScoreBreakdown` stores positive and negative rule contributions. `ProductMatch` stores product family, recommended products, reason, confidence, and linked evidence.

### ReviewDecision

Stores Approved, Rejected, or Needs Review, optional note, timestamp, and actor label. The latest decision is reflected on the account while the full history remains available.

## 8. Discovery and Collection Flow

1. The operator creates a task using search terms, target countries, one or more ICPs, optional seed URLs, and explicit result/crawl limits.
2. A search-provider adapter returns candidate public URLs. V1 includes a no-key provider suitable for light local use plus a deterministic seed-URL provider for tests and controlled operation.
3. URLs are canonicalized and unsafe targets are rejected. The collector permits HTTP/HTTPS only, blocks localhost and private/reserved networks after DNS resolution, applies timeouts and response-size limits, respects robots rules, and uses a descriptive user agent.
4. Per-domain throttling, retry limits, page limits, task limits, and daily budgets are enforced before each fetch.
5. Bounded HTML is converted to visible text. The system follows only same-domain links that are likely to describe the company, products, industries, capabilities, contact details, sustainability, procurement, or tenders.
6. The extractor creates a structured company observation with source evidence.
7. The deduplicator resolves the registrable domain and creates or updates one account.
8. Rules calculate the score and product matches. Optional AI enrichment then returns schema-validated suggestions and evidence references.
9. The final account grade and review state are persisted and shown in the UI.

Search result pages and third-party directory pages may identify candidate domains, but claims used for scoring should prefer the target company's official site. Unsupported AI assertions do not add score.

## 9. AI Enhancement

AI is optional. The provider interface accepts structured company text and returns a strict JSON-compatible result containing:

- concise company summary;
- most likely ICP and confidence;
- detected purchasing/use signals with source references;
- recommended Xinghan product families and reasons;
- risk flags and review recommendation.

Prompts live in versioned files under `config/prompts`. The API records provider, model, prompt version, token usage when available, estimated cost, latency, and error category. Raw secrets are never logged.

If no supported key is present, a provider is unavailable, output fails schema validation, or a cost budget would be exceeded, the task continues in rules-only mode and records the fallback reason.

## 10. User Interface

### Dashboard

Shows account totals, A/B/C counts, review-state counts, task activity, recently discovered accounts, source success/failure rate, and current daily crawl/AI budget usage.

### Accounts and A/B/C Leads

Provide server-side pagination, text search, country/ICP/grade/status filters, sort by score or discovery time, compact score explanations, and links to account details. The A/B/C navigation applies the corresponding grade filter to the shared account table.

### Search Tasks

Allows task creation, lists progress and cost/budget counters, shows partial failures, and opens the accounts discovered by a task. V1 supports cancellation between fetches, not interruption of an active network request.

### Account Detail

Shows identity, fit summary, score breakdown, product matches, evidence excerpts with source links, contact routes, crawl history, AI/rules mode, and decision history. It provides Approve, Reject, and Needs Review actions with an optional note.

The visual direction is an operations workspace: information-dense, calm, responsive, keyboard-friendly, and accessible. It is not a marketing site.

## 11. API Surface

V1 exposes versioned endpoints under `/api/v1` for:

- health and readiness;
- dashboard metrics;
- account list and detail;
- account review decisions;
- search-task create, list, detail, and cancel;
- configuration metadata safe for display.

Error responses use a consistent envelope with code, message, optional field details, and request ID. List endpoints use explicit page and page-size parameters with a configured maximum.

## 12. Configuration and Environment

Editable YAML configuration covers product taxonomy, ICP keywords, scoring rules, exclusion rules, crawler limits, allowed content types, task budgets, AI budgets, and model settings. Configuration is validated on startup and fails fast with actionable messages.

`.env.example` documents at least:

- `DATABASE_URL` with a SQLite default;
- API/web origins and ports;
- log level and log directory;
- crawler user agent, timeout, size, concurrency, delay, and daily limits;
- optional AI provider, model, key, and daily call/token/cost limits.

The frontend never receives provider secrets.

## 13. Reliability, Safety, and Cost Controls

- Structured application and task logs include timestamp, level, request/task ID, component, event, and safe context.
- Fetch, parse, provider, validation, database, and budget failures are categorized and shown without stack traces in the UI.
- Retry applies only to transient operations, uses bounded exponential backoff with jitter, and never bypasses budgets.
- HTTP collection defends against SSRF, oversized responses, redirect abuse, unsupported content, decompression bombs, and accidental credential logging.
- Default concurrency is conservative: one active request per domain and a configurable delay between requests.
- Every task has maximum search results, domains, pages per domain, total pages, elapsed time, and optional AI calls.
- The application does not bypass authentication, paywalls, CAPTCHAs, or access restrictions.

## 14. Testing and Verification

Backend tests cover configuration validation, URL safety, domain normalization, deduplication, scoring boundaries and negative rules, product matching, status transitions, budget enforcement, provider fallback, and API behavior. Network behavior uses local deterministic fixtures; automated tests do not crawl arbitrary live sites.

Frontend tests cover primary page rendering, filtering, task form validation, score display, account detail evidence, and review actions. End-to-end verification covers a seeded task through discovery, scoring, detail review, and approval.

Release verification includes backend tests, frontend tests, static checks, production builds, database initialization, seed loading, and a local smoke test of both services.

## 15. Seed and Demo Experience

The repository includes clearly marked synthetic/demo accounts and deterministic source fixtures. The first local run can therefore display a useful dashboard and demonstrate the workflow without external API keys or uncontrolled network access.

Live collection is enabled only when the operator creates a task. Demo data is never presented as a real newly discovered lead.

## 16. Out of Scope for V1

- Automated or one-click outbound email, WhatsApp, social messaging, or sequences.
- Contact-person enrichment from paid databases.
- Authentication, multi-user roles, or cloud deployment.
- Browser automation for sites that block ordinary HTTP collection.
- CAPTCHA solving, paywall bypass, or collection from private/logged-in sources.
- CRM synchronization, campaign analytics, reply tracking, and AI learning from won/lost revenue.
- Full company merge workflows or shared multi-worker task orchestration.

## 17. Delivery Boundary

The final handoff is a locally startable repository with source code, migrations/schema initialization, configuration, synthetic seed data, tests, `.env.example`, Windows-oriented setup instructions, and verified startup commands. Any missing API key affects only optional AI enhancement; it must not prevent core discovery, rules scoring, product matching, review, or demo operation.
