import asyncio
from importlib import import_module

import httpx
import pytest

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


def get(path: str) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.get(path)

    return asyncio.run(request())


def test_main_module_exposes_application_factory() -> None:
    main = import_module("app.main")

    assert callable(main.create_app)
    assert main.app is not None


def test_health_returns_typed_ok_response() -> None:
    response = get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_phase_two_exposes_only_health_and_public_dataset_routes() -> None:
    application_paths = set(create_app().openapi()["paths"])

    assert application_paths == {
        "/health",
        "/datasets",
        "/datasets/{dataset_id}/schema",
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
