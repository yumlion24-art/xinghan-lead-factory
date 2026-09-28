import type { AccountFilters, AccountListResponse, DashboardData } from "./types";


const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";


export function buildAccountQuery(filters: AccountFilters): string {
  const params = new URLSearchParams();
  const ordered: Array<[string, string | number | undefined]> = [
    ["page", filters.page],
    ["page_size", filters.page_size],
    ["search", filters.search],
    ["country", filters.country],
    ["icp", filters.icp],
    ["grade", filters.grade],
    ["review_status", filters.review_status],
    ["sort", filters.sort],
  ];
  for (const [key, value] of ordered) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  return params.toString();
}


async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message = payload?.error?.message ?? `API request failed (${response.status})`;
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}


export const api = {
  dashboard: () => request<DashboardData>("/dashboard"),
  accounts: (filters: AccountFilters) =>
    request<AccountListResponse>(`/accounts?${buildAccountQuery(filters)}`),
};

