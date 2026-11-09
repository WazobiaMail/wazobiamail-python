"""Transactional email, attachment, deliverability and tracking operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ..http import FileUpload, prepare_file
from ..models import (
    ApiResponse,
    EmailLogs,
    SendResult,
    SpamCheckResult,
    TrackingDetail,
    TrackingList,
    UploadedFile,
    normalize,
)
from .base import Resource


def _recipient_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _normalize_url_attachments(value: Any) -> List[Dict[str, str]]:
    if value is None:
        return []
    items = value if isinstance(value, (list, tuple)) else [value]
    result: List[Dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            result.append(
                {"url": item, "fileName": Path(item).name or "attachment"}
            )
            continue
        if isinstance(item, Mapping):
            data = normalize(item)
            url = data.get("url")
            if not url:
                raise ValueError("URL attachments require a 'url' value")
            file_name = (
                data.get("file_name")
                or data.get("fileName")
                or data.get("name")
                or Path(str(url)).name
                or "attachment"
            )
            result.append({"url": str(url), "fileName": str(file_name)})
            continue
        raise ValueError("URL attachments must be strings or mappings")
    return result


def _pick(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _build_message(
    message: Optional[Mapping[str, Any]],
    *,
    to: Any = None,
    subject: Optional[str] = None,
    html: Optional[str] = None,
    text: Optional[str] = None,
    html_body: Optional[str] = None,
    text_body: Optional[str] = None,
    sender: Optional[str] = None,
    from_: Optional[str] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
    cc: Any = None,
    bcc: Any = None,
    envelope_sender: Optional[str] = None,
    attachments: Any = None,
) -> Dict[str, Any]:
    if message is not None and not isinstance(message, Mapping):
        raise TypeError("message must be a mapping when supplied positionally")

    base: Mapping[str, Any] = message or {}
    content_value = base.get("content")
    content: Mapping[str, Any] = (
        content_value if isinstance(content_value, Mapping) else {}
    )
    normalized_content = normalize(content)

    resolved_to = to if to is not None else _pick(base, "to", "recipients")
    resolved_cc = cc if cc is not None else _pick(base, "cc")
    resolved_bcc = bcc if bcc is not None else _pick(base, "bcc")

    resolved_subject = subject if subject is not None else _pick(base, "subject")
    if resolved_subject is None:
        resolved_subject = _pick(normalized_content, "subject") or ""

    resolved_html = html if html is not None else html_body
    if resolved_html is None:
        resolved_html = _pick(base, "html", "htmlBody", "html_body") or _pick(
            normalized_content, "html", "html_body", "htmlBody"
        )

    resolved_text = text if text is not None else text_body
    if resolved_text is None:
        resolved_text = _pick(base, "text", "textBody", "text_body") or _pick(
            normalized_content, "text", "text_body", "textBody"
        )

    resolved_sender = (
        from_
        if from_ is not None
        else (from_email if from_email is not None else sender)
    )
    if resolved_sender is None:
        resolved_sender = _pick(
            base, "from", "from_", "from_email", "fromEmail", "sender"
        ) or _pick(normalized_content, "from", "from_email", "fromEmail", "sender")

    resolved_reply_to = reply_to
    if resolved_reply_to is None:
        resolved_reply_to = _pick(base, "replyTo", "reply_to") or _pick(
            normalized_content, "replyTo", "reply_to"
        )

    resolved_envelope = envelope_sender
    if resolved_envelope is None:
        resolved_envelope = _pick(base, "envelopeSender", "envelope_sender")

    resolved_attachments = (
        attachments if attachments is not None else _pick(base, "attachments")
    )

    content_payload: Dict[str, Any] = {"subject": str(resolved_subject)}
    if resolved_sender:
        content_payload["from"] = str(resolved_sender)
    if resolved_text is not None:
        content_payload["textBody"] = str(resolved_text)
    if resolved_html is not None:
        content_payload["htmlBody"] = str(resolved_html)
    if resolved_reply_to:
        content_payload["replyTo"] = str(resolved_reply_to)

    payload: Dict[str, Any] = {
        "to": _recipient_list(resolved_to),
        "cc": _recipient_list(resolved_cc),
        "bcc": _recipient_list(resolved_bcc),
        "content": content_payload,
    }
    if resolved_envelope:
        payload["envelopeSender"] = str(resolved_envelope)
    url_attachments = _normalize_url_attachments(resolved_attachments)
    if url_attachments:
        payload["attachments"] = url_attachments
    return payload


class MessagesResource(Resource):
    """Send transactional email and inspect deliverability or tracking."""

    def send(
        self,
        message: Optional[Mapping[str, Any]] = None,
        *,
        to: Any = None,
        subject: Optional[str] = None,
        html: Optional[str] = None,
        text: Optional[str] = None,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        sender: Optional[str] = None,
        from_: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Any = None,
        bcc: Any = None,
        envelope_sender: Optional[str] = None,
        attachments: Any = None,
        idempotency_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[SendResult]:
        """Send a message and return its queued/tracking receipt."""

        payload = _build_message(
            message,
            to=to,
            subject=subject,
            html=html,
            text=text,
            html_body=html_body,
            text_body=text_body,
            sender=sender,
            from_=from_,
            from_email=from_email,
            reply_to=reply_to,
            cc=cc,
            bcc=bcc,
            envelope_sender=envelope_sender,
            attachments=attachments,
        )
        return self._request(
            "POST",
            "/sending/messages",
            json_body=payload,
            idempotency_key=idempotency_key,
            timeout=timeout,
            parser=lambda data: SendResult.from_dict(normalize(data).get("result") or {}),
        )

    def send_with_attachments(
        self,
        message: Optional[Mapping[str, Any]] = None,
        files: Optional[Iterable[Any]] = None,
        *,
        attachments: Optional[Iterable[Any]] = None,
        to: Any = None,
        subject: Optional[str] = None,
        html: Optional[str] = None,
        text: Optional[str] = None,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        sender: Optional[str] = None,
        from_: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Any = None,
        bcc: Any = None,
        envelope_sender: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[SendResult]:
        """Send a message with direct binary attachments (multipart).

        The server accepts at most 5 MiB in total across all attached files.
        """

        source_files = files if files is not None else attachments
        if not source_files:
            raise ValueError("At least one attachment is required")

        payload = _build_message(
            message,
            to=to,
            subject=subject,
            html=html,
            text=text,
            html_body=html_body,
            text_body=text_body,
            sender=sender,
            from_=from_,
            from_email=from_email,
            reply_to=reply_to,
            cc=cc,
            bcc=bcc,
            envelope_sender=envelope_sender,
        )

        uploads = []
        for item in source_files:
            if isinstance(item, FileUpload):
                uploads.append(item)
            else:
                uploads.append(prepare_file(item))

        return self._request(
            "POST",
            "/sending/messages/with-attachments",
            multipart=(
                [("message", json.dumps(payload, separators=(",", ":")))],
                [("files", upload, "files") for upload in uploads],
            ),
            idempotency_key=idempotency_key,
            timeout=timeout,
            parser=lambda data: SendResult.from_dict(normalize(data).get("result") or {}),
        )

    def upload_attachment(
        self,
        file: Any,
        *,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[UploadedFile]:
        """Upload a file and receive a reusable public URL."""

        upload = (
            file
            if isinstance(file, FileUpload)
            else prepare_file(file, file_name=file_name, content_type=content_type)
        )
        if file_name:
            upload = FileUpload(
                file_name=file_name,
                content=upload.content,
                content_type=content_type or upload.content_type,
            )
        return self._request(
            "POST",
            "/sending/attachments/upload",
            multipart=([], [("file", upload, "file")]),
            timeout=timeout,
            parser=lambda data: UploadedFile.from_dict(
                normalize(data).get("file") or {}
            ),
        )

    def spam_check(
        self,
        message: Optional[Mapping[str, Any]] = None,
        *,
        subject: Optional[str] = None,
        html: Optional[str] = None,
        text: Optional[str] = None,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        sender: Optional[str] = None,
        from_: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[SpamCheckResult]:
        """Run the server-side spam and deliverability analysis.

        This endpoint requires a Business or Enterprise subscription (admins are
        also allowed).
        """

        base: Mapping[str, Any] = message or {}
        if message is not None and not isinstance(message, Mapping):
            raise TypeError("message must be a mapping when supplied positionally")
        normalized_base = normalize(base)

        resolved_subject = (
            subject
            if subject is not None
            else _pick(base, "subject")
            if _pick(base, "subject") is not None
            else ""
        )
        resolved_html = (
            html
            if html is not None
            else (
                html_body
                if html_body is not None
                else _pick(base, "html", "htmlBody", "html_body")
            )
        )
        resolved_text = (
            text
            if text is not None
            else (
                text_body
                if text_body is not None
                else _pick(base, "text", "textBody", "text_body")
            )
        )
        resolved_sender = (
            from_
            if from_ is not None
            else (from_email if from_email is not None else sender)
        )
        if resolved_sender is None:
            resolved_sender = _pick(
                base, "from", "from_", "from_email", "fromEmail", "sender"
            )
        resolved_reply = reply_to
        if resolved_reply is None:
            resolved_reply = _pick(normalized_base, "reply_to", "replyTo")
        resolved_headers = headers if headers is not None else _pick(base, "headers")

        payload: Dict[str, Any] = {"subject": str(resolved_subject)}
        if resolved_html is not None:
            payload["html"] = str(resolved_html)
        if resolved_text is not None:
            payload["text"] = str(resolved_text)
        if resolved_sender:
            payload["from"] = str(resolved_sender)
        if resolved_reply:
            payload["replyTo"] = str(resolved_reply)
        if resolved_headers:
            payload["headers"] = dict(resolved_headers)

        return self._request(
            "POST",
            "/sending/spam-check",
            json_body=payload,
            timeout=timeout,
            parser=lambda data: SpamCheckResult.from_dict(data),
        )

    def list_tracking(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[TrackingList]:
        """List tracked messages with open/click counters (paid plans)."""

        return self._request(
            "GET",
            "/sending/tracking/messages",
            params={
                "limit": limit,
                "offset": offset,
                "status": status,
                "from": from_date,
                "to": to_date,
            },
            timeout=timeout,
            parser=lambda data: TrackingList.from_dict(data),
        )

    def get_tracking(
        self, tracking_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[TrackingDetail]:
        """Read the delivery-event timeline for one tracked message."""

        from urllib.parse import quote

        return self._request(
            "GET",
            f"/sending/tracking/messages/{quote(str(tracking_id), safe='')}",
            timeout=timeout,
            parser=lambda data: TrackingDetail.from_dict(
                normalize(data).get("message") or {}
            ),
        )

    list_tracked = list_tracking
    get_tracked = get_tracking

    def list_logs(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[EmailLogs]:
        """List customer-visible email delivery logs (paid plans)."""

        return self._request(
            "GET",
            "/account/email-logs",
            params={
                "limit": limit,
                "offset": offset,
                "status": status,
                "from": from_date,
                "to": to_date,
            },
            timeout=timeout,
            parser=lambda data: EmailLogs.from_dict(data),
        )


__all__ = ["MessagesResource"]
