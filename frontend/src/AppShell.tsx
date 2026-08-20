import type { ReactNode } from "react";
import { formatEpsilon } from "./formatters";

const navigationItems = [
  { href: "/", label: "Overview" },
  { href: "/datasets", label: "Datasets" },
  { href: "/sessions", label: "Sessions" },
  { href: "/experiments", label: "Experiments" },
  { href: "/about-privacy", label: "About Privacy" },
];

export function PageHeader({ title, children }: { title: string; children: ReactNode }) {
  return (
    <header className="page-header">
      <p className="eyebrow">Privata</p>
      <h1>{title}</h1>
      <p>{children}</p>
    </header>
  );
}

export function BudgetSummary({
  epsilonTotal,
  epsilonSpent,
  epsilonRemaining,
}: {
  epsilonTotal: number;
  epsilonSpent: number;
  epsilonRemaining: number;
}) {
  return (
    <dl className="budget-summary">
      <div>
        <dt>Total epsilon</dt>
        <dd>{formatEpsilon(epsilonTotal)}</dd>
      </div>
      <div>
        <dt>Spent epsilon</dt>
        <dd>{formatEpsilon(epsilonSpent)}</dd>
      </div>
      <div>
        <dt>Remaining epsilon</dt>
        <dd>{formatEpsilon(epsilonRemaining)}</dd>
      </div>
    </dl>
  );
}

export function StateNotice({
  children,
  kind = "empty",
}: {
  children: ReactNode;
  kind?: "empty" | "error" | "loading";
}) {
  return (
    <p className={`state-notice state-notice-${kind}`} role={kind === "error" ? "alert" : undefined}>
      {children}
    </p>
  );
}

export default function AppShell({
  children,
  currentPath,
  onNavigate,
  context,
}: {
  children: ReactNode;
  currentPath: string;
  onNavigate: (href: string) => void;
  context?: ReactNode;
}) {
  function followLink(event: React.MouseEvent<HTMLAnchorElement>, href: string) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    event.preventDefault();
    onNavigate(href);
  }

  return (
    <main className="app-shell">
      <aside className="app-sidebar">
        <a className="brand" href="/" onClick={(event) => followLink(event, "/")}>
          <span className="brand-mark" aria-hidden="true">P</span>
          <span>
            <strong>Privata</strong>
            <small>Private analytics, explained</small>
          </span>
        </a>
        <nav aria-label="Primary navigation">
          {navigationItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              aria-current={currentPath === item.href ? "page" : undefined}
              onClick={(event) => followLink(event, item.href)}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </aside>
      <div className="app-content">
        {context ? <div className="app-context">{context}</div> : null}
        {children}
      </div>
    </main>
  );
}
