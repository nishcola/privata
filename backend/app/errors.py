"""Framework-neutral domain error vocabulary."""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Stable public codes for domain failures."""

    INVALID_QUERY = "INVALID_QUERY"
    INVALID_EPSILON = "INVALID_EPSILON"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    UNKNOWN_DATASET = "UNKNOWN_DATASET"
    UNKNOWN_SESSION = "UNKNOWN_SESSION"
    PRIVACY_MODEL_CONFIGURATION_ERROR = "PRIVACY_MODEL_CONFIGURATION_ERROR"


class DomainError(Exception):
    """Base class for expected domain failures."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})


class InvalidQueryError(DomainError):
    """Raised when a query is invalid for public configuration."""

    def __init__(
        self,
        message: str = "Query is invalid.",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(ErrorCode.INVALID_QUERY, message, details)


class InvalidEpsilonError(DomainError):
    """Raised when an epsilon value is invalid."""

    def __init__(
        self,
        message: str = "Epsilon is invalid.",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(ErrorCode.INVALID_EPSILON, message, details)


class BudgetExceededError(DomainError):
    """Raised when a query requests more than the remaining budget."""

    def __init__(self, requested_epsilon: float, remaining_epsilon: float) -> None:
        super().__init__(
            ErrorCode.BUDGET_EXCEEDED,
            "Requested epsilon exceeds the remaining privacy budget.",
            {
                "requested_epsilon": requested_epsilon,
                "remaining_epsilon": remaining_epsilon,
            },
        )


class UnknownDatasetError(DomainError):
    """Raised when a dataset identifier is not registered."""

    def __init__(self, dataset_id: str) -> None:
        super().__init__(
            ErrorCode.UNKNOWN_DATASET,
            "Dataset was not found.",
            {"dataset_id": dataset_id},
        )


class UnknownSessionError(DomainError):
    """Raised when a session identifier is not registered."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            ErrorCode.UNKNOWN_SESSION,
            "Session was not found.",
            {"session_id": session_id},
        )


class PrivacyModelConfigurationError(DomainError):
    """Raised when public privacy-model configuration is inconsistent."""

    def __init__(
        self,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            ErrorCode.PRIVACY_MODEL_CONFIGURATION_ERROR,
            message,
            details,
        )
