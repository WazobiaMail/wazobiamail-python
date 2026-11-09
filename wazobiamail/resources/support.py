"""Customer support tickets."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union
from urllib.parse import quote

from ..models import (
    Account,
    ApiResponse,
    SupportTicket,
    SupportTicketCreated,
    SupportTicketPage,
)
from .base import Resource


SupportAttachmentInput = Union[
    Mapping[str, Any],
    Tuple[str, Union[str, bytes, bytearray]],
    str,
    os.PathLike,
]


def _ticket_id(value: str) -> str:
    return quote(str(value), safe="")


def _b64(value: Union[str, bytes, bytearray]) -> str:
    if isinstance(value, str):
        return value
    return base64.b64encode(bytes(value)).decode("ascii")


def _upload(item: SupportAttachmentInput) -> Dict[str, str]:
    if isinstance(item, Mapping):
        filename = item.get("filename") or item.get("fileName") or item.get("name")
        data = item.get("data")
        if data is None:
            content = item.get("content")
            data = content
        if not filename or data is None:
            raise ValueError(
                "Support attachments require 'filename' and 'data' (base64 or bytes)"
            )
        return {"filename": str(filename), "data": _b64(data)}

    if isinstance(item, tuple) and len(item) == 2:
        filename, data = item
        return {"filename": str(filename), "data": _b64(data)}

    if isinstance(item, (str, os.PathLike)):
        path = Path(item)
        if not path.is_file():
            raise FileNotFoundError(f"Support attachment does not exist: {path}")
        return {
            "filename": path.name,
            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
        }

    raise ValueError(
        "Support attachments must be mappings, (filename, data) tuples, or file paths"
    )


def _uploads(
    attachments: Optional[Iterable[SupportAttachmentInput]],
) -> List[Dict[str, str]]:
    return [_upload(item) for item in (attachments or [])]


class SupportResource(Resource):
    """Open tickets, read conversations and reply."""

    def _identity(self) -> Account:
        """Resolve the authenticated account for ticket identity fields."""

        result = self._http.get("/auth/me")
        account = Account.from_dict(result.data or {})
        if not account.email:
            raise ValueError(
                "A support ticket needs name and email. Pass them explicitly for "
                "unauthenticated ticket creation."
            )
        return account

    def create(
        self,
        subject: str,
        message: str,
        *,
        category: str = "general",
        priority: str = "normal",
        name: Optional[str] = None,
        email: Optional[str] = None,
        domain: Optional[str] = None,
        content_type: Optional[str] = None,
        attachments: Optional[Iterable[SupportAttachmentInput]] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[SupportTicketCreated]:
        """Create a support ticket.

        Authenticated calls fill a missing ``name``/``email`` from
        ``GET /auth/me``; provide them explicitly for unauthenticated ticket
        creation (the public endpoint does not require credentials).
        """

        if name is None or email is None:
            account = self._identity()
            if name is None:
                name = account.name or account.username or account.email
            if email is None:
                email = account.email
        if not name or not email:
            raise ValueError(
                "A support ticket needs a name and email. Pass them explicitly for "
                "unauthenticated ticket creation."
            )

        body: Dict[str, Any] = {
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
            "category": category,
            "priority": priority,
        }
        if domain is not None:
            body["domain"] = domain
        if content_type is not None:
            body["contentType"] = content_type
        uploads = _uploads(attachments)
        if uploads:
            body["attachments"] = uploads

        return self._request(
            "POST",
            "/support",
            json_body=body,
            timeout=timeout,
            parser=lambda data: SupportTicketCreated.from_dict(data),
        )

    create_ticket = create


    def list(
        self,
        *,
        status: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[SupportTicketPage]:
        """List the authenticated account's support tickets."""

        return self._request(
            "GET",
            "/support/my",
            params={"status": status, "page": page, "limit": limit},
            timeout=timeout,
            parser=lambda data: SupportTicketPage.from_dict(data),
        )

    def get(
        self, ticket_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[SupportTicket]:
        """Read one support ticket and its message history."""

        return self._request(
            "GET",
            f"/support/tickets/{_ticket_id(ticket_id)}",
            timeout=timeout,
            parser=lambda data: SupportTicket.from_dict(data),
        )

    def reply(
        self,
        ticket_id: str,
        message: str,
        *,
        content_type: Optional[str] = None,
        attachments: Optional[Iterable[SupportAttachmentInput]] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Dict[str, Any]]:
        """Append a customer message to a ticket."""

        body: Dict[str, Any] = {"message": message}
        if content_type is not None:
            body["contentType"] = content_type
        uploads = _uploads(attachments)
        if uploads:
            body["attachments"] = uploads

        return self._request(
            "POST",
            f"/support/tickets/{_ticket_id(ticket_id)}/messages",
            json_body=body,
            timeout=timeout,
        )

    def mark_read(
        self, ticket_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Dict[str, Any]]:
        """Mark the authenticated customer's side of a conversation as read."""

        return self._request(
            "POST",
            f"/support/tickets/{_ticket_id(ticket_id)}/read",
            timeout=timeout,
        )


__all__ = ["SupportResource", "SupportAttachmentInput"]
