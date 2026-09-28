"use client";

import { FormEvent, useState } from "react";

import { api } from "@/lib/api-client";
import type { SearchTaskCreate, SearchTaskSummary } from "@/lib/types";


export function SearchTaskForm({
  submitTask = api.createTask,
}: {
  submitTask?: (body: SearchTaskCreate) => Promise<SearchTaskSummary>;
}) {
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [message, setMessage] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const query = String(form.get("query") ?? "").trim();
    const countries = String(form.get("countries") ?? "").split(",").map((item) => item.trim()).filter(Boolean);
    const icp = String(form.get("icp") ?? "");
    const seeds = String(form.get("seed_urls") ?? "").split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
    const maxResults = Number(form.get("max_results"));
    const maxPages = Number(form.get("max_pages_per_domain"));
    const nextErrors: string[] = [];
    if (!query && seeds.length === 0) nextErrors.push("Enter a search query or at least one seed URL");
    if (!Number.isInteger(maxResults) || maxResults < 1 || maxResults > 100) nextErrors.push("Maximum results must be between 1 and 100");
    if (!Number.isInteger(maxPages) || maxPages < 1 || maxPages > 20) nextErrors.push("Pages per domain must be between 1 and 20");
    if (seeds.some((url) => !/^https?:\/\//i.test(url))) nextErrors.push("Seed URL must start with http:// or https://");
    if (nextErrors.length) { setErrors(nextErrors); return; }

    setBusy(true); setErrors([]); setMessage("");
    try {
      const task = await submitTask({
        query,
        countries,
        icp_ids: icp ? [icp] : [],
        seed_urls: seeds,
        max_results: maxResults,
        max_pages_per_domain: maxPages,
      });
      setMessage(`Task ${task.id} created`);
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Unable to create task"]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="task-form panel" onSubmit={onSubmit} noValidate>
      <div className="panel__heading"><div><span className="eyebrow">NEW DISCOVERY RUN</span><h2>Search configuration</h2></div></div>
      {errors.length ? <div role="alert" className="form-message form-message--error">{errors.map((error) => <div key={error}>{error}</div>)}</div> : null}
      {message ? <div role="status" className="form-message">{message}</div> : null}
      <label className="task-form__wide"><span>Search query</span><input name="query" aria-label="Search query" placeholder="e.g. airline catering procurement UAE" /></label>
      <label><span>Countries</span><input name="countries" aria-label="Countries" placeholder="UAE, Singapore" /></label>
      <label><span>ICP</span><select name="icp" aria-label="ICP" defaultValue="aviation_catering"><option value="aviation_catering">Aviation catering</option><option value="foodservice_distribution">Foodservice distribution</option><option value="sustainable_buyers">Sustainable buyers</option></select></label>
      <label className="task-form__wide"><span>Seed URLs — one per line</span><textarea name="seed_urls" aria-label="Seed URLs" rows={4} placeholder="https://company.example" /></label>
      <label><span>Maximum results</span><input name="max_results" aria-label="Maximum results" type="number" min="1" max="100" defaultValue="20" /></label>
      <label><span>Pages per domain</span><input name="max_pages_per_domain" aria-label="Pages per domain" type="number" min="1" max="20" defaultValue="4" /></label>
      <button type="submit" disabled={busy}>{busy ? "Creating…" : "Create search task"}</button>
    </form>
  );
}

