"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api-client";
import type { ReviewStatus } from "@/lib/types";


export function ReviewActions({
  accountId,
  submitReview = api.submitReview,
}: {
  accountId: string;
  submitReview?: (accountId: string, status: ReviewStatus, note: string) => Promise<unknown>;
}) {
  const router = useRouter();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function save(status: ReviewStatus) {
    if (busy) return;
    setBusy(true); setMessage(""); setError("");
    try {
      await submitReview(accountId, status, note);
      setMessage("Review saved");
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save review");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="review-actions panel">
      <span className="eyebrow">OPERATOR DECISION</span><h2>Review this account</h2>
      <label><span>Review note</span><textarea aria-label="Review note" value={note} onChange={(event) => setNote(event.target.value)} rows={3} placeholder="Optional evidence or decision note" /></label>
      <div><button disabled={busy} onClick={() => save("approved")}>Approve</button><button disabled={busy} onClick={() => save("needs_review")}>Needs review</button><button disabled={busy} className="danger" onClick={() => save("rejected")}>Reject</button></div>
      {message ? <p role="status" className="form-message">{message}</p> : null}
      {error ? <p role="alert" className="form-message form-message--error">{error}</p> : null}
    </section>
  );
}

