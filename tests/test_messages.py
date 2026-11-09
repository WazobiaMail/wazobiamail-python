"""Transactional email, attachment, deliverability and tracking tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from wazobiamail import FileUpload, WazobiaMail
from wazobiamail.models import SendResult, normalize

try:
    from ._server import MockServerTestCase
except ImportError:  # pragma: no cover
    from _server import MockServerTestCase


def _multipart_parts(body: bytes, content_type: str) -> list[bytes]:
    boundary = content_type.split("boundary=", 1)[1].encode("utf-8")
    return [part for part in body.split(b"--" + boundary) if part.strip() and part.strip() != b"--"]


class TestMessages(MockServerTestCase):
    def test_send_normalizes_payload_and_parses_receipt(self) -> None:
        self.server.enqueue(
            data={
                "result": {
                    "status": "queued",
                    "trackingId": "trk_123456789",
                    "recipients": 2,
                }
            },
            message="Your message is on its way",
        )
        result = self.make_client().messages.send(
            sender="Acme Store <hello@example.com>",
            to=["one@example.com", "two@example.com"],
            cc="copy@example.com",
            bcc=["blind@example.com"],
            subject="Welcome!",
            html="<p>Welcome to our service</p>",
            text="Welcome to our service",
            reply_to="support@example.com",
            envelope_sender="bounce@example.com",
        )
        request = self.server.last
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.path, "/api/v1/sending/messages")
        self.assertEqual(
            request.json,
            {
                "to": ["one@example.com", "two@example.com"],
                "cc": ["copy@example.com"],
                "bcc": ["blind@example.com"],
                "content": {
                    "subject": "Welcome!",
                    "from": "Acme Store <hello@example.com>",
                    "textBody": "Welcome to our service",
                    "htmlBody": "<p>Welcome to our service</p>",
                    "replyTo": "support@example.com",
                },
                "envelopeSender": "bounce@example.com",
            },
        )
        self.assertEqual(result.data.tracking_id, "trk_123456789")
        self.assertEqual(result.data.status, "queued")
        self.assertEqual(result.data.recipients, 2)

    def test_send_accepts_full_message_mapping_and_from_alias(self) -> None:
        self.server.enqueue(data={"result": {"status": "queued", "trackingId": "t1"}})
        self.make_client().messages.send(
            {
                "recipients": "recipient@example.com",
                "subject": "Mapped",
                "content": {
                    "from": "Mapped <from@example.com>",
                    "htmlBody": "<p>body</p>",
                    "textBody": "body",
                    "replyTo": "reply@example.com",
                },
            }
        )
        self.assertEqual(
            self.server.last.json,
            {
                "to": ["recipient@example.com"],
                "cc": [],
                "bcc": [],
                "content": {
                    "subject": "Mapped",
                    "from": "Mapped <from@example.com>",
                    "textBody": "body",
                    "htmlBody": "<p>body</p>",
                    "replyTo": "reply@example.com",
                },
            },
        )

    def test_send_supports_url_attachments(self) -> None:
        self.server.enqueue(data={"result": {"status": "queued"}})
        self.make_client().messages.send(
            to="to@example.com",
            subject="Invoice",
            html="<p>Attached</p>",
            attachments=[
                "https://cdn.example.com/invoices/1042.pdf",
                {"url": "https://cdn.example.com/receipt.pdf", "name": "receipt.pdf"},
            ],
        )
        attachments = self.server.last.json["attachments"]
        self.assertEqual(
            attachments,
            [
                {
                    "url": "https://cdn.example.com/invoices/1042.pdf",
                    "fileName": "1042.pdf",
                },
                {
                    "url": "https://cdn.example.com/receipt.pdf",
                    "fileName": "receipt.pdf",
                },
            ],
        )

    def test_client_send_shortcut(self) -> None:
        self.server.enqueue(data={"result": {"status": "queued", "trackingId": "t9"}})
        self.assertIsInstance(
            self.make_client().send(
                to="to@example.com", subject="Shortcut", text="hello"
            ).data,
            SendResult,
        )

    def test_send_with_attachments_multipart(self) -> None:
        self.server.enqueue(data={"result": {"status": "queued", "trackingId": "t2"}})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "note.txt"
            path.write_bytes(b"hello attachment")
            result = self.make_client().messages.send_with_attachments(
                to="to@example.com",
                subject="Files",
                html="<p>Files</p>",
                files=[path, FileUpload("raw.bin", b"\x00\x01", "application/octet-stream")],
            )
        request = self.server.last
        self.assertEqual(request.path, "/api/v1/sending/messages/with-attachments")
        self.assertTrue(request.content_type.startswith("multipart/form-data; boundary="))
        parts = _multipart_parts(request.body, request.content_type)
        self.assertEqual(len(parts), 3)
        self.assertIn(b'name="message"', parts[0])
        message = json.loads(parts[0].split(b"\r\n\r\n", 1)[1].strip())
        self.assertEqual(message["to"], ["to@example.com"])
        self.assertEqual(message["content"]["subject"], "Files")
        self.assertIn(b'name="files"; filename="note.txt"', parts[1])
        self.assertIn(b"hello attachment", parts[1])
        self.assertIn(b'name="files"; filename="raw.bin"', parts[2])
        self.assertEqual(result.data.tracking_id, "t2")

    def test_send_with_attachments_requires_a_file(self) -> None:
        with self.assertRaises(ValueError):
            self.make_client().messages.send_with_attachments(
                to="to@example.com", subject="none"
            )

    def test_upload_attachment_uses_file_field_and_parses_result(self) -> None:
        self.server.enqueue(
            data={
                "file": {
                    "fileName": "logo.png",
                    "contentType": "image/png",
                    "sizeBytes": 3,
                    "publicUrl": "https://cdn.example.com/logo.png",
                }
            }
        )
        result = self.make_client().messages.upload_attachment(
            b"png", file_name="logo.png", content_type="image/png"
        )
        request = self.server.last
        self.assertEqual(request.path, "/api/v1/sending/attachments/upload")
        self.assertIn(b'name="file"; filename="logo.png"', request.body)
        self.assertIn(b"Content-Type: image/png", request.body)
        self.assertEqual(result.data.file_name, "logo.png")
        self.assertEqual(result.data.size_bytes, 3)
        self.assertEqual(result.data.public_url, "https://cdn.example.com/logo.png")

    def test_spam_check_payload_and_findings(self) -> None:
        self.server.enqueue(
            data={
                "score": 2.2,
                "threshold": 5.0,
                "isSpam": False,
                "rating": "moderate_risk",
                "badgeColor": "yellow",
                "deliverabilityScore": 78,
                "summary": "Moderate spam risk",
                "rules": [
                    {
                        "code": "MISSING_TEXT_PART",
                        "points": 1.0,
                        "title": "Missing Plain-Text Version",
                        "description": "HTML without text",
                        "recommendation": "Add a text part",
                    }
                ],
            }
        )
        result = self.make_client().messages.spam_check(
            subject="Hello",
            html="<p>Hi</p>",
            from_="Acme <hello@example.com>",
            reply_to="support@example.com",
            headers={"List-Unsubscribe": "<mailto:unsubscribe@example.com>"},
        )
        self.assertEqual(
            self.server.last.json,
            {
                "subject": "Hello",
                "html": "<p>Hi</p>",
                "from": "Acme <hello@example.com>",
                "replyTo": "support@example.com",
                "headers": {"List-Unsubscribe": "<mailto:unsubscribe@example.com>"},
            },
        )
        self.assertEqual(result.data.score, 2.2)
        self.assertFalse(result.data.is_spam)
        self.assertEqual(result.data.deliverability_score, 78)
        self.assertEqual(result.data.rules[0].code, "MISSING_TEXT_PART")

    def test_spam_check_accepts_message_mapping_aliases(self) -> None:
        self.server.enqueue(data={"score": 0.0, "rules": []})
        self.make_client().messages.spam_check(
            {
                "subject": "Mapped",
                "htmlBody": "<p>Mapped</p>",
                "text_body": "Mapped",
                "replyTo": "reply@example.com",
            }
        )
        self.assertEqual(
            self.server.last.json,
            {
                "subject": "Mapped",
                "html": "<p>Mapped</p>",
                "text": "Mapped",
                "replyTo": "reply@example.com",
            },
        )

    def test_list_tracking_and_summary(self) -> None:
        self.server.enqueue(
            data={
                "messages": [
                    {
                        "trackingId": "trk_1",
                        "senderDomain": "mail.example.com",
                        "subject": "Hello",
                        "recipientsCount": 3,
                        "acceptedCount": 3,
                        "deliveredCount": 2,
                        "bouncedCount": 1,
                        "openCount": 5,
                        "clickCount": 2,
                        "status": "delivered",
                        "createdAt": "2026-11-09T10:00:00",
                        "lastOpenedAt": "2026-11-09T11:00:00",
                        "lastClickedAt": None,
                        "lastDeliveryEventAt": "2026-11-09T10:30:00",
                    }
                ],
                "summary": {
                    "messages": 1,
                    "recipients": 3,
                    "accepted": 3,
                    "delivered": 2,
                    "bounced": 1,
                    "opens": 5,
                    "clicks": 2,
                },
            }
        )
        result = self.make_client().messages.list_tracking(
            limit=10,
            offset=5,
            status="delivered",
            from_date="2026-11-01",
            to_date="2026-11-09",
        )
        self.assertEqual(
            self.server.last.query_dict(),
            {
                "limit": "10",
                "offset": "5",
                "status": "delivered",
                "from": "2026-11-01",
                "to": "2026-11-09",
            },
        )
        message = result.data.messages[0]
        self.assertEqual(message.tracking_id, "trk_1")
        self.assertEqual(message.open_count, 5)
        self.assertIsNone(message.last_clicked_at)
        self.assertEqual(result.data.summary.opens, 5)

    def test_get_tracking_timeline(self) -> None:
        self.server.enqueue(
            data={
                "message": {
                    "message": {
                        "trackingId": "trk_1",
                        "senderDomain": "mail.example.com",
                        "subject": "Hello",
                        "status": "delivered",
                    },
                    "events": [
                        {
                            "id": "evt_1",
                            "eventType": "click",
                            "recipientEmail": "to@example.com",
                            "clickUrl": "https://example.com/promo",
                            "occurredAt": "2026-11-09T12:00:00",
                            "engagement": {"count": 1},
                        }
                    ],
                }
            }
        )
        result = self.make_client().messages.get_tracking("trk_1")
        self.assertEqual(result.data.message.tracking_id, "trk_1")
        self.assertEqual(result.data.events[0].event_type, "click")
        self.assertEqual(result.data.events[0].click_url, "https://example.com/promo")
        self.assertEqual(result.data.events[0].engagement, {"count": 1})

    def test_list_logs(self) -> None:
        self.server.enqueue(
            data={
                "available": True,
                "messages": [
                    {
                        "accountId": 7,
                        "trackingId": "trk_1",
                        "subject": "Hello",
                        "senderDomain": "mail.example.com",
                        "from": "hello@mail.example.com",
                        "fromName": "Acme",
                        "method": "api",
                        "to": ["to@example.com"],
                        "cc": [],
                        "receivedAt": "2026-11-09T10:00:00",
                        "status": "delivered",
                        "recipientsCount": 1,
                        "deliveredCount": 1,
                        "bouncedCount": 0,
                        "diagnostic": None,
                        "events": [],
                    }
                ],
                "hasMore": False,
                "eventDetailsAvailable": True,
            }
        )
        result = self.make_client().messages.list_logs(limit=20, status="delivered")
        self.assertEqual(
            self.server.last.query_dict(),
            {"limit": "20", "status": "delivered"},
        )
        self.assertTrue(result.data.available)
        self.assertEqual(result.data.messages[0].from_address, "hello@mail.example.com")
        self.assertEqual(result.data.messages[0].from_name, "Acme")
        self.assertTrue(result.data.event_details_available)

    def test_normalize_accepts_camel_and_snake_keys(self) -> None:
        normalized = normalize(
            {"trackingId": "a", "tracking_id": "b", "already_snake": True}
        )
        self.assertEqual(normalized["tracking_id"], "b")
        self.assertEqual(normalized["trackingId"], "a")
        self.assertTrue(normalized["already_snake"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
