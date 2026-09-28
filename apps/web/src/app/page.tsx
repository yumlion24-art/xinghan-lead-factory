import { Dashboard } from "@/components/dashboard";
import { api } from "@/lib/api-client";


export default async function DashboardPage() {
  let data;
  try {
    const [dashboard, recent] = await Promise.all([
      api.dashboard(),
      api.accounts({ page: 1, page_size: 5, sort: "created_desc" }),
    ]);
    data = { ...dashboard, recent_accounts: recent.items };
  } catch (error) {
    return <Dashboard state="error" error={error instanceof Error ? error.message : "Unable to load dashboard"} />;
  }
  return <Dashboard data={data} />;
}
