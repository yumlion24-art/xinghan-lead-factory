import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SearchTaskForm } from "./search-task-form";
import { SearchTaskList } from "./search-task-list";


describe("SearchTaskForm", () => {
  it("requires a query or seed URL and validates limits", async () => {
    const user = userEvent.setup();
    render(<SearchTaskForm submitTask={vi.fn()} />);

    await user.clear(screen.getByLabelText("Maximum results"));
    await user.type(screen.getByLabelText("Maximum results"), "101");
    await user.click(screen.getByRole("button", { name: "Create search task" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Enter a search query or at least one seed URL");
    expect(screen.getByRole("alert")).toHaveTextContent("Maximum results must be between 1 and 100");
  });

  it("preserves values after recoverable errors and submits configured fields", async () => {
    const user = userEvent.setup();
    const submitTask = vi.fn().mockRejectedValueOnce(new Error("API unavailable"));
    render(<SearchTaskForm submitTask={submitTask} />);

    await user.type(screen.getByLabelText("Search query"), "airline catering procurement");
    await user.type(screen.getByLabelText("Countries"), "UAE, Singapore");
    await user.selectOptions(screen.getByLabelText("ICP"), "aviation_catering");
    await user.type(screen.getByLabelText("Seed URLs"), "https://example.com\nnot-a-url");
    await user.click(screen.getByRole("button", { name: "Create search task" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Seed URL must start with http:// or https://");

    await user.clear(screen.getByLabelText("Seed URLs"));
    await user.type(screen.getByLabelText("Seed URLs"), "https://example.com");
    await user.click(screen.getByRole("button", { name: "Create search task" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("API unavailable");
    expect(screen.getByLabelText("Search query")).toHaveValue("airline catering procurement");
    expect(submitTask).toHaveBeenCalledWith(
      expect.objectContaining({
        query: "airline catering procurement",
        countries: ["UAE", "Singapore"],
        icp_ids: ["aviation_catering"],
        seed_urls: ["https://example.com"],
        max_results: 20,
      }),
    );
  });
});


describe("SearchTaskList", () => {
  it("shows partial progress, failure context, and cancellation only for active tasks", () => {
    render(
      <SearchTaskList
        tasks={[
          {
            id: "task-1",
            query: "airline catering",
            status: "partially_completed",
            progress: { discovered: 10, processed: 10, succeeded: 8, failed: 2 },
            budget_usage: { pages: 18, domains: 10, ai_calls: 0 },
            failure_summary: "2 domains could not be fetched",
            created_at: "2026-09-28T08:00:00Z",
          },
          {
            id: "task-2",
            query: "food packaging",
            status: "running",
            progress: { discovered: 20, processed: 4, succeeded: 4, failed: 0 },
            budget_usage: { pages: 7, domains: 4, ai_calls: 0 },
            failure_summary: null,
            created_at: "2026-09-28T09:00:00Z",
          },
        ]}
      />,
    );

    expect(screen.getByText("8 succeeded / 2 failed")).toBeInTheDocument();
    expect(screen.getByText("2 domains could not be fetched")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel food packaging" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel airline catering" })).not.toBeInTheDocument();
  });
});
