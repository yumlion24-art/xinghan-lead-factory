import { SearchTaskList } from "@/components/search-task-list";
import { api } from "@/lib/api-client";


export default async function SearchTaskPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ action?: string }> }) {
  const { id } = await params;
  const { action } = await searchParams;
  if (action === "cancel") await api.cancelTask(id);
  const task = await api.task(id);
  return <div className="page-stack"><section className="page-heading"><div><span className="eyebrow">TASK DETAIL</span><h1>{task.query || "Seed URL search"}</h1><p>Progress, failure isolation, and budget consumption.</p></div></section><SearchTaskList tasks={[task]} /></div>;
}

