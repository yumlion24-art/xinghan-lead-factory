import Link from "next/link";
import type { ReactNode } from "react";


const navigation = [
  { href: "/", label: "Dashboard", mark: "01" },
  { href: "/accounts", label: "Accounts", mark: "02" },
  { href: "/leads/A", label: "A leads", mark: "A" },
  { href: "/leads/B", label: "B leads", mark: "B" },
  { href: "/leads/C", label: "C leads", mark: "C" },
  { href: "/search-tasks", label: "Search tasks", mark: "03" },
];


export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="Xinghan Lead Factory home">
          <span className="brand__signal" aria-hidden="true">XH</span>
          <span>
            <strong>Lead Factory</strong>
            <small>XINGHAN / V1</small>
          </span>
        </Link>
        <nav aria-label="Primary navigation" className="nav-list">
          {navigation.map((item) => (
            <Link href={item.href} key={item.href}>
              <span>{item.mark}</span>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebar__footer">
          <span className="pulse-dot" aria-hidden="true" /> Local workspace
          <small>No automated outreach</small>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">B2B ACCOUNT INTELLIGENCE</span>
            <strong>Guangdong Xinghan Industrial</strong>
          </div>
          <Link className="topbar__action" href="/search-tasks">+ New search task</Link>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}

