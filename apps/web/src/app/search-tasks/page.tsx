import { SearchTaskForm } from "@/components/search-task-form";
import { SearchTaskList } from "@/components/search-task-list";
import { api } from "@/lib/api-client";
import type { SearchTaskSummary } from "@/lib/types";


export default async function SearchTasksPage() {
  let tasks: SearchTaskSummary[] = [];
  let error = "";
  try { tasks = (await api.tasks()).items; } catch (reason) { error = reason instanceof Error ? reason.message : "Unable to load tasks"; }
  return <div className="page-stack"><section className="page-heading"><div><span className="eyebrow">PUBLIC-WEB DISCOVERY</span><h1>Search tasks</h1><p>Bound each run by market, ICP, domains, pages, and cost.</p></div></section><div className="tasks-layout"><SearchTaskForm /><div>{error ? <div role="alert" className="panel state-panel state-panel--error">{error}</div> : <SearchTaskList tasks={tasks} />}</div></div></div>;
}
