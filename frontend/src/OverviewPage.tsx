import type { Dataset, Session } from "./api";
import { BudgetSummary, PageHeader, StateNotice } from "./AppShell";

export default function OverviewPage({
  datasets,
  sessions,
  loading,
  error,
  onNavigate,
  onRetry,
}: {
  datasets: Dataset[];
  sessions: Session[];
  loading: boolean;
  error: string | null;
  onNavigate: (href: string) => void;
  onRetry: () => void;
}) {
  const activeSession = sessions[0];
  return (
    <>
      <PageHeader title="Overview">Privata is an educational, local-first differential privacy analytics application for supported aggregate releases.</PageHeader>
      <div className="overview-grid">
        <section className="card overview-intro">
          <h2>Start with public configuration</h2>
          <p>Review a dataset’s public schema, choose a session budget, then run supported aggregate queries. Privata reports the server-calculated privacy accounting for each completed release.</p>
          <div className="action-row"><button type="button" onClick={() => onNavigate("/sessions")}>Create a session</button><button type="button" className="secondary-button" onClick={() => onNavigate("/experiments")}>Explore experiments</button></div>
        </section>
        <section className="card">
          <h2>Analysis sessions</h2>
          {activeSession ? <><p>Active session for {activeSession.dataset_id}</p><BudgetSummary epsilonTotal={activeSession.epsilon_total} epsilonSpent={activeSession.epsilon_spent} epsilonRemaining={activeSession.epsilon_remaining} /><button type="button" className="secondary-button" onClick={() => onNavigate(`/sessions/${activeSession.session_id}`)}>Open session</button></> : <StateNotice>No analysis sessions have been created in this tab.</StateNotice>}
        </section>
      </div>
      <section className="section-block">
        <div className="section-heading"><div><h2>Available datasets</h2><p>Dataset metadata and schemas are public configuration.</p></div><button type="button" className="text-button" onClick={() => onNavigate("/datasets")}>View datasets</button></div>
        {loading ? <StateNotice kind="loading">Loading public dataset metadata…</StateNotice> : null}
        {error ? <div><StateNotice kind="error">{error}</StateNotice><button type="button" className="secondary-button" onClick={onRetry}>Retry loading datasets</button></div> : null}
        {!loading && !error ? <div className="dataset-card-grid">{datasets.map((dataset) => <article key={dataset.dataset_id} className="card compact-card"><h3>{dataset.name}</h3><p>{dataset.row_count} public rows</p><span className="status-chip">{dataset.safe_for_demo ? "Demo eligible" : "Demo unavailable"}</span></article>)}</div> : null}
      </section>
    </>
  );
}
