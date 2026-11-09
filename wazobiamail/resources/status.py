"""Account status and health."""

from __future__ import annotations

from typing import Optional

from ..models import AccountStatus, ApiResponse
from .base import Resource


class StatusResource(Resource):
    """Read the current plan and remaining unit allowance."""

    def get(self, *, timeout: Optional[float] = None) -> ApiResponse[AccountStatus]:
        return self._request(
            "GET",
            "/status",
            timeout=timeout,
            parser=lambda data: AccountStatus.from_dict(data),
        )


__all__ = ["StatusResource"]
