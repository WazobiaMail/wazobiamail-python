"""Account SMTP submission access."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..models import ApiResponse, SmtpAccess
from .base import Resource


class SmtpAccessResource(Resource):
    """Read SMTP entitlement and enable/disable client sending."""

    def get(self, *, timeout: Optional[float] = None) -> ApiResponse[SmtpAccess]:
        return self._request(
            "GET",
            "/sending/smtp-access",
            timeout=timeout,
            parser=lambda data: SmtpAccess.from_dict(data),
        )

    def update(
        self, enabled: bool, *, timeout: Optional[float] = None
    ) -> ApiResponse[Dict[str, Any]]:
        """Save the SMTP preference.

        The API acknowledges the preference with ``{"enabled": bool}``; call
        :meth:`get` afterwards for the full entitlement snapshot.
        """

        return self._request(
            "PUT",
            "/sending/smtp-access",
            json_body={"enabled": bool(enabled)},
            timeout=timeout,
        )


__all__ = ["SmtpAccessResource"]
