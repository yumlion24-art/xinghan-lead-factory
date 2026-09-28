import { SearchTaskList } from "@/components/search-task-list";
import { api } from "@/lib/api-client";


export default async function SearchTaskPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const task = await api.task(id);
  return <div className="page-stack"><section className="page-heading"><div><span className="eyebrow">TASK DETAIL</span><h1>{task.query || "Seed URL search"}</h1><p>Progress, failure isolation, and budget consumption.</p></div></section><SearchTaskList tasks={[task]} /></div>;
}
