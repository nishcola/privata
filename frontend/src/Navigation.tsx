export type Page = "setup" | "query" | "experiments";

export default function Navigation({
  activePage,
  canUseQuery,
  onNavigate,
}: {
  activePage: Page;
  canUseQuery: boolean;
  onNavigate: (page: Page) => void;
}) {
  return (
    <nav aria-label="Primary navigation">
      <button
        type="button"
        aria-current={activePage === "setup" ? "page" : undefined}
        onClick={() => onNavigate("setup")}
      >
        Setup
      </button>
      <button
        type="button"
        disabled={!canUseQuery}
        aria-current={activePage === "query" ? "page" : undefined}
        onClick={() => onNavigate("query")}
      >
        Query console
      </button>
      <button
        type="button"
        aria-current={activePage === "experiments" ? "page" : undefined}
        onClick={() => onNavigate("experiments")}
      >
        Experiments
      </button>
    </nav>
  );
}
