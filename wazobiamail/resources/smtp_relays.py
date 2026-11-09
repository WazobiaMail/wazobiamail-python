"""Customer SMTP relay configuration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ..models import ApiResponse, SmtpRelay, normalize
from .base import Resource, parse_items, parse_one


class SmtpRelaysResource(Resource):
    """Manage outbound SMTP relays for the authenticated account.

    The relay request DTO intentionally accepts snake_case wire fields
    (``smtp_host``, ``smtp_password``, ...); the SDK hides that detail.
    """

    def list(self, *, timeout: Optional[float] = None) -> ApiResponse[List[SmtpRelay]]:
        return self._request(
            "GET",
            "/smtp-relays",
            timeout=timeout,
            parser=parse_items(SmtpRelay, "smtpRelays"),
        )

    def get(
        self, relay_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Optional[SmtpRelay]]:
        return self._request(
            "GET",
            f"/smtp-relays/{quote(str(relay_id), safe='')}",
            timeout=timeout,
            parser=parse_one(SmtpRelay, "smtpRelay"),
        )

    def create(
        self,
        name: str,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        tls_mode: Optional[str] = None,
        smtp_security: str = "starttls",
        status: Optional[str] = None,
        is_default: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Optional[SmtpRelay]]:
        resolved_host = host or smtp_host or ""
        resolved_port = port if port is not None else (smtp_port or 587)
        resolved_username = username or smtp_username or ""
        resolved_password = password or smtp_password or ""
        resolved_security = tls_mode or smtp_security
        body: Dict[str, Any] = {
            "name": name,
            "smtp_host": resolved_host,
            "smtp_port": resolved_port,
            "smtp_username": resolved_username,
            "smtp_password": resolved_password,
            "smtp_security": resolved_security,
        }
        if status is not None:
            body["status"] = status
        if is_default is not None:
            body["is_default"] = is_default
        return self._request(
            "POST",
            "/smtp-relays",
            json_body=body,
            timeout=timeout,
            parser=parse_one(SmtpRelay, "smtpRelay"),
        )


    def update(
        self,
        relay_id: str,
        *,
        name: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_security: Optional[str] = None,
        status: Optional[str] = None,
        is_default: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Optional[SmtpRelay]]:
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if smtp_host is not None:
            body["smtp_host"] = smtp_host
        if smtp_port is not None:
            body["smtp_port"] = smtp_port
        if smtp_username is not None:
            body["smtp_username"] = smtp_username
        if smtp_password is not None:
            body["smtp_password"] = smtp_password
        if smtp_security is not None:
            body["smtp_security"] = smtp_security
        if status is not None:
            body["status"] = status
        if is_default is not None:
            body["is_default"] = is_default
        return self._request(
            "PATCH",
            f"/smtp-relays/{quote(str(relay_id), safe='')}",
            json_body=body,
            timeout=timeout,
            parser=parse_one(SmtpRelay, "smtpRelay"),
        )

    def delete(
        self, relay_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "DELETE",
            f"/smtp-relays/{quote(str(relay_id), safe='')}",
            send_json=False,
            timeout=timeout,
        )

    def activate(
        self, relay_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Optional[SmtpRelay]]:
        return self._request(
            "POST",
            f"/smtp-relays/{quote(str(relay_id), safe='')}/activate",
            timeout=timeout,
            parser=parse_one(SmtpRelay, "smtpRelay"),
        )

    def deactivate(
        self, relay_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Optional[SmtpRelay]]:
        return self._request(
            "POST",
            f"/smtp-relays/{quote(str(relay_id), safe='')}/deactivate",
            timeout=timeout,
            parser=parse_one(SmtpRelay, "smtpRelay"),
        )


__all__ = ["SmtpRelaysResource"]
