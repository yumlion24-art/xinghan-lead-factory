import type { ScoreContribution } from "@/lib/types";


export function ScoreBreakdown({ items }: { items: ScoreContribution[] }) {
  return (
    <section className="detail-section"><div className="panel__heading"><div><span className="eyebrow">EXPLAINABLE SCORE</span><h2>Score breakdown</h2></div></div>
      <div className="score-rules">{items.map((item) => <article key={item.rule_id}><strong className={item.points < 0 ? "negative" : "positive"}>{item.points > 0 ? "+" : ""}{item.points}</strong><div><b>{item.dimension.replaceAll("_", " ")}</b><p>{item.excerpt}</p>{item.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer">View source</a> : null}</div></article>)}</div>
    </section>
  );
}

