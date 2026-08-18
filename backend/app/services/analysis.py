"""Framework-free orchestration of datasets, DP releases, and accounting."""

from collections.abc import Sequence
from threading import Lock
from uuid import uuid4

from app.datasets.models import DatasetSchema
from app.datasets.registry import DatasetRecord, DatasetRegistry
from app.dp.accounting import PrivacySession, PrivacySessionStore
from app.dp.mechanisms.laplace import UniformSampler
from app.dp.models import QueryResultMetadata
from app.dp.queries import (
    HistogramQueryResult,
    ScalarQueryResult,
    execute_count_category,
    execute_histogram,
    execute_mean,
    validate_query_request,
)
from app.dp.queries.models import (
    CountCategoryRequest,
    HistogramRequest,
    MeanRequest,
    QueryRequest,
)
from app.services.models import (
    QueryHistoryResponse,
    QueryReleaseResponse,
    SessionResponse,
)

ExecutedQueryResult = ScalarQueryResult | HistogramQueryResult


class AnalysisService:
    """Coordinate safe public releases without depending on the API layer."""

    def __init__(
        self,
        *,
        dataset_registry: DatasetRegistry,
        session_store: PrivacySessionStore,
        uniform_sampler: UniformSampler | None = None,
    ) -> None:
        self._dataset_registry = dataset_registry
        self._session_store = session_store
        self._uniform_sampler = uniform_sampler
        self._execution_lock = Lock()

    def create_session(
        self, *, dataset_id: str, epsilon_total: float, strict_mode: bool
    ) -> SessionResponse:
        """Verify a public dataset and create a new analysis session."""
        self._dataset_registry.get_schema(dataset_id)
        session = self._session_store.create(
            dataset_id=dataset_id,
            epsilon_total=epsilon_total,
            strict_mode=strict_mode,
        )
        return _session_response(session)

    def get_session(self, *, session_id: str) -> SessionResponse:
        """Return public state for a stored privacy session."""
        return _session_response(self._session_store.get(session_id))

    def get_history(self, *, session_id: str) -> tuple[QueryHistoryResponse, ...]:
        """Return safe accounting metadata for completed releases."""
        session = self._session_store.get(session_id)
        return tuple(
            QueryHistoryResponse(
                query_id=entry.query_id,
                query_type=entry.query_type,
                epsilon_charged=entry.epsilon_charged,
                epsilon_remaining=entry.epsilon_remaining,
                timestamp=entry.timestamp,
            )
            for entry in session.history
        )

    def execute_query(
        self, *, session_id: str, request: QueryRequest
    ) -> QueryReleaseResponse:
        """Execute one valid DP query and charge its budget only on success."""
        with self._execution_lock:
            session = self._session_store.get(session_id)
            metadata = self._dataset_registry.get_metadata(session.dataset_id)
            schema = metadata.dataset_schema
            validate_query_request(request=request, schema=schema)
            session.assert_can_charge(request.epsilon)
            records = self._dataset_registry.get_records(session.dataset_id)

            result = self._execute(request=request, schema=schema, records=records)
            true_result, is_demo = _disclosed_truth(
                strict_mode=session.strict_mode,
                safe_for_demo=metadata.safe_for_demo,
                result=result,
            )
            query_id = str(uuid4())
            session.record_successful_query(
                query_id, request.query_type, request.epsilon
            )
            charge = session.history[-1]
            release_metadata = QueryResultMetadata(
                query_id=query_id,
                query_type=request.query_type,
                dataset_id=session.dataset_id,
                epsilon_charged=charge.epsilon_charged,
                epsilon_remaining=charge.epsilon_remaining,
                sensitivity=result.sensitivity,
                mechanism_name=result.mechanism,
                mechanism_scale=result.scale,
                timestamp=charge.timestamp,
            )
            return QueryReleaseResponse(
                **release_metadata.model_dump(),
                noisy_result=result.noisy_result,
                true_result=true_result,
                true_result_is_demo=is_demo,
            )

    def _execute(
        self,
        *,
        request: QueryRequest,
        schema: DatasetSchema,
        records: Sequence[DatasetRecord],
    ) -> ExecutedQueryResult:
        if isinstance(request, CountCategoryRequest):
            return execute_count_category(
                request=request,
                schema=schema,
                records=records,
                uniform_sampler=self._uniform_sampler,
            )
        if isinstance(request, MeanRequest):
            return execute_mean(
                request=request,
                schema=schema,
                records=records,
                uniform_sampler=self._uniform_sampler,
            )
        if isinstance(request, HistogramRequest):
            return execute_histogram(
                request=request,
                schema=schema,
                records=records,
                uniform_sampler=self._uniform_sampler,
            )
        raise TypeError("request must be a supported QueryRequest")


def _session_response(session: PrivacySession) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        dataset_id=session.dataset_id,
        epsilon_total=session.epsilon_total,
        epsilon_spent=session.epsilon_spent,
        epsilon_remaining=session.epsilon_remaining,
        strict_mode=session.strict_mode,
    )


def _disclosed_truth(
    *,
    strict_mode: bool,
    safe_for_demo: bool,
    result: ExecutedQueryResult,
) -> tuple[int | float | tuple[int, ...] | None, bool | None]:
    if strict_mode or not safe_for_demo:
        return None, None
    return result.true_result, True
