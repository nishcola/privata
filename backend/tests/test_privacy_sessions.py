from dataclasses import fields
from datetime import UTC, datetime

import pytest

from app.dp.accounting import (
    PrivacySession,
    PrivacySessionStore,
    QueryChargeHistoryEntry,
)
from app.dp.queries.models import QueryType
from app.errors import BudgetExceededError, InvalidEpsilonError, UnknownSessionError


def session(*, epsilon_total: float = 1.0) -> PrivacySession:
    return PrivacySession(
        session_id="session-1",
        dataset_id="synthetic-workforce",
        epsilon_total=epsilon_total,
        strict_mode=True,
    )


def state(
    value: PrivacySession,
) -> tuple[float, float, tuple[QueryChargeHistoryEntry, ...]]:
    return value.epsilon_spent, value.epsilon_remaining, value.history


def test_fresh_session_exposes_immutable_metadata_and_full_budget() -> None:
    value = session(epsilon_total=2.0)

    assert value.session_id == "session-1"
    assert value.dataset_id == "synthetic-workforce"
    assert value.epsilon_total == 2.0
    assert value.strict_mode is True
    assert value.epsilon_spent == 0.0
    assert value.epsilon_remaining == 2.0
    assert value.history == ()
    with pytest.raises(AttributeError):
        value.epsilon_spent = 1.0


def test_preflight_is_non_mutating_and_successful_charge_records_safe_history() -> None:
    value = session()
    timestamp = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)

    value.assert_can_charge(0.25)
    assert state(value) == (0.0, 1.0, ())

    value.record_successful_query(
        query_id="query-1",
        query_type=QueryType.MEAN,
        epsilon=0.25,
        timestamp=timestamp,
    )

    assert value.epsilon_spent == 0.25
    assert value.epsilon_remaining == 0.75
    assert value.history == (
        QueryChargeHistoryEntry(
            query_id="query-1",
            query_type=QueryType.MEAN,
            epsilon_charged=0.25,
            epsilon_remaining=0.75,
            timestamp=timestamp,
        ),
    )


def test_sequential_successful_charges_add_to_spent_budget() -> None:
    value = session(epsilon_total=2.0)

    value.record_successful_query("query-1", QueryType.COUNT_CATEGORY, 0.25)
    value.record_successful_query("query-2", QueryType.HISTOGRAM, 0.5)

    assert value.epsilon_spent == 0.75
    assert value.epsilon_remaining == 1.25


def test_final_charge_accepts_floating_point_residue_and_exhausts_budget() -> None:
    value = session(epsilon_total=0.3)

    value.record_successful_query("query-1", QueryType.MEAN, 0.1)
    value.record_successful_query("query-2", QueryType.MEAN, 0.2)

    assert value.epsilon_spent == 0.3
    assert value.epsilon_remaining == 0.0


def test_small_positive_budget_is_available_before_its_first_charge() -> None:
    value = session(epsilon_total=1e-13)

    value.assert_can_charge(1e-13)
    value.record_successful_query("query-1", QueryType.MEAN, 1e-13)

    assert value.epsilon_spent == 1e-13
    assert value.epsilon_remaining == 0.0


def test_over_budget_charge_is_rejected_without_changing_session_state() -> None:
    value = session(epsilon_total=0.5)
    value.record_successful_query("query-1", QueryType.MEAN, 0.25)
    before = state(value)

    with pytest.raises(BudgetExceededError):
        value.assert_can_charge(0.26)

    assert state(value) == before

    with pytest.raises(BudgetExceededError):
        value.record_successful_query("query-2", QueryType.MEAN, 0.26)

    assert state(value) == before


@pytest.mark.parametrize(
    "epsilon", [0.0, -1.0, float("nan"), float("inf"), float("-inf"), True, "0.1", 10.1]
)
def test_invalid_charge_epsilon_leaves_session_state_unchanged(epsilon: object) -> None:
    value = session()
    before = state(value)

    with pytest.raises(InvalidEpsilonError):
        value.record_successful_query("query-1", QueryType.MEAN, epsilon)

    assert state(value) == before


def test_default_per_query_epsilon_maximum_is_accepted() -> None:
    value = session(epsilon_total=10.0)

    value.record_successful_query("query-1", QueryType.MEAN, 10.0)

    assert value.epsilon_spent == 10.0
    assert value.epsilon_remaining == 0.0


def test_identical_successful_queries_are_each_charged_and_recorded() -> None:
    value = session()

    value.record_successful_query("query-1", QueryType.MEAN, 0.25)
    value.record_successful_query("query-1", QueryType.MEAN, 0.25)

    assert value.epsilon_spent == 0.5
    assert len(value.history) == 2
    assert [entry.epsilon_charged for entry in value.history] == [0.25, 0.25]


def test_history_entry_has_only_safe_charge_metadata() -> None:
    assert {field.name for field in fields(QueryChargeHistoryEntry)} == {
        "query_id",
        "query_type",
        "epsilon_charged",
        "epsilon_remaining",
        "timestamp",
    }


@pytest.mark.parametrize(
    "epsilon_total", [0.0, -1.0, float("nan"), float("inf"), float("-inf"), True, "1.0"]
)
def test_invalid_session_total_is_rejected(epsilon_total: object) -> None:
    with pytest.raises(InvalidEpsilonError):
        session(epsilon_total=epsilon_total)


def test_store_creates_uuid_backed_session_and_rejects_unknown_ids() -> None:
    store = PrivacySessionStore()

    created = store.create(
        dataset_id="synthetic-workforce", epsilon_total=1.0, strict_mode=False
    )

    assert created.session_id
    assert store.get(created.session_id) is created
    with pytest.raises(UnknownSessionError):
        store.get("missing")
