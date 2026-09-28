import { EvidenceList } from "./evidence-list";
import { ReviewActions } from "./review-actions";
import { ScoreBreakdown } from "./score-breakdown";
import { StatusBadge } from "./status-badge";
import type { AccountDetailData } from "@/lib/types";


export function AccountDetail({ account }: { account: AccountDetailData }) {
  return <div className="page-stack account-detail">
    <section className="detail-hero panel">
      <div><span className="eyebrow">{account.company_type ?? "UNCLASSIFIED ACCOUNT"}</span><h1>{account.display_name}</h1><a href={account.website_url ?? "#"} target="_blank" rel="noreferrer">{account.normalized_domain} ↗</a><p>{account.description}</p><div className="badge-row">{account.grade ? <StatusBadge value={account.grade} /> : null}<StatusBadge value={account.review_status} /><StatusBadge value={account.enrichment_mode === "ai" ? "ai" : "rules_only"} /></div></div>
      <div className="lead-score" aria-label={`Lead score ${account.score} out of 100`}><strong>{account.score}</strong><span>/100</span><small>{account.calculation_version ?? "unversioned"}</small></div>
    </section>
    <div className="detail-grid">
      <div className="panel detail-main"><ScoreBreakdown items={account.score_breakdown} /><EvidenceList evidence={account.evidence} /><section className="detail-section"><div className="panel__heading"><div><span className="eyebrow">PUBLIC ROUTES</span><h2>Contact and enrichment notes</h2></div></div>{account.contact_routes.length ? <ul>{account.contact_routes.map((route) => <li key={`${route.type}:${route.value}`}>{route.type}: {route.value}</li>)}</ul> : <p>No public contact route collected.</p>}{account.scale_signals.length ? <ul>{account.scale_signals.map((signal) => <li key={signal}>{signal}</li>)}</ul> : null}</section><section className="detail-section"><div className="panel__heading"><div><span className="eyebrow">XINGHAN FIT</span><h2>Product matches</h2></div></div><div className="product-matches">{account.product_matches.map((match) => <article key={match.family_id}><header><strong>{match.family_id.replaceAll("_", " ")}</strong><span>{Math.round(match.confidence * 100)}% confidence</span></header><p>{match.reason}</p><ul>{match.recommended_products.map((product) => <li key={product}>{product}</li>)}</ul></article>)}</div></section></div>
      <aside className="detail-aside"><ReviewActions accountId={account.id} /><section className="panel history"><span className="eyebrow">AUDIT TRAIL</span><h2>Review history</h2>{account.review_history.map((item) => <article key={item.id}><StatusBadge value={item.status} /><p>{item.note || "No note"}</p><small>{item.actor} · {new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(item.created_at))}</small></article>)}</section></aside>
    </div>
  </div>;
}
