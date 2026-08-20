import { useState, type FormEvent } from "react";
import type { Dataset, Session } from "./api";
import { BudgetSummary, PageHeader, StateNotice } from "./AppShell";

export default function SessionsPage({
  datasets,
  selectedDatasetId,
  sessions,
  createSession,
  onOpenSession,
}: {
  datasets: Dataset[];
  selectedDatasetId: string;
  sessions: Session[];
  createSession: (input: { dataset_id: string; epsilon_total: number; strict_mode: boolean }) => Promise<void>;
  onOpenSession: (sessionId: string) => void;
}) {
  const [datasetId, setDatasetId] = useState(selectedDatasetId);
  const [epsilonTotal, setEpsilonTotal] = useState("1");
  const [strictMode, setStrictMode] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setCreating(true);
    try {
      await createSession({ dataset_id: datasetId, epsilon_total: Number(epsilonTotal), strict_mode: strictMode });
    } catch {
      setError("The session could not be created. Check the public configuration.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <>
      <PageHeader title="Sessions">Create a session with public configuration, then follow the server-reported accounting for its completed releases.</PageHeader>
      <div className="sessions-layout">
        <section className="card">
          <h2>Set up a privacy session</h2>
          {error ? <StateNotice kind="error">{error}</StateNotice> : null}
          <form onSubmit={handleSubmit}>
            <label>Dataset<select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>{datasets.map((dataset) => <option key={dataset.dataset_id} value={dataset.dataset_id}>{dataset.name}</option>)}</select></label>
            <label>Total epsilon<input type="number" required step="any" value={epsilonTotal} onChange={(event) => setEpsilonTotal(event.target.value)} /></label>
            <fieldset><legend>Release mode</legend><label><input type="radio" name="release-mode" checked={strictMode} onChange={() => setStrictMode(true)} />Strict mode</label><label><input type="radio" name="release-mode" checked={!strictMode} onChange={() => setStrictMode(false)} />Demo mode</label></fieldset>
            <p>Strict mode never returns ground truth. Demo ground truth is intentionally non-private and is available only when the dataset is safe for demonstration.</p>
            <button type="submit" disabled={!datasetId || creating}>{creating ? "Creating session…" : "Create session"}</button>
          </form>
        </section>
        <section className="card">
          <h2>Active and recent sessions</h2>
          {sessions.length === 0 ? <StateNotice>No analysis sessions have been created in this tab.</StateNotice> : <div className="session-list">{sessions.map((session) => <article key={session.session_id} className="session-card"><div><h3>{session.dataset_id}</h3><p>{session.strict_mode ? "Strict mode" : "Demo mode"}</p></div><BudgetSummary epsilonTotal={session.epsilon_total} epsilonSpent={session.epsilon_spent} epsilonRemaining={session.epsilon_remaining} /><button type="button" className="secondary-button" onClick={() => onOpenSession(session.session_id)}>Open query console</button></article>)}</div>}
        </section>
      </div>
    </>
  );
}
