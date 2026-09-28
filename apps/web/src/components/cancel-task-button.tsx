"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api-client";

export function CancelTaskButton({ taskId, label }: { taskId: string; label: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function cancel() {
    setBusy(true);
    setError("");
    try {
      await api.cancelTask(taskId);
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to cancel task");
      setBusy(false);
    }
  }

  return <><button type="button" disabled={busy} onClick={cancel} aria-label={`Cancel ${label}`}>{busy ? "Cancelling…" : "Cancel"}</button>{error ? <span role="alert">{error}</span> : null}</>;
}
