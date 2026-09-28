import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Dashboard } from "./dashboard";


const data = {
  accounts_total: 42,
  grades: { A: 8, B: 19, C: 15 },
  reviews: { approved: 5, rejected: 3, needs_review: 34 },
  active_tasks: 2,
  budget_usage: { pages: 128, domains: 47, ai_calls: 0 },
};


describe("Dashboard", () => {
  it("shows lead pipeline, review queue, task, and budget metrics", () => {
    render(<Dashboard data={data} />);

    expect(screen.getByRole("heading", { name: "Lead operations overview" })).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /A leads 8/i })).toHaveAttribute("href", "/leads/A");
    expect(screen.getByRole("link", { name: /B leads 19/i })).toHaveAttribute("href", "/leads/B");
    expect(screen.getByText("34 awaiting review")).toBeInTheDocument();
    expect(screen.getByText("128 pages")).toBeInTheDocument();
    expect(screen.getByText("AI off")).toBeInTheDocument();
  });

  it("renders an explicit empty state instead of blank metrics", () => {
    render(
      <Dashboard
        data={{
          accounts_total: 0,
          grades: { A: 0, B: 0, C: 0 },
          reviews: {},
          active_tasks: 0,
          budget_usage: { pages: 0, domains: 0, ai_calls: 0 },
        }}
      />,
    );

    expect(screen.getByText("No accounts yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create a search task" })).toHaveAttribute(
      "href",
      "/search-tasks",
    );
  });

  it("renders loading and error states accessibly", () => {
    const { rerender } = render(<Dashboard state="loading" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading dashboard");

    rerender(<Dashboard state="error" error="API unavailable" />);
    expect(screen.getByRole("alert")).toHaveTextContent("API unavailable");
  });
});
