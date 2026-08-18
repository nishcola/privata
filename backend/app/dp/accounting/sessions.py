"""In-memory pure-epsilon privacy session accounting."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from numbers import Real
from uuid import uuid4

from app.dp.queries.models import QueryType
from app.errors import BudgetExceededError, InvalidEpsilonError, UnknownSessionError

MAX_QUERY_EPSILON = 10.0
"""Public educational maximum for one query's epsilon allocation."""

BUDGET_TOLERANCE = 1e-12
"""Residue allowed only when normalizing a nearly exhausted float budget."""


@dataclass(frozen=True, slots=True)
class QueryChargeHistoryEntry:
    """Safe metadata for a query that has already completed successfully."""

    query_id: str
    query_type: QueryType
    epsilon_charged: float
    epsilon_remaining: float
    timestamp: datetime


class PrivacySession:
    """Mutable accounting state for one dataset's in-memory analysis session."""

    __slots__ = (
        "_dataset_id",
        "_epsilon_spent",
        "_epsilon_total",
        "_history",
        "_session_id",
        "_strict_mode",
    )

    def __init__(
        self,
        *,
        session_id: str,
        dataset_id: str,
        epsilon_total: float,
        strict_mode: bool,
    ) -> None:
        self._session_id = _nonempty_string(session_id, "session_id")
        self._dataset_id = _nonempty_string(dataset_id, "dataset_id")
        self._epsilon_total = _positive_epsilon(epsilon_total)
        if type(strict_mode) is not bool:
            raise ValueError("strict_mode must be a boolean")
        self._strict_mode = strict_mode
        self._epsilon_spent = 0.0
        self._history: list[QueryChargeHistoryEntry] = []

    @property
    def session_id(self) -> str:
        """Return the immutable session identifier."""
        return self._session_id

    @property
    def dataset_id(self) -> str:
        """Return the immutable dataset identifier."""
        return self._dataset_id

    @property
    def epsilon_total(self) -> float:
        """Return the configured total epsilon budget."""
        return self._epsilon_total

    @property
    def epsilon_spent(self) -> float:
        """Return epsilon charged to successful queries."""
        return self._epsilon_spent

    @property
    def epsilon_remaining(self) -> float:
        """Return remaining epsilon after completed-charge normalization."""
        remaining = self._epsilon_total - self._epsilon_spent
        if remaining <= 0.0:
            return 0.0
        return remaining

    @property
    def strict_mode(self) -> bool:
        """Return whether true query results must remain suppressed."""
        return self._strict_mode

    @property
    def history(self) -> tuple[QueryChargeHistoryEntry, ...]:
        """Return immutable safe metadata for successful query charges."""
        return tuple(self._history)

    def assert_can_charge(self, epsilon: float) -> None:
        """Validate a requested epsilon allocation without changing session state."""
        requested_epsilon = _query_epsilon(epsilon)
        remaining_epsilon = self.epsilon_remaining
        if (
            remaining_epsilon == 0.0
            or requested_epsilon > remaining_epsilon + BUDGET_TOLERANCE
        ):
            raise BudgetExceededError(requested_epsilon, remaining_epsilon)

    def record_successful_query(
        self,
        query_id: str,
        query_type: QueryType,
        epsilon: float,
        *,
        timestamp: datetime | None = None,
    ) -> None:
        """Charge a completed query and append only its safe history metadata."""
        validated_query_id = _nonempty_string(query_id, "query_id")
        if not isinstance(query_type, QueryType):
            raise ValueError("query_type must be a QueryType")
        completed_at = _utc_timestamp(timestamp)
        requested_epsilon = _query_epsilon(epsilon)
        self.assert_can_charge(requested_epsilon)

        new_spent = self._epsilon_spent + requested_epsilon
        if self._epsilon_total - new_spent <= BUDGET_TOLERANCE:
            new_spent = self._epsilon_total
        self._epsilon_spent = new_spent
        self._history.append(
            QueryChargeHistoryEntry(
                query_id=validated_query_id,
                query_type=query_type,
                epsilon_charged=requested_epsilon,
                epsilon_remaining=self.epsilon_remaining,
                timestamp=completed_at,
            )
        )


class PrivacySessionStore:
    """In-memory session storage for the single-process MVP."""

    def __init__(self) -> None:
        self._sessions: dict[str, PrivacySession] = {}

    def create(
        self, *, dataset_id: str, epsilon_total: float, strict_mode: bool
    ) -> PrivacySession:
        """Create and retain a session with an opaque UUID identifier."""
        session = PrivacySession(
            session_id=str(uuid4()),
            dataset_id=dataset_id,
            epsilon_total=epsilon_total,
            strict_mode=strict_mode,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> PrivacySession:
        """Return a stored session or raise the stable unknown-session error."""
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise UnknownSessionError(session_id) from error


def _positive_epsilon(epsilon: float) -> float:
    if isinstance(epsilon, bool) or not isinstance(epsilon, Real):
        raise InvalidEpsilonError()
    numeric_epsilon = float(epsilon)
    if not math.isfinite(numeric_epsilon) or numeric_epsilon <= 0.0:
        raise InvalidEpsilonError()
    return numeric_epsilon


def _query_epsilon(epsilon: float) -> float:
    numeric_epsilon = _positive_epsilon(epsilon)
    if numeric_epsilon > MAX_QUERY_EPSILON:
        raise InvalidEpsilonError()
    return numeric_epsilon


def _nonempty_string(value: str, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _utc_timestamp(timestamp: datetime | None) -> datetime:
    completed_at = datetime.now(UTC) if timestamp is None else timestamp
    if not isinstance(completed_at, datetime) or completed_at.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return completed_at.astimezone(UTC)
