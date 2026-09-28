import { AccountDetail } from "@/components/account-detail";
import { api } from "@/lib/api-client";


export default async function AccountPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const account = await api.account(id);
  return <AccountDetail account={account} />;
}

