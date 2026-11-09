"""Hosted mailboxes, credentials and enterprise inbox messages."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import quote

from ..models import (
    ApiResponse,
    CreatedMailbox,
    CreatedMailboxCredential,
    Mailbox,
    MailboxConnection,
    MailboxMessageDetail,
    MailboxMessagesPage,
    MailboxStorage,
    normalize,
)
from .base import Resource, parse_bare_list, parse_one


def _mailbox_id(value: str) -> str:
    return quote(str(value), safe="")


class MailboxMessagesResource(Resource):
    """Enterprise-plan mailbox inbox endpoints.

    All three operations require an active Enterprise subscription; other plans
    receive HTTP 403 (``WazobiaForbiddenError``).
    """

    def list(
        self,
        mailbox_id: str,
        *,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        unread_only: Optional[bool] = None,
        search: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[MailboxMessagesPage]:
        return self._request(
            "GET",
            f"/mailboxes/{_mailbox_id(mailbox_id)}/messages",
            params={
                "page": page,
                "limit": limit,
                "unreadOnly": unread_only,
                "search": search,
            },
            timeout=timeout,
            parser=lambda data: MailboxMessagesPage.from_dict(data),
        )

    def get(
        self,
        mailbox_id: str,
        message_id: str,
        *,
        timeout: Optional[float] = None,
    ) -> ApiResponse[MailboxMessageDetail]:
        return self._request(
            "GET",
            f"/mailboxes/{_mailbox_id(mailbox_id)}/messages/{_mailbox_id(message_id)}",
            timeout=timeout,
            parser=lambda data: MailboxMessageDetail.from_dict(data),
        )

    def delete(
        self,
        mailbox_id: str,
        message_id: str,
        *,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "DELETE",
            f"/mailboxes/{_mailbox_id(mailbox_id)}/messages/{_mailbox_id(message_id)}",
            send_json=False,
            timeout=timeout,
        )


class MailboxesResource(Resource):
    """Provision and manage hosted mailboxes."""

    def __init__(self, http: Any) -> None:
        super().__init__(http)
        self.messages = MailboxMessagesResource(http)

    def list(
        self, *, timeout: Optional[float] = None
    ) -> ApiResponse[List[Mailbox]]:
        return self._request(
            "GET",
            "/mailboxes",
            timeout=timeout,
            parser=parse_bare_list(Mailbox),
        )

    def get(
        self, mailbox_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Optional[Mailbox]]:
        return self._request(
            "GET",
            f"/mailboxes/{_mailbox_id(mailbox_id)}",
            timeout=timeout,
            parser=parse_one(Mailbox, "mailbox"),
        )

    def create(
        self,
        domain_id: str,
        local_part: str,
        *,
        display_name: Optional[str] = None,
        quota_mb: Optional[int] = None,
        password: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[CreatedMailbox]:
        body: Dict[str, Any] = {
            "domainId": domain_id,
            "localPart": local_part,
        }
        if display_name is not None:
            body["displayName"] = display_name
        if quota_mb is not None:
            body["quotaMb"] = quota_mb
        if password is not None:
            body["password"] = password
        if role is not None:
            body["role"] = role
        if status is not None:
            body["status"] = status

        return self._request(
            "POST",
            "/mailboxes",
            json_body=body,
            timeout=timeout,
            parser=lambda data: CreatedMailbox.from_dict(data),
        )

    def update(
        self,
        mailbox_id: str,
        *,
        display_name: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Optional[Mailbox]]:
        body: Dict[str, Any] = {}
        if display_name is not None:
            body["displayName"] = display_name
        if password is not None:
            body["password"] = password
        return self._request(
            "PATCH",
            f"/mailboxes/{_mailbox_id(mailbox_id)}",
            json_body=body,
            timeout=timeout,
            parser=parse_one(Mailbox, "mailbox"),
        )

    def delete(
        self, mailbox_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "DELETE",
            f"/mailboxes/{_mailbox_id(mailbox_id)}",
            send_json=False,
            timeout=timeout,
        )

    def activate(
        self, mailbox_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Optional[Mailbox]]:
        return self._request(
            "POST",
            f"/mailboxes/{_mailbox_id(mailbox_id)}/activate",
            timeout=timeout,
            parser=parse_one(Mailbox, "mailbox"),
        )

    def suspend(
        self, mailbox_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Optional[Mailbox]]:
        return self._request(
            "POST",
            f"/mailboxes/{_mailbox_id(mailbox_id)}/suspend",
            timeout=timeout,
            parser=parse_one(Mailbox, "mailbox"),
        )

    def storage(
        self, *, timeout: Optional[float] = None
    ) -> ApiResponse[MailboxStorage]:
        return self._request(
            "GET",
            "/mailboxes/storage",
            timeout=timeout,
            parser=lambda data: MailboxStorage.from_dict(data),
        )

    def connection(
        self, mailbox_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[MailboxConnection]:
        return self._request(
            "GET",
            f"/mailboxes/{_mailbox_id(mailbox_id)}/connection",
            timeout=timeout,
            parser=lambda data: MailboxConnection.from_dict(data),
        )

    def password(
        self, mailbox_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[str]:
        return self._request(
            "GET",
            f"/mailboxes/{_mailbox_id(mailbox_id)}/password",
            timeout=timeout,
            parser=lambda data: str(normalize(data).get("password") or ""),
        )

    def create_credentials(
        self,
        mailbox_id: str,
        *,
        expires_at: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[CreatedMailboxCredential]:
        body: Dict[str, Any] = {}
        if expires_at is not None:
            body["expiresAt"] = expires_at
        return self._request(
            "POST",
            f"/mailboxes/{_mailbox_id(mailbox_id)}/credentials",
            json_body=body,
            timeout=timeout,
            parser=lambda data: CreatedMailboxCredential.from_dict(
                normalize(data).get("credential") or {}
            ),
        )

    def rotate_credentials(
        self,
        mailbox_id: str,
        *,
        expires_at: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[CreatedMailboxCredential]:
        body: Dict[str, Any] = {}
        if expires_at is not None:
            body["expiresAt"] = expires_at
        return self._request(
            "POST",
            f"/mailboxes/{_mailbox_id(mailbox_id)}/credentials/rotate",
            json_body=body,
            timeout=timeout,
            parser=lambda data: CreatedMailboxCredential.from_dict(
                normalize(data).get("credential") or {}
            ),
        )

    def revoke_credential(
        self,
        mailbox_id: str,
        credential_id: str,
        *,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "POST",
            (
                f"/mailboxes/{_mailbox_id(mailbox_id)}/credentials/"
                f"{_mailbox_id(credential_id)}/revoke"
            ),
            timeout=timeout,
        )

    def webmail_login(
        self, mailbox_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "POST",
            f"/mailboxes/{_mailbox_id(mailbox_id)}/webmail-login",
            timeout=timeout,
        )

    # Ergonomic aliases
    get_storage = storage
    get_connection_settings = connection



__all__ = ["MailboxesResource", "MailboxMessagesResource"]
