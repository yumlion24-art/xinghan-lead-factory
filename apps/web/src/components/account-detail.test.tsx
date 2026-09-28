import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AccountDetail } from "./account-detail";


const account = {
  id: "a1",
  display_name: "Sky Meals International",
  normalized_domain: "skymeals.example",
  website_url: "https://skymeals.example",
  country: "UAE",
  company_type: "Inflight caterer",
  industry: "Aviation catering",
  description: "International inflight catering operator.",
  scale_signals: ["multi-site"],
  contact_routes: [{ type: "email", value: "buying@skymeals.example" }],
  grade: "A" as const,
  score: 88,
  confidence: 0.9,
  calculation_version: "v1.0.0",
  review_status: "needs_review" as const,
  enrichment_mode: "rules_only",
  is_demo: false,
  created_at: "2026-09-28T08:00:00Z",
  evidence: [
    {
      id: "ev-1",
      signal_type: "product",
      excerpt: "We source airline meal trays for multiple kitchens.",
      source_url: "https://skymeals.example/products",
      confidence: 1,
    },
  ],
  score_breakdown: [
    {
      rule_id: "demand-airline-meals",
      dimension: "product_demand",
      points: 25,
      excerpt: "We source airline meal trays.",
      source_url: "https://skymeals.example/products",
    },
  ],
  product_matches: [
    {
      family_id: "airline_airport",
      recommended_products: ["Airline meal trays and meal boxes"],
      reason: "Direct meal tray demand",
      confidence: 0.9,
      evidence_ids: ["ev-1"],
    },
  ],
  review_history: [
    {
      id: "review-1",
      status: "needs_review" as const,
      note: "Check volume",
      actor: "operator",
      created_at: "2026-09-28T09:00:00Z",
    },
  ],
};


describe("AccountDetail", () => {
  it("shows score evidence, product confidence, source links, mode, and history", () => {
    render(<AccountDetail account={account} />);

    expect(screen.getByRole("heading", { name: "Sky Meals International" })).toBeInTheDocument();
    expect(screen.getByLabelText("Lead score 88 out of 100")).toBeInTheDocument();
    expect(screen.getByText("+25")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View source" })).toHaveAttribute(
      "href",
      "https://skymeals.example/products",
    );
    expect(screen.getByText("Airline meal trays and meal boxes")).toBeInTheDocument();
    expect(screen.getByText("90% confidence")).toBeInTheDocument();
    expect(screen.getByText("Rules only")).toBeInTheDocument();
    expect(screen.getByText("Check volume")).toBeInTheDocument();
  });
});
