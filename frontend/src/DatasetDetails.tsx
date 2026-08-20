import type { Dataset } from "./api";

export default function DatasetDetails({ dataset }: { dataset: Dataset }) {
  return (
    <section className="card" aria-label={dataset.name}>
      <h2>{dataset.name}</h2>
      <dl className="dataset-facts">
        <div><dt>Rows</dt><dd>{dataset.row_count} public rows</dd></div>
        <div><dt>Demo mode</dt><dd><span className="status-chip">{dataset.safe_for_demo ? "Demo eligible" : "Demo unavailable"}</span></dd></div>
      </dl>
      <div className="schema-table-wrapper">
        <table className="schema-table" aria-label="Public schema">
          <thead><tr><th scope="col">Field</th><th scope="col">Type</th><th scope="col">Public configuration</th></tr></thead>
          <tbody>
            {dataset.schema.fields.map((field) => (
              <tr key={field.name}>
                <td>{field.name}</td>
                <td>{field.field_type === "numeric" ? "Numeric" : "Category"}</td>
                <td>{field.field_type === "numeric" ? <><span>{field.lower_bound}–{field.upper_bound}</span>{field.histogram_bins ? <details><summary><span>{field.histogram_bins.edges.length - 1} public bins</span><span>Show public bin edges</span></summary><p>{field.histogram_bins.edges.join(", ")}</p></details> : null}</> : <div className="category-list">{field.categories.map((category) => <span key={category} className="category-chip">{category}</span>)}</div>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
