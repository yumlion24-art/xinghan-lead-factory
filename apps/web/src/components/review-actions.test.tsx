import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReviewActions } from "./review-actions";


describe("ReviewActions", () => {
  it.each([
    ["Approve", "approved"],
    ["Reject", "rejected"],
    ["Needs review", "needs_review"],
  ] as const)("submits the %s transition and announces completion", async (label, status) => {
    const user = userEvent.setup();
    const submitReview = vi.fn().mockResolvedValue({ status });
    render(<ReviewActions accountId="a1" submitReview={submitReview} />);

    await user.type(screen.getByLabelText("Review note"), "Verified by operator");
    await user.click(screen.getByRole("button", { name: label }));

    expect(submitReview).toHaveBeenCalledWith("a1", status, "Verified by operator");
    expect(await screen.findByRole("status")).toHaveTextContent("Review saved");
  });

  it("disables duplicate submissions and reports recoverable errors", async () => {
    const user = userEvent.setup();
    let rejectRequest!: (error: Error) => void;
    const pending = new Promise((_, reject) => { rejectRequest = reject; });
    const submitReview = vi.fn().mockReturnValue(pending);
    render(<ReviewActions accountId="a1" submitReview={submitReview} />);

    await user.click(screen.getByRole("button", { name: "Approve" }));
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    rejectRequest(new Error("API unavailable"));

    expect(await screen.findByRole("alert")).toHaveTextContent("API unavailable");
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
  });
});
