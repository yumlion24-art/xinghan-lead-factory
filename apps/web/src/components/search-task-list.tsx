import Link from "next/link";

import type { SearchTaskSummary } from "@/lib/types";


const active = new Set(["queued", "running"]);


export function SearchTaskList({ tasks }: { tasks: SearchTaskSummary[] }) {
  if (!tasks.length) return <div className="panel empty-table">No search tasks yet</div>;
  return (
    <section className="task-list" aria-label="Search tasks">
      {tasks.map((task) => {
        const succeeded = task.progress.succeeded ?? 0;
        const failed = task.progress.failed ?? 0;
        const processed = task.progress.processed ?? 0;
        const discovered = task.progress.discovered ?? 0;
        return (
          <article className="panel task-card" key={task.id}>
            <div className="task-card__top">
              <div><span className={`task-state task-state--${task.status}`}>{task.status.replaceAll("_", " ")}</span><h2>{task.query || "Seed URL search"}</h2></div>
              <time>{new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(task.created_at))}</time>
            </div>
            <div className="task-progress"><span style={{ width: `${discovered ? Math.min(100, processed / discovered * 100) : 0}%` }} /></div>
            <div className="task-card__meta"><span>{processed} / {discovered} processed</span><span>{succeeded} succeeded / {failed} failed</span><span>{task.budget_usage.pages ?? 0} pages</span></div>
            {task.failure_summary ? <p className="task-failure">{task.failure_summary}</p> : null}
            <footer><Link href={`/search-tasks/${task.id}`}>View task</Link>{active.has(task.status) ? <Link href={`/search-tasks/${task.id}?action=cancel`} aria-label={`Cancel ${task.query || "seed URL search"}`}>Cancel</Link> : null}</footer>
          </article>
        );
      })}
    </section>
  );
}

