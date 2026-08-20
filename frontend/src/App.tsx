import { useCallback, useEffect, useMemo, useState } from "react";
import { createSession, listDatasets, type Dataset, type Session } from "./api";
import AboutPrivacyPage from "./AboutPrivacyPage";
import AppShell, { PageHeader, StateNotice } from "./AppShell";
import DatasetsPage from "./DatasetsPage";
import ExperimentsPage from "./ExperimentsPage";
import OverviewPage from "./OverviewPage";
import QueryConsole from "./QueryConsole";
import SessionsPage from "./SessionsPage";

type LocationState = { pathname: string; search: string };

function readLocation(): LocationState {
  return { pathname: window.location.pathname, search: window.location.search };
}

function matchingSessionId(pathname: string) {
  const match = /^\/sessions\/([^/]+)$/.exec(pathname);
  return match?.[1] ?? null;
}

export default function App() {
  const [location, setLocation] = useState(readLocation);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetError, setDatasetError] = useState<string | null>(null);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [sessions, setSessions] = useState<Session[]>([]);

  const loadDatasets = useCallback(() =>
    listDatasets()
      .then((loadedDatasets) => setDatasets(loadedDatasets))
      .catch(() => setDatasetError("Unable to load public dataset metadata."))
      .finally(() => setLoadingDatasets(false)), []);

  useEffect(() => { void loadDatasets(); }, [loadDatasets]);
  useEffect(() => {
    const updateLocation = () => setLocation(readLocation());
    window.addEventListener("popstate", updateLocation);
    return () => window.removeEventListener("popstate", updateLocation);
  }, []);

  const navigate = useCallback((href: string) => {
    window.history.pushState({}, "", href);
    setLocation(readLocation());
  }, []);

  const retryDatasets = useCallback(() => {
    setLoadingDatasets(true);
    setDatasetError(null);
    void loadDatasets();
  }, [loadDatasets]);

  const selectedDatasetId = useMemo(() => {
    const requested = new URLSearchParams(location.search).get("dataset");
    return datasets.some((dataset) => dataset.dataset_id === requested) ? requested! : datasets[0]?.dataset_id ?? "";
  }, [datasets, location.search]);

  const updateSession = useCallback((nextSession: Session) => {
    setSessions((current) => [nextSession, ...current.filter((session) => session.session_id !== nextSession.session_id)]);
  }, []);

  async function createAndOpenSession(input: { dataset_id: string; epsilon_total: number; strict_mode: boolean }) {
    const session = await createSession(input);
    updateSession(session);
    navigate(`/sessions/${session.session_id}`);
  }

  const sessionId = matchingSessionId(location.pathname);
  const activeSession = sessionId ? sessions.find((session) => session.session_id === sessionId) : undefined;
  const activeDataset = activeSession ? datasets.find((dataset) => dataset.dataset_id === activeSession.dataset_id) : undefined;
  const context = activeSession && activeDataset ? <><span>{activeDataset.name}</span><span>{activeSession.strict_mode ? "Strict mode" : "Demo mode"}</span><span>Remaining epsilon: {activeSession.epsilon_remaining}</span></> : undefined;

  let content;
  if (location.pathname === "/") {
    content = <OverviewPage datasets={datasets} sessions={sessions} loading={loadingDatasets} error={datasetError} onNavigate={navigate} onRetry={retryDatasets} />;
  } else if (location.pathname === "/datasets") {
    content = <DatasetsPage datasets={datasets} loading={loadingDatasets} error={datasetError} onRetry={retryDatasets} onCreateSession={(datasetId) => navigate(`/sessions?dataset=${encodeURIComponent(datasetId)}`)} />;
  } else if (location.pathname === "/sessions") {
    content = <SessionsPage key={selectedDatasetId} datasets={datasets} selectedDatasetId={selectedDatasetId} sessions={sessions} createSession={createAndOpenSession} onOpenSession={(id) => navigate(`/sessions/${id}`)} />;
  } else if (activeSession && activeDataset) {
    content = <QueryConsole dataset={activeDataset} session={activeSession} onSessionUpdate={updateSession} />;
  } else if (sessionId) {
    content = <><PageHeader title="Session unavailable">This session is not available in the current browser tab.</PageHeader><section className="card"><StateNotice>Sessions are held only for this tab. Create a new session to begin an analysis.</StateNotice><button type="button" onClick={() => navigate("/sessions")}>Create a session</button></section></>;
  } else if (location.pathname === "/experiments") {
    content = <ExperimentsPage />;
  } else if (location.pathname === "/about-privacy") {
    content = <AboutPrivacyPage />;
  } else {
    content = <><PageHeader title="Page not found">Choose a primary application area to continue.</PageHeader><StateNotice>That address is not part of Privata.</StateNotice></>;
  }

  return <AppShell currentPath={sessionId ? "/sessions" : location.pathname} onNavigate={navigate} context={context}>{content}</AppShell>;
}
