import { AccountTable } from "@/components/account-table";
import { api } from "@/lib/api-client";
import type { AccountFilters, LeadGrade, ReviewStatus } from "@/lib/types";


type Params = Record<string, string | string[] | undefined>;


function value(params: Params, key: string): string | undefined {
  const item = params[key];
  return Array.isArray(item) ? item[0] : item;
}


export default async function AccountsPage({ searchParams }: { searchParams: Promise<Params> }) {
  const params = await searchParams;
  const filters: AccountFilters = {
    page: Number(value(params, "page") ?? 1),
    page_size: Number(value(params, "page_size") ?? 25),
    search: value(params, "search"),
    country: value(params, "country"),
    grade: value(params, "grade") as LeadGrade | undefined,
    review_status: value(params, "review_status") as ReviewStatus | undefined,
    sort: (value(params, "sort") as AccountFilters["sort"]) ?? "created_desc",
  };
  let data;
  try {
    data = await api.accounts(filters);
  } catch (error) {
    return <div className="panel state-panel state-panel--error" role="alert">{error instanceof Error ? error.message : "Unable to load accounts"}</div>;
  }
  return (
    <div className="page-stack">
      <section className="page-heading"><div><span className="eyebrow">ACCOUNT DIRECTORY</span><h1>All accounts</h1><p>Evidence-backed companies discovered across active search tasks.</p></div><div className="date-chip">{data.total} total</div></section>
      <AccountTable accounts={data.items} total={data.total} filters={filters} />
    </div>
  );
}
