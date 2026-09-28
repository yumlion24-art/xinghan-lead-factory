import { notFound } from "next/navigation";

import { AccountTable } from "@/components/account-table";
import { api } from "@/lib/api-client";
import type { LeadGrade } from "@/lib/types";


export default async function GradePage({ params }: { params: Promise<{ grade: string }> }) {
  const { grade: rawGrade } = await params;
  const grade = rawGrade.toUpperCase() as LeadGrade;
  if (!["A", "B", "C"].includes(grade)) notFound();
  const filters = { page: 1, page_size: 25, grade, sort: "score_desc" as const };
  const data = await api.accounts(filters);
  return (
    <div className="page-stack">
      <section className="page-heading"><div><span className="eyebrow">PRIORITY QUEUE</span><h1>Grade {grade} leads</h1><p>Accounts grouped by the current explainable score.</p></div><div className={`grade-orb grade-orb--${grade.toLowerCase()}`}>{grade}</div></section>
      <AccountTable accounts={data.items} total={data.total} filters={filters} />
    </div>
  );
}

