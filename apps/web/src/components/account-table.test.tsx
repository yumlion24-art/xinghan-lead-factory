import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AccountTable } from "./account-table";
import { buildAccountQuery } from "@/lib/api-client";


const accounts = [
  {
    id: "a1",
    display_name: "Sky Meals International",
    normalized_domain: "skymeals.example",
    website_url: "https://skymeals.example",
    country: "UAE",
    company_type: "Inflight caterer",
    grade: "A" as const,
    score: 88,
    review_status: "needs_review" as const,
    enrichment_mode: "rules_only",
    is_demo: false,
    created_at: "2026-09-28T08:00:00Z",
  },
  {
    id: "b1",
    display_name: "Demo Foodservice Distributor",
    normalized_domain: "demo-distributor.example",
    website_url: "https://demo-distributor.example",
    country: "UK",
    company_type: "Foodservice distributor",
    grade: "B" as const,
    score: 63,
    review_status: "approved" as const,
    enrichment_mode: "rules_only",
    is_demo: true,
    created_at: "2026-09-27T08:00:00Z",
  },
];


describe("AccountTable", () => {
  it("shows accessible account rows, score explanations, and demo labels", () => {
    render(
      <AccountTable
        accounts={accounts}
        total={2}
        filters={{ page: 1, page_size: 25, sort: "score_desc" }}
      />,
    );

    const table = screen.getByRole("table", { name: "Lead accounts" });
    expect(within(table).getByRole("link", { name: "Sky Meals International" })).toHaveAttribute(
      "href",
      "/accounts/a1",
    );
    expect(screen.getByLabelText("Sky Meals International score 88 out of 100")).toBeInTheDocument();
    expect(screen.getByText("Synthetic demo")).toBeInTheDocument();
    expect(screen.getAllByText("Rules only")).toHaveLength(2);
  });

  it("serializes server-side filters and pagination without losing values", () => {
    const query = buildAccountQuery({
      page: 2,
      page_size: 25,
      search: "airline catering",
      country: "UAE",
      grade: "A",
      review_status: "needs_review",
      sort: "score_desc",
    });

    expect(query).toBe(
      "page=2&page_size=25&search=airline+catering&country=UAE&grade=A&review_status=needs_review&sort=score_desc",
    );
  });

  it("shows empty results and a previous pagination link", () => {
    const { rerender } = render(
      <AccountTable accounts={[]} total={0} filters={{ page: 1, page_size: 25, search: "none" }} />,
    );
    expect(screen.getByText("No accounts match these filters")).toBeInTheDocument();

    rerender(
      <AccountTable accounts={accounts} total={27} filters={{ page: 2, page_size: 25, grade: "A" }} />,
    );
    expect(screen.getByRole("link", { name: "Previous page" })).toHaveAttribute(
      "href",
      "/accounts?page=1&page_size=25&grade=A",
    );
  });
});
