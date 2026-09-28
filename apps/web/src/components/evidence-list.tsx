import type { Evidence } from "@/lib/types";


export function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  return <section className="detail-section"><div className="panel__heading"><div><span className="eyebrow">SOURCE RECORD</span><h2>Evidence</h2></div></div><div className="evidence-list">{evidence.map((item) => <blockquote key={item.id}><p>{item.excerpt}</p><footer><span>{item.signal_type.replaceAll("_", " ")}</span><a href={item.source_url} target="_blank" rel="noreferrer">Open source ↗</a></footer></blockquote>)}</div></section>;
}

