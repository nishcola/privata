import { useState, type FormEvent } from "react";
import {
  executeQuery,
  getHistory,
  getSession,
  type CategoricalField,
  type Dataset,
  type QueryHistoryItem,
  type QueryInput,
  type QueryRelease,
  type QueryType,
  type NumericField,
  type Session,
} from "./api";
import Navigation, { type Page } from "./Navigation";

function fieldsForQuery(dataset: Dataset, queryType: QueryType) {
  if (queryType === "COUNT_CATEGORY") {
    return dataset.schema.fields.filter(
      (field): field is CategoricalField => field.field_type === "categorical",
    );
  }
  if (queryType === "MEAN") {
    return dataset.schema.fields.filter(
      (field): field is NumericField => field.field_type === "numeric",
    );
  }
  return dataset.schema.fields.filter(
    (field) => field.field_type === "categorical" || field.histogram_bins !== null,
  );
}

export default function QueryConsole({
  dataset,
  session,
  onNavigate,
}: {
  dataset: Dataset;
  session: Session;
  onNavigate: (page: Page) => void;
}) {
  const [queryType, setQueryType] = useState<QueryType>("COUNT_CATEGORY");
  const validFields = fieldsForQuery(dataset, queryType);
  const [fieldName, setFieldName] = useState(validFields[0]?.name ?? "");
  const selectedField = validFields.find((field) => field.name === fieldName);
  const [category, setCategory] = useState(
    selectedField?.field_type === "categorical" ? selectedField.categories[0] ?? "" : "",
  );
  const [epsilon, setEpsilon] = useState("0.1");
  const [currentSession, setCurrentSession] = useState(session);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [release, setRelease] = useState<QueryRelease | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshSessionState() {
    const [updatedSession, updatedHistory] = await Promise.all([
      getSession(session.session_id),
      getHistory(session.session_id),
    ]);
    setCurrentSession(updatedSession);
    setHistory(updatedHistory);
  }

  function selectQueryType(nextQueryType: QueryType) {
    setQueryType(nextQueryType);
    const nextField = fieldsForQuery(dataset, nextQueryType)[0];
    setFieldName(nextField?.name ?? "");
    setCategory(nextField?.field_type === "categorical" ? nextField.categories[0] ?? "" : "");
  }

  function selectField(nextFieldName: string) {
    setFieldName(nextFieldName);
    const nextField = validFields.find((field) => field.name === nextFieldName);
    setCategory(nextField?.field_type === "categorical" ? nextField.categories[0] ?? "" : "");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const request: QueryInput =
      queryType === "COUNT_CATEGORY"
        ? {
            query_type: "COUNT_CATEGORY",
            field: fieldName,
            category,
            epsilon: Number(epsilon),
          }
        : { query_type: queryType, field: fieldName, epsilon: Number(epsilon) };

    try {
      const nextRelease = await executeQuery(session.session_id, request);
      setRelease(nextRelease);
      await refreshSessionState();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Query failed.");
    }
  }

  return (
    <main className="app-shell">
      <Navigation activePage="query" canUseQuery onNavigate={onNavigate} />
      <header>
        <p className="eyebrow">Privata</p>
        <h1>Query console</h1>
        <p>Server-reported privacy accounting for this session.</p>
      </header>
      <dl className="budget-summary">
        <div>
          <dt>Total epsilon</dt>
          <dd>{currentSession.epsilon_total}</dd>
        </div>
        <div>
          <dt>Spent epsilon</dt>
          <dd>{currentSession.epsilon_spent}</dd>
        </div>
        <div>
          <dt>Remaining epsilon</dt>
          <dd>{currentSession.epsilon_remaining}</dd>
        </div>
      </dl>
      <p className="mode-status">
        {currentSession.strict_mode
          ? "Mode: strict. Ground truth is never returned."
          : "Mode: demo. Ground truth, if returned, is intentionally non-private."}
      </p>
      {error ? <p role="alert">{error}</p> : null}
      <form onSubmit={handleSubmit}>
        <label>
          Query type
          <select
            value={queryType}
            onChange={(event) => selectQueryType(event.target.value as QueryType)}
          >
            <option value="COUNT_CATEGORY">Category count</option>
            <option value="MEAN">Bounded mean</option>
            <option value="HISTOGRAM">Histogram</option>
          </select>
        </label>
        <label>
          Field
          <select value={fieldName} onChange={(event) => selectField(event.target.value)}>
            {validFields.map((field) => (
              <option key={field.name} value={field.name}>
                {field.name}
              </option>
            ))}
          </select>
        </label>
        {queryType === "COUNT_CATEGORY" && selectedField?.field_type === "categorical" ? (
          <label>
            Category
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              {selectedField.categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {queryType === "HISTOGRAM" &&
        selectedField?.field_type === "numeric" &&
        selectedField.histogram_bins ? (
          <p>
            Histogram bins: {formatHistogramIntervals(selectedField.histogram_bins.edges)}
          </p>
        ) : null}
        <label>
          Query epsilon
          <input
            type="number"
            required
            step="any"
            value={epsilon}
            onChange={(event) => setEpsilon(event.target.value)}
          />
        </label>
        <button type="submit">Run query</button>
      </form>
      {release ? (
        <section className="release-card" aria-label="Query release">
          <h2>Latest release</h2>
          <p>Noisy result</p>
          <output className="release-result" aria-label="Noisy result">
            {formatDisplayResult(release.noisy_result)}
          </output>
          {hasHiddenPrecision(release.noisy_result) ? (
            <details className="full-precision">
              <summary>Show full precision</summary>
              <p>{formatResult(release.noisy_result)}</p>
            </details>
          ) : null}
          <dl className="release-metadata">
            <div>
              <dt>Sensitivity</dt>
              <dd>{release.sensitivity}</dd>
            </div>
            <div>
              <dt>Laplace scale</dt>
              <dd>{release.mechanism_scale}</dd>
            </div>
          </dl>
          {!currentSession.strict_mode &&
          release.true_result_is_demo &&
          release.true_result !== undefined ? (
            <p className="demo-truth">
              Demo ground truth (intentionally non-private): {formatResult(release.true_result)}
            </p>
          ) : null}
        </section>
      ) : null}
      <section aria-label="Query history">
        <h2 id="query-history-heading">Query history</h2>
        {history.length === 0 ? (
          <p>No completed private releases yet.</p>
        ) : (
          <div className="history-table-wrapper">
            <table aria-labelledby="query-history-heading">
              <thead>
                <tr>
                  <th scope="col">Query type</th>
                  <th scope="col">Epsilon charged</th>
                  <th scope="col">Remaining epsilon</th>
                  <th scope="col">Released at</th>
                </tr>
              </thead>
              <tbody>
                {history.map((entry) => (
                  <tr key={entry.query_id}>
                    <td>{entry.query_type}</td>
                    <td>{entry.epsilon_charged}</td>
                    <td>{entry.epsilon_remaining}</td>
                    <td>{entry.timestamp}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

type NumericResult = QueryRelease["noisy_result"];

function formatResult(result: NumericResult) {
  return Array.isArray(result) ? result.join(", ") : result;
}

function formatDisplayResult(result: NumericResult) {
  const formatter = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
  return Array.isArray(result)
    ? result.map((value) => formatter.format(value)).join(", ")
    : formatter.format(result);
}

function hasHiddenPrecision(result: QueryRelease["noisy_result"]) {
  return formatDisplayResult(result) !== String(formatResult(result));
}

function formatHistogramIntervals(edges: number[]) {
  return edges
    .slice(0, -1)
    .map((lowerBound, index) => `${lowerBound}–${edges[index + 1]}`)
    .join(", ");
}
