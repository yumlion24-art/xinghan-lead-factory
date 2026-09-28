import type {
  AccountDetailData,
  AccountFilters,
  AccountListResponse,
  DashboardData,
  ReviewStatus,
  SearchTaskCreate,
  SearchTaskSummary,
} from "./types";


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
  account: (id: string) => request<AccountDetailData>(`/accounts/${id}`),
  submitReview: (accountId: string, status: ReviewStatus, note: string) =>
    request(`/accounts/${accountId}/review`, {
      method: "POST",
      body: JSON.stringify({ status, note }),
    }),
  tasks: () => request<{ items: SearchTaskSummary[] }>("/search-tasks"),
  task: (id: string) => request<SearchTaskSummary>(`/search-tasks/${id}`),
  createTask: (body: SearchTaskCreate) =>
    request<SearchTaskSummary>("/search-tasks", { method: "POST", body: JSON.stringify(body) }),
  cancelTask: (id: string) => request(`/search-tasks/${id}/cancel`, { method: "POST" }),
};
