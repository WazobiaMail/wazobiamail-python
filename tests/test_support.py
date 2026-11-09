"""Support ticket identity, attachments and conversation tests."""

from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from wazobiamail import WazobiaAuthenticationError
from wazobiamail.models import SupportTicket, SupportTicketCreated, SupportTicketPage

try:
    from ._server import MockServerTestCase
except ImportError:  # pragma: no cover
    from _server import MockServerTestCase


ACCOUNT = {
    "accountId": 7,
    "email": "ada@example.com",
    "username": "ada",
    "name": "Ada Lovelace",
    "planId": "starter",
    "selectedPlanId": "starter",
    "saasRole": "user",
    "authProvider": "email",
}

TICKET = {
    "id": "ticket_123",
    "accountId": 7,
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "subject": "Cannot verify domain",
    "domain": "example.com",
    "category": "domain",
    "priority": "high",
    "status": "open",
    "messages": [
        {
            "id": "msg_1",
            "ticketId": "ticket_123",
            "senderName": "Ada Lovelace",
            "senderEmail": "ada@example.com",
            "message": "The TXT record never verifies.",
            "isFromStaff": False,
            "contentType": "text",
            "attachments": [
                {"id": "att_1", "filename": "dig.txt", "sizeBytes": 42}
            ],
            "createdAt": "2026-11-09T00:00:00Z",
        }
    ],
    "customerReadAt": None,
    "staffReadAt": None,
    "createdAt": "2026-11-09T00:00:00Z",
    "updatedAt": "2026-11-09T00:00:00Z",
}


class TestSupport(MockServerTestCase):
    def test_create_with_explicit_identity_skips_me_lookup(self) -> None:
        self.server.enqueue(
            status=201,
            message="Support ticket created successfully",
            data={"id": "ticket_123", "ticketId": "ticket_123"},
        )
        result = self.make_client().support.create(
            "Cannot verify domain",
            "The TXT record never verifies.",
            category="domain",
            priority="high",
            name="Ada Lovelace",
            email="ada@example.com",
            domain="example.com",
            content_type="text",
        )
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(self.server.last.path, "/api/v1/support")
        self.assertEqual(
            self.server.last.json,
            {
                "name": "Ada Lovelace",
                "email": "ada@example.com",
                "subject": "Cannot verify domain",
                "message": "The TXT record never verifies.",
                "category": "domain",
                "priority": "high",
                "domain": "example.com",
                "contentType": "text",
            },
        )
        self.assertIsInstance(result.data, SupportTicketCreated)
        self.assertEqual(result.data.id, "ticket_123")
        self.assertEqual(result.data.ticket_id, "ticket_123")

    def test_create_autofills_identity_from_auth_me(self) -> None:
        self.server.enqueue(data=ACCOUNT)
        self.server.enqueue(
            status=201, data={"id": "ticket_123", "ticketId": "ticket_123"}
        )
        self.make_client().support.create(
            "Cannot verify domain", "Please help", category="general"
        )
        self.assertEqual(len(self.server.requests), 2)
        self.assertEqual(self.server.requests[0].path, "/api/v1/auth/me")
        self.assertEqual(self.server.requests[1].path, "/api/v1/support")
        payload = self.server.requests[1].json
        self.assertEqual(payload["name"], "Ada Lovelace")
        self.assertEqual(payload["email"], "ada@example.com")
        self.assertEqual(payload["priority"], "normal")

    def test_create_fills_only_the_missing_identity_field(self) -> None:
        self.server.enqueue(data=ACCOUNT)
        self.server.enqueue(data={"id": "ticket_123", "ticketId": "ticket_123"})
        self.make_client().support.create(
            "Billing question",
            "Please review my invoice",
            name="Custom Name",
            category="billing",
            priority="low",
        )
        payload = self.server.last.json
        self.assertEqual(payload["name"], "Custom Name")
        self.assertEqual(payload["email"], "ada@example.com")

    def test_create_falls_back_to_username_when_name_is_absent(self) -> None:
        self.server.enqueue(data={**ACCOUNT, "name": None})
        self.server.enqueue(data={"id": "ticket_123", "ticketId": "ticket_123"})
        self.make_client().support.create("Hello", "World")
        self.assertEqual(self.server.last.json["name"], "ada")

    def test_create_propagates_identity_lookup_failure(self) -> None:
        self.server.enqueue_error(401, "Invalid API key")
        with self.assertRaises(WazobiaAuthenticationError):
            self.make_client().support.create("Hello", "World")
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(self.server.requests[0].path, "/api/v1/auth/me")

    def test_create_requires_identity_when_auth_me_has_no_email(self) -> None:
        self.server.enqueue(data={**ACCOUNT, "email": ""})
        with self.assertRaises(ValueError) as caught:
            self.make_client().support.create("Hello", "World")
        self.assertIn("email", str(caught.exception))

    def test_create_with_attachments_from_paths_tuples_and_mappings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dig.txt"
            path.write_bytes(b"txt record output")
            self.server.enqueue(
                status=201, data={"id": "ticket_123", "ticketId": "ticket_123"}
            )
            self.make_client().support.create(
                "Attachments",
                "See attached",
                name="Ada",
                email="ada@example.com",
                content_type="html",
                attachments=[
                    path,
                    ("headers.txt", b"Received: from example.com"),
                    {"filename": "shot.png", "content": b"\x89PNG"},
                ],
            )
        payload = self.server.last.json
        self.assertEqual(payload["contentType"], "html")
        self.assertEqual(len(payload["attachments"]), 3)
        self.assertEqual(payload["attachments"][0]["filename"], "dig.txt")
        self.assertEqual(
            base64.b64decode(payload["attachments"][0]["data"]),
            b"txt record output",
        )
        self.assertEqual(payload["attachments"][1]["filename"], "headers.txt")
        self.assertEqual(
            base64.b64decode(payload["attachments"][1]["data"]),
            b"Received: from example.com",
        )
        self.assertEqual(payload["attachments"][2]["filename"], "shot.png")
        self.assertEqual(
            base64.b64decode(payload["attachments"][2]["data"]), b"\x89PNG"
        )

    def test_create_rejects_invalid_attachments(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.make_client().support.create(
                "Missing",
                "File",
                name="Ada",
                email="ada@example.com",
                attachments=["/definitely/not/here.txt"],
            )
        with self.assertRaises(ValueError):
            self.make_client().support.create(
                "Invalid",
                "Mapping",
                name="Ada",
                email="ada@example.com",
                attachments=[{"filename": "missing-data.txt"}],
            )

    def test_list_tickets(self) -> None:
        self.server.enqueue(
            data={"items": [TICKET], "total": 1, "page": 2, "pages": 3}
        )
        result = self.make_client().support.list(
            status="open", page=2, limit=10
        )
        self.assertEqual(self.server.last.path, "/api/v1/support/my")
        self.assertEqual(
            self.server.last.query_dict(),
            {"status": "open", "page": "2", "limit": "10"},
        )
        self.assertIsInstance(result.data, SupportTicketPage)
        self.assertEqual(result.data.total, 1)
        self.assertEqual(result.data.page, 2)
        self.assertEqual(result.data.pages, 3)
        self.assertEqual(result.data.items[0].subject, "Cannot verify domain")

    def test_get_ticket_with_messages_and_attachments(self) -> None:
        self.server.enqueue(data=TICKET)
        result = self.make_client().support.get("ticket_123")
        self.assertEqual(
            self.server.last.path, "/api/v1/support/tickets/ticket_123"
        )
        self.assertIsInstance(result.data, SupportTicket)
        self.assertEqual(result.data.category, "domain")
        self.assertEqual(result.data.priority, "high")
        message = result.data.messages[0]
        self.assertEqual(message.ticket_id, "ticket_123")
        self.assertEqual(message.sender_name, "Ada Lovelace")
        self.assertFalse(message.is_from_staff)
        self.assertEqual(message.attachments[0].filename, "dig.txt")
        self.assertEqual(message.attachments[0].size_bytes, 42)

    def test_reply_and_mark_read(self) -> None:
        client = self.make_client()

        self.server.enqueue(data={})
        replied = client.support.reply(
            "ticket_123",
            "Any update?",
            content_type="text",
            attachments=[("ping.txt", b"ping")],
        )
        self.assertEqual(self.server.last.method, "POST")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/support/tickets/ticket_123/messages",
        )
        payload = self.server.last.json
        self.assertEqual(payload["message"], "Any update?")
        self.assertEqual(payload["contentType"], "text")
        self.assertEqual(payload["attachments"][0]["filename"], "ping.txt")
        self.assertEqual(
            base64.b64decode(payload["attachments"][0]["data"]), b"ping"
        )
        self.assertEqual(replied.data, {})

        self.server.enqueue(data={})
        client.support.mark_read("ticket_123")
        self.assertEqual(self.server.last.method, "POST")
        self.assertEqual(
            self.server.last.path, "/api/v1/support/tickets/ticket_123/read"
        )
        self.assertEqual(self.server.last.json, {})

    def test_ticket_ids_are_url_encoded(self) -> None:
        self.server.enqueue(data=TICKET)
        self.make_client().support.get("id/with space")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/support/tickets/id%2Fwith%20space",
        )

    def test_create_ticket_alias_is_the_same_callable(self) -> None:
        from wazobiamail.resources.support import SupportResource

        self.assertIs(SupportResource.create_ticket, SupportResource.create)
        client = self.make_client()
        self.assertIs(client.support.create_ticket.__func__, client.support.create.__func__)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
