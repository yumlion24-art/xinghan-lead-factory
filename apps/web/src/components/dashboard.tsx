import Link from "next/link";

import type { DashboardData } from "@/lib/types";


interface DashboardProps {
  data?: DashboardData;
  state?: "ready" | "loading" | "error";
  error?: string;
}


export function Dashboard({ data, state = "ready", error }: DashboardProps) {
  if (state === "loading") return <div role="status" className="panel state-panel">Loading dashboard…</div>;
  if (state === "error") return <div role="alert" className="panel state-panel state-panel--error">{error}</div>;
  if (!data) return null;

  const reviewCount = data.reviews.needs_review ?? 0;
  return (
    <div className="page-stack">
      <section className="page-heading">
        <div>
          <span className="eyebrow">PIPELINE CONTROL</span>
          <h1>Lead operations overview</h1>
          <p>Discover, qualify, and review overseas B2B accounts from public evidence.</p>
        </div>
        <div className="date-chip">Rules-first qualification</div>
      </section>

      {data.accounts_total === 0 ? (
        <section className="panel empty-state">
          <span className="empty-state__mark">00</span>
          <h2>No accounts yet</h2>
          <p>Start a bounded public-web search or load the synthetic demo dataset.</p>
          <Link className="button" href="/search-tasks">Create a search task</Link>
        </section>
      ) : (
        <>
          <section className="metric-grid" aria-label="Lead pipeline metrics">
            <article className="metric-card metric-card--hero">
              <span>Total accounts</span>
              <strong>{data.accounts_total.toLocaleString()}</strong>
              <small>{reviewCount} awaiting review</small>
            </article>
            {(["A", "B", "C"] as const).map((grade) => (
              <Link
                aria-label={`${grade} leads ${data.grades[grade]}`}
                className={`metric-card metric-card--${grade.toLowerCase()}`}
                href={`/leads/${grade}`}
                key={grade}
              >
                <span>{grade} leads</span>
                <strong>{data.grades[grade].toLocaleString()}</strong>
                <small>Open filtered queue →</small>
              </Link>
            ))}
          </section>

          <section className="dashboard-grid">
            <article className="panel review-panel">
              <div className="panel__heading">
                <div><span className="eyebrow">HUMAN GATE</span><h2>Review queue</h2></div>
                <Link href="/accounts?review_status=needs_review">Open queue</Link>
              </div>
              <div className="review-number">{reviewCount}</div>
              <p>accounts need an explicit operator decision</p>
              <div className="segmented-bar" aria-label={`${reviewCount} accounts need review`}>
                <span style={{ width: `${data.accounts_total ? (reviewCount / data.accounts_total) * 100 : 0}%` }} />
              </div>
            </article>
            <article className="panel budget-panel">
              <div className="panel__heading"><div><span className="eyebrow">TODAY</span><h2>Usage controls</h2></div></div>
              <dl className="budget-list">
                <div><dt>Collection</dt><dd>{data.budget_usage.pages.toLocaleString()} pages</dd></div>
                <div><dt>Domains</dt><dd>{data.budget_usage.domains.toLocaleString()} checked</dd></div>
                <div><dt>Enrichment</dt><dd>{data.budget_usage.ai_calls ? `${data.budget_usage.ai_calls} AI calls` : "AI off"}</dd></div>
                <div><dt>Active tasks</dt><dd>{data.active_tasks}</dd></div>
              </dl>
            </article>
          </section>
        </>
      )}
    </div>
  );
}
