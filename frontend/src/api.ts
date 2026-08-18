export type NumericField = {
  name: string;
  field_type: "numeric";
  value_type: "integer" | "float";
  lower_bound: number;
  upper_bound: number;
  histogram_bins: { edges: number[] } | null;
};

export type CategoricalField = {
  name: string;
  field_type: "categorical";
  categories: string[];
};

export type Dataset = {
  dataset_id: string;
  name: string;
  row_count: number;
  safe_for_demo: boolean;
  schema: { fields: Array<NumericField | CategoricalField> };
};

export type ApiErrorPayload = {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
};

export type Session = {
  session_id: string;
  dataset_id: string;
  epsilon_total: number;
  epsilon_spent: number;
  epsilon_remaining: number;
  strict_mode: boolean;
};

export type QueryType = "COUNT_CATEGORY" | "MEAN" | "HISTOGRAM";

export type QueryInput =
  | { query_type: "COUNT_CATEGORY"; field: string; category: string; epsilon: number }
  | { query_type: "MEAN" | "HISTOGRAM"; field: string; epsilon: number };

export type QueryRelease = {
  query_id: string;
  query_type: QueryType;
  dataset_id: string;
  epsilon_charged: number;
  epsilon_remaining: number;
  sensitivity: number;
  mechanism_name: "laplace";
  mechanism_scale: number;
  timestamp: string;
  noisy_result: number | number[];
  true_result?: number | number[];
  true_result_is_demo?: boolean;
};

export type QueryHistoryItem = {
  query_id: string;
  query_type: QueryType;
  epsilon_charged: number;
  epsilon_remaining: number;
  timestamp: string;
};

export class ApiError extends Error {
  readonly code: string;

  constructor(payload: ApiErrorPayload) {
    super(payload.error.message);
    this.code = payload.error.code;
  }
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(new URL(path, apiBaseUrl), init);
  const payload: unknown = await response.json();

  if (!response.ok) {
    throw new ApiError(payload as ApiErrorPayload);
  }

  return payload as T;
}

export function listDatasets(): Promise<Dataset[]> {
  return request<Dataset[]>("/datasets");
}

export function createSession(input: {
  dataset_id: string;
  epsilon_total: number;
  strict_mode: boolean;
}): Promise<Session> {
  return request<Session>("/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function getSession(sessionId: string): Promise<Session> {
  return request<Session>(`/sessions/${sessionId}`);
}

export function getHistory(sessionId: string): Promise<QueryHistoryItem[]> {
  return request<QueryHistoryItem[]>(`/sessions/${sessionId}/history`);
}

export function executeQuery(
  sessionId: string,
  input: QueryInput,
): Promise<QueryRelease> {
  return request<QueryRelease>(`/sessions/${sessionId}/queries`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}
