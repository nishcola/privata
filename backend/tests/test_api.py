import asyncio
from importlib import import_module

import httpx
import pytest

from app.main import create_app


def test_main_module_exposes_application_factory() -> None:
    main = import_module("app.main")

    assert callable(main.create_app)
    assert main.app is not None


def test_health_returns_typed_ok_response() -> None:
    async def get_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.get("/health")

    response = asyncio.run(get_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_the_only_application_route() -> None:
    application_paths = set(create_app().openapi()["paths"])

    assert application_paths == {"/health"}


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
