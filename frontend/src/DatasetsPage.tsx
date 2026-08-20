import type { Dataset } from "./api";
import { PageHeader, StateNotice } from "./AppShell";
import DatasetDetails from "./DatasetDetails";

export default function DatasetsPage({
  datasets,
  loading,
  error,
  onRetry,
  onCreateSession,
}: {
  datasets: Dataset[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onCreateSession: (datasetId: string) => void;
}) {
  return (
    <>
      <PageHeader title="Datasets">Review the public metadata and configuration available for each dataset before creating an analysis session.</PageHeader>
      {loading ? <StateNotice kind="loading">Loading public dataset metadata…</StateNotice> : null}
      {error ? <div><StateNotice kind="error">{error}</StateNotice><button type="button" className="secondary-button" onClick={onRetry}>Retry loading datasets</button></div> : null}
      {!loading && !error && datasets.length === 0 ? <StateNotice>No public datasets are currently available.</StateNotice> : null}
      {!loading && !error ? datasets.map((dataset) => <div key={dataset.dataset_id} className="dataset-detail"><DatasetDetails dataset={dataset} /><button type="button" className="secondary-button" onClick={() => onCreateSession(dataset.dataset_id)}>Create a session for this dataset</button></div>) : null}
    </>
  );
}
