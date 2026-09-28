import Link from "next/link";

import { buildAccountQuery } from "@/lib/api-client";
import type { AccountFilters, AccountSummary } from "@/lib/types";
import { StatusBadge } from "./status-badge";


interface AccountTableProps {
  accounts: AccountSummary[];
  total: number;
  filters: AccountFilters;
}


export function AccountTable({ accounts, total, filters }: AccountTableProps) {
  const previous = filters.page > 1 ? { ...filters, page: filters.page - 1 } : null;
  const next = filters.page * filters.page_size < total ? { ...filters, page: filters.page + 1 } : null;

  return (
    <section className="panel accounts-panel">
      <form className="filters" action="/accounts" method="get" aria-label="Account filters">
        <label>
          <span>Search accounts</span>
          <input name="search" defaultValue={filters.search} placeholder="Company or domain" />
        </label>
        <label>
          <span>Country</span>
          <input name="country" defaultValue={filters.country} placeholder="All countries" />
        </label>
        <label>
          <span>Grade</span>
          <select name="grade" defaultValue={filters.grade ?? ""}>
            <option value="">All grades</option><option>A</option><option>B</option><option>C</option>
          </select>
        </label>
        <label>
          <span>Review</span>
          <select name="review_status" defaultValue={filters.review_status ?? ""}>
            <option value="">All states</option>
            <option value="needs_review">Needs review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </label>
        <input type="hidden" name="page_size" value={filters.page_size} />
        <input type="hidden" name="sort" value={filters.sort ?? "created_desc"} />
        <button type="submit">Apply filters</button>
      </form>

      {accounts.length === 0 ? (
        <div className="empty-table">No accounts match these filters</div>
      ) : (
        <div className="table-scroll">
          <table aria-label="Lead accounts">
            <thead><tr><th>Account</th><th>Fit</th><th>Market</th><th>Evidence mode</th><th>Review</th><th>Discovered</th></tr></thead>
            <tbody>
              {accounts.map((account) => (
                <tr key={account.id}>
                  <td>
                    <Link className="account-link" href={`/accounts/${account.id}`}>{account.display_name}</Link>
                    <small>{account.normalized_domain}</small>
                    {account.is_demo ? <span className="demo-label">Synthetic demo</span> : null}
                  </td>
                  <td>
                    <div className="score-cell" aria-label={`${account.display_name} score ${account.score} out of 100`}>
                      <strong>{account.score}</strong><span>/100</span>
                    </div>
                    {account.grade ? <StatusBadge value={account.grade} /> : null}
                  </td>
                  <td><strong>{account.country ?? "Unknown"}</strong><small>{account.company_type ?? "Unclassified"}</small></td>
                  <td><StatusBadge value={account.enrichment_mode === "ai" ? "ai" : "rules_only"} /></td>
                  <td><StatusBadge value={account.review_status} /></td>
                  <td>{new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(account.created_at))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <footer className="table-footer">
        <span>{total.toLocaleString()} accounts · Page {filters.page}</span>
        <div>
          {previous ? <Link href={`/accounts?${buildAccountQuery(previous)}`} aria-label="Previous page">← Previous</Link> : <span />}
          {next ? <Link href={`/accounts?${buildAccountQuery(next)}`} aria-label="Next page">Next →</Link> : null}
        </div>
      </footer>
    </section>
  );
}

