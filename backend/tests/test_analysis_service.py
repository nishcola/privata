"""Behavioral tests for Phase 6 analysis orchestration."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from app.datasets.models import DatasetMetadata
from app.datasets.registry import DatasetRegistry, RegisteredDataset
from app.datasets.synthetic import create_builtin_registry
from app.dp.accounting import PrivacySession, PrivacySessionStore
from app.dp.queries.models import (
    CountCategoryRequest,
    HistogramRequest,
    MeanRequest,
)
from app.errors import (
    BudgetExceededError,
    InvalidQueryError,
    UnknownDatasetError,
    UnknownSessionError,
)
from app.services.analysis import AnalysisService


def zero_noise_sampler() -> float:
    return 0.5


def service(
    *,
    registry: DatasetRegistry | None = None,
    sampler: Callable[[], float] = zero_noise_sampler,
) -> AnalysisService:
    return AnalysisService(
        dataset_registry=registry or create_builtin_registry(),
        session_store=PrivacySessionStore(),
        uniform_sampler=sampler,
    )


@pytest.mark.parametrize(
    ("query_request", "sensitivity", "scale"),
    (
        (
            CountCategoryRequest(
                field="department", category="Engineering", epsilon=0.5
            ),
            1.0,
            2.0,
        ),
        (MeanRequest(field="age", epsilon=0.5), 62.0 / 500.0, 0.248),
        (HistogramRequest(field="department", epsilon=0.5), 2.0, 4.0),
    ),
)
def test_strict_service_releases_all_query_types_without_true_results(
    query_request: CountCategoryRequest | MeanRequest | HistogramRequest,
    sensitivity: float,
    scale: float,
) -> None:
    value = service()
    session = value.create_session(
        dataset_id="synthetic-workforce", epsilon_total=2.0, strict_mode=True
    )

    response = value.execute_query(
        session_id=session.session_id, request=query_request
    )

    assert response.query_type is query_request.query_type
    assert response.epsilon_charged == 0.5
    assert response.epsilon_remaining == 1.5
    assert response.sensitivity == pytest.approx(sensitivity)
    assert response.mechanism_scale == pytest.approx(scale)
    assert response.true_result is None
    assert response.true_result_is_demo is None
    assert "true_result" not in response.model_dump(exclude_none=True)


def test_successive_queries_decrease_budget_and_history_is_safe() -> None:
    value = service()
    session = value.create_session(
        dataset_id="synthetic-workforce", epsilon_total=1.0, strict_mode=True
    )

    first = value.execute_query(
        session_id=session.session_id,
        request=MeanRequest(field="age", epsilon=0.25),
    )
    second = value.execute_query(
        session_id=session.session_id,
        request=HistogramRequest(field="department", epsilon=0.5),
    )

    assert (first.epsilon_remaining, second.epsilon_remaining) == (0.75, 0.25)
    history = value.get_history(session_id=session.session_id)
    assert [entry.epsilon_charged for entry in history] == [0.25, 0.5]
    assert all("true_result" not in entry.model_dump() for entry in history)


def test_demo_safe_non_strict_session_marks_ground_truth_as_demo() -> None:
    value = service()
    session = value.create_session(
        dataset_id="synthetic-workforce", epsilon_total=1.0, strict_mode=False
    )

    response = value.execute_query(
        session_id=session.session_id,
        request=CountCategoryRequest(
            field="department", category="Engineering", epsilon=0.5
        ),
    )

    assert response.noisy_result == response.true_result
    assert response.true_result_is_demo is True


def test_non_demo_safe_dataset_never_discloses_ground_truth() -> None:
    source = create_builtin_registry()
    metadata = DatasetMetadata(
        dataset_id="private-workforce",
        name="Private Workforce",
        row_count=500,
        safe_for_demo=False,
        schema=source.get_schema("synthetic-workforce"),
    )
    registry = DatasetRegistry(
        (
            RegisteredDataset(
                metadata=metadata,
                records=source.get_records("synthetic-workforce"),
            ),
        )
    )
    value = service(registry=registry)
    session = value.create_session(
        dataset_id="private-workforce", epsilon_total=1.0, strict_mode=False
    )

    response = value.execute_query(
        session_id=session.session_id,
        request=MeanRequest(field="age", epsilon=0.5),
    )

    assert response.true_result is None
    assert response.true_result_is_demo is None


def test_invalid_and_over_budget_queries_do_not_charge_session() -> None:
    value = service()
    session = value.create_session(
        dataset_id="synthetic-workforce", epsilon_total=0.5, strict_mode=True
    )

    with pytest.raises(InvalidQueryError):
        value.execute_query(
            session_id=session.session_id,
            request=MeanRequest(field="department", epsilon=0.25),
        )
    with pytest.raises(BudgetExceededError):
        value.execute_query(
            session_id=session.session_id,
            request=MeanRequest(field="age", epsilon=0.75),
        )

    assert value.get_session(session_id=session.session_id).epsilon_spent == 0.0
    assert value.get_history(session_id=session.session_id) == ()


def test_mechanism_failure_does_not_charge_session() -> None:
    value = service(sampler=lambda: 1.0)
    session = value.create_session(
        dataset_id="synthetic-workforce", epsilon_total=1.0, strict_mode=True
    )

    with pytest.raises(ValueError, match="uniform sampler result"):
        value.execute_query(
            session_id=session.session_id,
            request=MeanRequest(field="age", epsilon=0.5),
        )

    assert value.get_session(session_id=session.session_id).epsilon_spent == 0.0
    assert value.get_history(session_id=session.session_id) == ()


def test_concurrent_query_cannot_execute_after_another_query_uses_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = service()
    session = value.create_session(
        dataset_id="synthetic-workforce", epsilon_total=0.5, strict_mode=True
    )
    first_preflight = Event()
    second_preflight = Event()
    release_first = Event()
    original_assert = PrivacySession.assert_can_charge
    successful_preflights = 0

    def controlled_assert(value: PrivacySession, epsilon: float) -> None:
        nonlocal successful_preflights
        original_assert(value, epsilon)
        successful_preflights += 1
        if successful_preflights == 1:
            first_preflight.set()
            assert release_first.wait(timeout=1.0)
        elif successful_preflights == 2:
            second_preflight.set()

    monkeypatch.setattr(PrivacySession, "assert_can_charge", controlled_assert)
    query = MeanRequest(field="age", epsilon=0.5)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            value.execute_query, session_id=session.session_id, request=query
        )
        assert first_preflight.wait(timeout=1.0)
        second = executor.submit(
            value.execute_query, session_id=session.session_id, request=query
        )
        try:
            assert not second_preflight.wait(timeout=0.5)
        finally:
            release_first.set()

        first.result(timeout=1.0)
        with pytest.raises(BudgetExceededError):
            second.result(timeout=1.0)


def test_unknown_resources_raise_stable_domain_errors() -> None:
    value = service()

    with pytest.raises(UnknownDatasetError):
        value.create_session(dataset_id="missing", epsilon_total=1.0, strict_mode=True)
    with pytest.raises(UnknownSessionError):
        value.get_session(session_id="missing")
