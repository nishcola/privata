import asyncio
from importlib import import_module

import httpx
import pytest
from fastapi import FastAPI

from app.main import create_app

EXPECTED_SCHEMA = {
    "fields": [
        {
            "name": "age",
            "field_type": "numeric",
            "value_type": "integer",
            "lower_bound": 18.0,
            "upper_bound": 80.0,
            "histogram_bins": None,
        },
        {
            "name": "annual_income",
            "field_type": "numeric",
            "value_type": "integer",
            "lower_bound": 20_000.0,
            "upper_bound": 200_000.0,
            "histogram_bins": {
                "edges": [
                    20_000.0,
                    50_000.0,
                    80_000.0,
                    110_000.0,
                    140_000.0,
                    170_000.0,
                    200_000.0,
                ]
            },
        },
        {
            "name": "department",
            "field_type": "categorical",
            "categories": [
                "Engineering",
                "Sales",
                "Operations",
                "Finance",
                "People",
            ],
        },
    ]
}


def request(
    method: str,
    path: str,
    *,
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    application: FastAPI | None = None,
) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=application or create_app())
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.request(method, path, json=payload, headers=headers)

    return asyncio.run(request())


def get(path: str, *, application: FastAPI | None = None) -> httpx.Response:
    return request("GET", path, application=application)


def test_vite_development_origin_can_preflight_api_requests() -> None:
    response = request(
        "OPTIONS",
        "/sessions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]


def post(
    path: str, payload: dict[str, object], *, application: FastAPI | None = None
) -> httpx.Response:
    return request("POST", path, payload=payload, application=application)


def test_main_module_exposes_application_factory() -> None:
    main = import_module("app.main")

    assert callable(main.create_app)
    assert main.app is not None


def test_health_returns_typed_ok_response() -> None:
    response = get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_phase_six_exposes_only_authorized_routes() -> None:
    application_paths = set(create_app().openapi()["paths"])

    assert application_paths == {
        "/health",
        "/datasets",
        "/datasets/{dataset_id}/schema",
        "/sessions",
        "/sessions/{session_id}",
        "/sessions/{session_id}/queries",
        "/sessions/{session_id}/history",
    }


def test_list_datasets_returns_public_metadata_without_records() -> None:
    response = get("/datasets")

    assert response.status_code == 200
    assert response.json() == [
        {
            "dataset_id": "synthetic-workforce",
            "name": "Synthetic Workforce",
            "row_count": 500,
            "safe_for_demo": True,
            "schema": EXPECTED_SCHEMA,
        }
    ]
    assert '"records"' not in response.text


def test_get_dataset_schema_returns_only_public_schema() -> None:
    response = get("/datasets/synthetic-workforce/schema")

    assert response.status_code == 200
    assert response.json() == EXPECTED_SCHEMA
    assert '"records"' not in response.text


def test_unknown_dataset_returns_structured_not_found_error() -> None:
    response = get("/datasets/missing/schema")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "UNKNOWN_DATASET",
            "message": "Dataset was not found.",
            "details": {"dataset_id": "missing"},
        }
    }


def create_session(
    application: FastAPI, *, epsilon_total: float, strict_mode: bool
) -> dict[str, object]:
    response = post(
        "/sessions",
        {
            "dataset_id": "synthetic-workforce",
            "epsilon_total": epsilon_total,
            "strict_mode": strict_mode,
        },
        application=application,
    )

    assert response.status_code == 200
    return response.json()


def test_create_and_get_session_return_public_accounting_state() -> None:
    application = create_app()
    created = create_session(application, epsilon_total=1.5, strict_mode=True)

    response = get(f"/sessions/{created['session_id']}", application=application)

    assert created == response.json() == {
        "session_id": created["session_id"],
        "dataset_id": "synthetic-workforce",
        "epsilon_total": 1.5,
        "epsilon_spent": 0.0,
        "epsilon_remaining": 1.5,
        "strict_mode": True,
    }


@pytest.mark.parametrize(
    "payload",
    (
        {
            "query_type": "COUNT_CATEGORY",
            "field": "department",
            "category": "Engineering",
            "epsilon": 0.5,
        },
        {"query_type": "MEAN", "field": "age", "epsilon": 0.5},
        {"query_type": "HISTOGRAM", "field": "department", "epsilon": 0.5},
    ),
)
def test_strict_query_responses_expose_all_release_metadata_without_truth(
    payload: dict[str, object],
) -> None:
    application = create_app()
    session = create_session(application, epsilon_total=1.0, strict_mode=True)

    response = post(
        f"/sessions/{session['session_id']}/queries", payload, application=application
    )

    assert response.status_code == 200
    body = response.json()
    assert {
        "query_id",
        "query_type",
        "dataset_id",
        "epsilon_charged",
        "epsilon_remaining",
        "sensitivity",
        "mechanism_name",
        "mechanism_scale",
        "timestamp",
        "noisy_result",
    } <= set(body)
    assert "true_result" not in body
    assert "true_result_is_demo" not in body

    history = get(f"/sessions/{session['session_id']}/history", application=application)
    assert history.status_code == 200
    assert "true_result" not in history.text


def test_safe_demo_session_labels_true_result_as_demo() -> None:
    application = create_app()
    session = create_session(application, epsilon_total=1.0, strict_mode=False)

    response = post(
        f"/sessions/{session['session_id']}/queries",
        {
            "query_type": "COUNT_CATEGORY",
            "field": "department",
            "category": "Engineering",
            "epsilon": 0.5,
        },
        application=application,
    )

    assert response.status_code == 200
    assert response.json()["true_result_is_demo"] is True
    assert "true_result" in response.json()


def test_invalid_and_over_budget_queries_do_not_charge_via_http() -> None:
    application = create_app()
    session = create_session(application, epsilon_total=0.5, strict_mode=True)
    session_id = session["session_id"]

    invalid = post(
        f"/sessions/{session_id}/queries",
        {"query_type": "MEAN", "field": "department", "epsilon": 0.25},
        application=application,
    )
    over_budget = post(
        f"/sessions/{session_id}/queries",
        {"query_type": "MEAN", "field": "age", "epsilon": 0.75},
        application=application,
    )
    current = get(f"/sessions/{session_id}", application=application)

    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "INVALID_QUERY"
    assert over_budget.status_code == 409
    assert over_budget.json()["error"]["code"] == "BUDGET_EXCEEDED"
    assert current.json()["epsilon_spent"] == 0.0
    assert get(f"/sessions/{session_id}/history", application=application).json() == []


def test_malformed_query_body_does_not_charge_via_http() -> None:
    application = create_app()
    session = create_session(application, epsilon_total=0.5, strict_mode=True)
    session_id = session["session_id"]

    response = post(
        f"/sessions/{session_id}/queries",
        {"query_type": "MEAN", "field": "age", "epsilon": 0.0},
        application=application,
    )

    assert response.status_code == 422
    assert get(f"/sessions/{session_id}", application=application).json()[
        "epsilon_spent"
    ] == 0.0
    assert get(f"/sessions/{session_id}/history", application=application).json() == []


@pytest.mark.parametrize(
    "path",
    (
        "/sessions/missing",
        "/sessions/missing/history",
    ),
)
def test_unknown_session_returns_structured_not_found_error(path: str) -> None:
    response = get(path)

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "UNKNOWN_SESSION",
            "message": "Session was not found.",
            "details": {"session_id": "missing"},
        }
    }


def test_unknown_dataset_is_rejected_when_creating_session() -> None:
    response = post(
        "/sessions",
        {"dataset_id": "missing", "epsilon_total": 1.0, "strict_mode": True},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "UNKNOWN_DATASET"


@pytest.mark.parametrize(
    "module_name",
    [
        "app.api",
        "app.api.health",
        "app.datasets",
        "app.datasets.models",
        "app.dp",
        "app.dp.accounting",
        "app.dp.clipping",
        "app.dp.mechanisms",
        "app.dp.models",
        "app.dp.queries",
        "app.dp.queries.models",
        "app.dp.sensitivity",
        "app.errors",
        "app.main",
        "app.services",
    ],
)
def test_backend_modules_import_cleanly(module_name: str) -> None:
    assert import_module(module_name) is not None
