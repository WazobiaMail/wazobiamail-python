"""Exception hierarchy for the WazobiaMail Python SDK."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


class WazobiaError(Exception):
    """Base class for every error raised by the SDK."""

    def __init__(self, message: str, *, cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.message = message
        self.__cause__ = cause


class WazobiaConnectionError(WazobiaError):
    """The API could not be reached (DNS, TLS, socket or proxy failure)."""


class WazobiaTimeoutError(WazobiaError):
    """A request exceeded the configured timeout."""

    def __init__(self, message: str, timeout: float, *, cause: Optional[BaseException] = None) -> None:
        super().__init__(message, cause=cause)
        self.timeout = timeout


class WazobiaApiError(WazobiaError):
    """The API returned a non-2xx response."""

    def __init__(
        self,
        message: str,
        status_code: int,
        *,
        code: Optional[str] = None,
        errors: Optional[Mapping[str, str]] = None,
        raw_body: Any = None,
        request_id: Optional[str] = None,
        response_headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = int(status_code)
        self.code = code
        self.errors: Dict[str, str] = dict(errors or {})
        self.raw_body = raw_body
        self.request_id = request_id
        self.response_headers: Dict[str, str] = dict(response_headers or {})

    def __str__(self) -> str:
        suffix = f" (HTTP {self.status_code})" if self.status_code else ""
        return f"{self.message}{suffix}"


class WazobiaAuthenticationError(WazobiaApiError):
    """Authentication failed (HTTP 401) or credentials are missing/invalid."""

    def __init__(
        self,
        message: str = "Invalid or missing WazobiaMail credentials",
        status_code: int = 401,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code, **kwargs)


class WazobiaForbiddenError(WazobiaApiError):
    """The account or plan is not allowed to perform the action (HTTP 403)."""

    def __init__(
        self,
        message: str = "Access forbidden for this account or plan tier",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, 403, **kwargs)


class WazobiaNotFoundError(WazobiaApiError):
    """The requested resource does not exist (HTTP 404)."""

    def __init__(self, message: str = "The requested resource was not found", **kwargs: Any) -> None:
        super().__init__(message, 404, **kwargs)


class WazobiaConflictError(WazobiaApiError):
    """The request conflicts with the current state (HTTP 409)."""

    def __init__(self, message: str = "This item has changed; refresh and try again", **kwargs: Any) -> None:
        super().__init__(message, 409, **kwargs)


class WazobiaValidationError(WazobiaApiError):
    """The submitted payload failed validation (HTTP 422, or 400 with field errors)."""

    def __init__(
        self,
        message: str = "Validation failed",
        status_code: int = 422,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code, **kwargs)


class WazobiaRateLimitError(WazobiaApiError):
    """The account hit a rate limit (HTTP 429)."""

    def __init__(
        self,
        message: str = "Too many requests; rate limit exceeded",
        *,
        retry_after: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, 429, **kwargs)
        self.retry_after = retry_after


class WazobiaServerError(WazobiaApiError):
    """The API returned a 5xx response."""

    def __init__(self, message: str = "WazobiaMail service error", **kwargs: Any) -> None:
        status = int(kwargs.pop("status_code", 500))
        super().__init__(message, status, **kwargs)


class WazobiaWebhookError(WazobiaError):
    """A webhook payload or signature could not be verified."""


__all__ = [
    "WazobiaError",
    "WazobiaConnectionError",
    "WazobiaTimeoutError",
    "WazobiaApiError",
    "WazobiaAuthenticationError",
    "WazobiaForbiddenError",
    "WazobiaNotFoundError",
    "WazobiaConflictError",
    "WazobiaValidationError",
    "WazobiaRateLimitError",
    "WazobiaServerError",
    "WazobiaWebhookError",
]
