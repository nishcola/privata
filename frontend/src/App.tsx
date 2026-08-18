import { useEffect, useState, type FormEvent } from "react";
import {
  createSession,
  listDatasets,
  type Dataset,
  type Session,
} from "./api";
import QueryConsole from "./QueryConsole";
import ExperimentsPage from "./ExperimentsPage";
import Navigation, { type Page } from "./Navigation";

function SchemaSummary({ dataset }: { dataset: Dataset }) {
  return (
    <div className="schema-table-wrapper">
      <table className="schema-table" aria-label="Public schema">
        <thead>
          <tr>
            <th scope="col">Field</th>
            <th scope="col">Type</th>
            <th scope="col">Public configuration</th>
          </tr>
        </thead>
        <tbody>
          {dataset.schema.fields.map((field) => (
            <tr key={field.name}>
              <td>{field.name}</td>
              <td>{field.field_type === "numeric" ? "Numeric" : "Category"}</td>
              <td>
                {field.field_type === "numeric" ? (
                  <>
                    <span>
                      {field.lower_bound}–{field.upper_bound}
                    </span>
                    {field.histogram_bins ? (
                      <details>
                        <summary>
                          <span>{field.histogram_bins.edges.length - 1} public bins</span>
                          <span>Show public bin edges</span>
                        </summary>
                        <p>{field.histogram_bins.edges.join(", ")}</p>
                      </details>
                    ) : null}
                  </>
                ) : (
                  <div className="category-list">
                    {field.categories.map((category) => (
                      <span key={category} className="category-chip">
                        {category}
                      </span>
                    ))}
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>("setup");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [epsilonTotal, setEpsilonTotal] = useState("1");
  const [strictMode, setStrictMode] = useState(true);
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listDatasets()
      .then((loadedDatasets) => {
        setDatasets(loadedDatasets);
        setSelectedDatasetId(loadedDatasets[0]?.dataset_id ?? "");
      })
      .catch(() => setError("Unable to load public dataset metadata."));
  }, []);

  const selectedDataset = datasets.find(
    (dataset) => dataset.dataset_id === selectedDatasetId,
  );

  async function handleCreateSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      const createdSession = await createSession({
        dataset_id: selectedDatasetId,
        epsilon_total: Number(epsilonTotal),
        strict_mode: strictMode,
      });
      setSession(createdSession);
      setPage("query");
    } catch {
      setError("The session could not be created. Check the public configuration.");
    }
  }

  if (page === "experiments") {
    return (
      <main className="app-shell">
        <Navigation activePage={page} canUseQuery={session !== null} onNavigate={setPage} />
        <ExperimentsPage />
      </main>
    );
  }

  if (page === "query" && session) {
    return selectedDataset ? (
      <QueryConsole
        dataset={selectedDataset}
        session={session}
        onNavigate={setPage}
      />
    ) : null;
  }

  return (
    <main className="app-shell">
      <Navigation activePage={page} canUseQuery={session !== null} onNavigate={setPage} />
      <header>
        <p className="eyebrow">Privata</p>
        <h1>Set up a privacy session</h1>
        <p>
          Choose public configuration for a differential privacy analysis session.
        </p>
      </header>
      {error ? <p role="alert">{error}</p> : null}
      <form onSubmit={handleCreateSession}>
        <label>
          Dataset
          <select
            value={selectedDatasetId}
            onChange={(event) => setSelectedDatasetId(event.target.value)}
          >
            {datasets.map((dataset) => (
              <option key={dataset.dataset_id} value={dataset.dataset_id}>
                {dataset.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Total epsilon
          <input
            type="number"
            required
            step="any"
            value={epsilonTotal}
            onChange={(event) => setEpsilonTotal(event.target.value)}
          />
        </label>
        <fieldset>
          <legend>Release mode</legend>
          <label>
            <input
              type="radio"
              name="release-mode"
              checked={strictMode}
              onChange={() => setStrictMode(true)}
            />
            Strict mode
          </label>
          <label>
            <input
              type="radio"
              name="release-mode"
              checked={!strictMode}
              onChange={() => setStrictMode(false)}
            />
            Demo mode
          </label>
        </fieldset>
        <p>
          Strict mode never returns ground truth. Demo ground truth is intentionally
          non-private and is available only when the dataset is safe for demonstration.
        </p>
        <button type="submit" disabled={!selectedDataset}>
          Create session
        </button>
      </form>
      {selectedDataset ? (
        <section aria-label={selectedDataset.name}>
          <h2>{selectedDataset.name}</h2>
          <dl className="dataset-facts">
            <div>
              <dt>Rows</dt>
              <dd>{selectedDataset.row_count} public rows</dd>
            </div>
            <div>
              <dt>Demo mode</dt>
              <dd>
                <span className="status-chip">
                  {selectedDataset.safe_for_demo ? "Demo eligible" : "Demo unavailable"}
                </span>
              </dd>
            </div>
          </dl>
          <SchemaSummary dataset={selectedDataset} />
        </section>
      ) : null}
    </main>
  );
}
