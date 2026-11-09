"""Authentication resource."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..models import Account, ApiResponse, AuthPayload
from .base import Resource, parse_direct


class AuthResource(Resource):
    """Account sign-in and identity endpoints.

    Bearer tokens obtained here can be supplied to ``WazobiaMail(access_token=...)``.
    """

    def login(
        self,
        email: str,
        password: str,
        *,
        totp_code: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[AuthPayload]:
        body: Dict[str, Any] = {"email": email, "password": password}
        if totp_code:
            body["totpCode"] = totp_code
        return self._request(
            "POST",
            "/auth/login",
            json_body=body,
            parser=parse_direct(AuthPayload),
            timeout=timeout,
        )

    def register(
        self,
        email: str,
        password: str,
        *,
        username: Optional[str] = None,
        plan_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Dict[str, Any]]:
        body: Dict[str, Any] = {"email": email, "password": password}
        if username is not None:
            body["username"] = username
        if plan_id is not None:
            body["planId"] = plan_id
        return self._request(
            "POST", "/auth/register", json_body=body, timeout=timeout
        )

    def refresh(
        self, refresh_token: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[AuthPayload]:
        return self._request(
            "POST",
            "/auth/refresh",
            json_body={"refreshToken": refresh_token},
            parser=parse_direct(AuthPayload),
            timeout=timeout,
        )

    def me(self, *, timeout: Optional[float] = None) -> ApiResponse[Account]:
        return self._request(
            "GET", "/auth/me", parser=parse_direct(Account), timeout=timeout
        )


__all__ = ["AuthResource"]
