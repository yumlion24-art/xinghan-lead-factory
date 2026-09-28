import type { LeadGrade, ReviewStatus } from "@/lib/types";


type BadgeTone = LeadGrade | ReviewStatus | "rules_only" | "ai";


const labels: Record<BadgeTone, string> = {
  A: "Grade A",
  B: "Grade B",
  C: "Grade C",
  approved: "Approved",
  rejected: "Rejected",
  needs_review: "Needs review",
  rules_only: "Rules only",
  ai: "AI enhanced",
};


export function StatusBadge({ value }: { value: BadgeTone }) {
  return <span className={`badge badge--${value.toLowerCase()}`}>{labels[value]}</span>;
}

