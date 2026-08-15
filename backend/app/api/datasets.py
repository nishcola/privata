"""HTTP routes for public dataset discovery."""

from fastapi import APIRouter, Request

from app.api.errors import ErrorResponse
from app.datasets.models import DatasetMetadata, DatasetSchema
from app.datasets.registry import DatasetRegistry

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _registry(request: Request) -> DatasetRegistry:
    return request.app.state.dataset_registry


@router.get("", response_model=list[DatasetMetadata])
def list_datasets(request: Request) -> tuple[DatasetMetadata, ...]:
    """List public metadata for registered datasets."""
    return _registry(request).list_metadata()


@router.get(
    "/{dataset_id}/schema",
    response_model=DatasetSchema,
    responses={404: {"model": ErrorResponse}},
)
def get_dataset_schema(dataset_id: str, request: Request) -> DatasetSchema:
    """Return one dataset's public schema."""
    return _registry(request).get_schema(dataset_id)
