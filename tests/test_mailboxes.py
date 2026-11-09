"""Hosted mailbox, credential and enterprise inbox tests."""

from __future__ import annotations

import unittest

from wazobiamail.models import CreatedMailbox, MailboxConnection, MailboxMessagesPage

try:
    from ._server import MockServerTestCase
except ImportError:  # pragma: no cover
    from _server import MockServerTestCase


MAILBOX = {
    "id": "mbx_123",
    "domainId": "dom_123",
    "address": "support@brand.com",
    "localPart": "support",
    "displayName": "Support Team",
    "status": "active",
    "isPlatformSubdomain": False,
    "autoProvisioned": False,
    "role": "general",
    "createdAt": "2026-11-09T00:00:00",
    "updatedAt": "2026-11-09T00:00:00",
}

CREDENTIAL = {
    "id": "cred_1",
    "mailboxId": "mbx_123",
    "username": "support@brand.com",
    "expiresAt": None,
    "revokedAt": None,
    "createdAt": "2026-11-09T00:00:00",
}


class TestMailboxes(MockServerTestCase):
    def test_list_returns_bare_array(self) -> None:
        self.server.enqueue(data=[MAILBOX])
        result = self.make_client().mailboxes.list()
        self.assertEqual(self.server.last.path, "/api/v1/mailboxes")
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].address, "support@brand.com")
        self.assertEqual(result.data[0].domain_id, "dom_123")

    def test_create_mailbox_and_initial_credential(self) -> None:
        self.server.enqueue(
            status=201,
            message="Your mailbox is ready.",
            data={
                "mailbox": MAILBOX,
                "credential": {
                    "credential": CREDENTIAL,
                    "password": "GeneratedPassword123!",
                },
            },
        )
        result = self.make_client().mailboxes.create(
            domain_id="dom_123",
            local_part="support",
            display_name="Support Team",
            quota_mb=2048,
            password="ChosenPassword123!",
            role="general",
            status="active",
        )
        self.assertEqual(self.server.last.method, "POST")
        self.assertEqual(
            self.server.last.json,
            {
                "domainId": "dom_123",
                "localPart": "support",
                "displayName": "Support Team",
                "quotaMb": 2048,
                "password": "ChosenPassword123!",
                "role": "general",
                "status": "active",
            },
        )
        self.assertIsInstance(result.data, CreatedMailbox)
        self.assertEqual(result.data.mailbox.address, "support@brand.com")
        self.assertEqual(
            result.data.credential.credential.username, "support@brand.com"
        )
        self.assertEqual(
            result.data.credential.password, "GeneratedPassword123!"
        )

    def test_get_update_activate_and_suspend(self) -> None:
        self.server.enqueue(data={"mailbox": MAILBOX})
        result = self.make_client().mailboxes.get("mbx_123")
        self.assertEqual(self.server.last.path, "/api/v1/mailboxes/mbx_123")
        self.assertEqual(result.data.display_name, "Support Team")

        self.server.enqueue(
            data={"mailbox": {**MAILBOX, "displayName": "Customer Care"}}
        )
        updated = self.make_client().mailboxes.update(
            "mbx_123", display_name="Customer Care", password="NewPassword123!"
        )
        self.assertEqual(self.server.last.method, "PATCH")
        self.assertEqual(
            self.server.last.json,
            {"displayName": "Customer Care", "password": "NewPassword123!"},
        )
        self.assertEqual(updated.data.display_name, "Customer Care")

        self.server.enqueue(data={"mailbox": {**MAILBOX, "status": "suspended"}})
        suspended = self.make_client().mailboxes.suspend("mbx_123")
        self.assertEqual(self.server.last.path, "/api/v1/mailboxes/mbx_123/suspend")
        self.assertEqual(self.server.last.json, {})
        self.assertEqual(suspended.data.status, "suspended")

        self.server.enqueue(data={"mailbox": MAILBOX})
        activated = self.make_client().mailboxes.activate("mbx_123")
        self.assertEqual(self.server.last.path, "/api/v1/mailboxes/mbx_123/activate")
        self.assertEqual(activated.data.status, "active")

    def test_delete_mailbox(self) -> None:
        self.server.enqueue(data={"mailboxId": "mbx_123"})
        result = self.make_client().mailboxes.delete("mbx_123")
        self.assertEqual(self.server.last.method, "DELETE")
        self.assertEqual(result.data, {"mailboxId": "mbx_123"})

    def test_storage_metrics(self) -> None:
        self.server.enqueue(
            data={
                "mailboxes": [
                    {
                        "id": "mbx_123",
                        "address": "support@brand.com",
                        "usageBytes": 1024,
                        "quotaBytes": 2048,
                    }
                ],
                "customers": [{"accountId": 7, "usageBytes": 1024}],
                "domains": [{"domain": "brand.com", "usageBytes": 1024}],
                "measurement": "bytes",
                "plan": {
                    "mailboxLimit": 10,
                    "baseMailboxLimit": 10,
                    "additionalMailboxLimit": 0,
                    "mailboxesUsed": 1,
                    "mailboxRemaining": 9,
                    "storageTotalBytes": 10240,
                    "storageAllocatedBytes": 2048,
                    "storageRemainingBytes": 8192,
                },
            }
        )
        result = self.make_client().mailboxes.storage()
        self.assertEqual(self.server.last.path, "/api/v1/mailboxes/storage")
        self.assertEqual(result.data.plan.mailboxes_used, 1)
        self.assertEqual(result.data.plan.storage_remaining_bytes, 8192)
        self.assertEqual(result.data.mailboxes[0]["usageBytes"], 1024)

    def test_connection_and_password(self) -> None:
        self.server.enqueue(
            data={
                "mailboxId": "mbx_123",
                "domainId": "dom_123",
                "username": "support@brand.com",
                "status": "active",
                "smtp": {"host": "smtp.example.com", "port": 587, "security": "STARTTLS"},
                "imap": {"host": "imap.example.com", "port": 993, "security": "SSL/TLS"},
                "pop3": {"host": "imap.example.com", "port": 995, "security": "SSL/TLS"},
                "authentication": "Normal password",
                "passwordHint": "Use the mailbox password",
            }
        )
        connection = self.make_client().mailboxes.connection("mbx_123")
        self.assertEqual(
            self.server.last.path, "/api/v1/mailboxes/mbx_123/connection"
        )
        self.assertIsInstance(connection.data, MailboxConnection)
        self.assertEqual(connection.data.smtp["port"], 587)
        self.assertEqual(connection.data.password_hint, "Use the mailbox password")

        self.server.enqueue(data={"password": "MailboxSecret123!"})
        password = self.make_client().mailboxes.password("mbx_123")
        self.assertEqual(password.data, "MailboxSecret123!")

    def test_credential_create_rotate_and_revoke(self) -> None:
        self.server.enqueue(
            status=201,
            data={"credential": {"credential": CREDENTIAL, "password": "PassOne!"}},
        )
        created = self.make_client().mailboxes.create_credentials("mbx_123")
        self.assertEqual(
            self.server.last.path, "/api/v1/mailboxes/mbx_123/credentials"
        )
        self.assertEqual(created.data.credential.id, "cred_1")
        self.assertEqual(created.data.password, "PassOne!")

        self.server.enqueue(
            data={"credential": {"credential": CREDENTIAL, "password": "PassTwo!"}}
        )
        rotated = self.make_client().mailboxes.rotate_credentials("mbx_123")
        self.assertEqual(
            self.server.last.path, "/api/v1/mailboxes/mbx_123/credentials/rotate"
        )
        self.assertEqual(rotated.data.password, "PassTwo!")

        self.server.enqueue(
            data={"mailboxId": "mbx_123", "credentialId": "cred_1"}
        )
        revoked = self.make_client().mailboxes.revoke_credential("mbx_123", "cred_1")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/mailboxes/mbx_123/credentials/cred_1/revoke",
        )
        self.assertEqual(revoked.data["credentialId"], "cred_1")

    def test_webmail_login(self) -> None:
        self.server.enqueue(data={"url": "https://webmail.example.com/login?token=x"})
        result = self.make_client().mailboxes.webmail_login("mbx_123")
        self.assertEqual(
            self.server.last.path, "/api/v1/mailboxes/mbx_123/webmail-login"
        )
        self.assertIn("webmail", result.data["url"])

    def test_aliases(self) -> None:
        client = self.make_client()
        self.assertEqual(client.mailboxes.get_storage.__name__, "storage")
        self.assertEqual(
            client.mailboxes.get_connection_settings.__name__, "connection"
        )

    def test_message_list_query_and_parsing(self) -> None:
        self.server.enqueue(
            data={
                "items": [
                    {
                        "id": "msg_1",
                        "threadId": "thread_1",
                        "from": [{"name": "Sender", "email": "sender@example.com"}],
                        "to": [{"name": "Support", "email": "support@brand.com"}],
                        "subject": "Hello",
                        "preview": "Hi there",
                        "receivedAt": "2026-11-09T12:00:00Z",
                        "isUnread": True,
                        "hasAttachments": False,
                        "sizeBytes": 123,
                    }
                ],
                "total": 1,
                "page": 2,
                "limit": 10,
            }
        )
        result = self.make_client().mailboxes.messages.list(
            "mbx_123", page=2, limit=10, unread_only=True, search="Hello"
        )
        self.assertEqual(
            self.server.last.query_dict(),
            {
                "page": "2",
                "limit": "10",
                "unreadOnly": "true",
                "search": "Hello",
            },
        )
        self.assertIsInstance(result.data, MailboxMessagesPage)
        self.assertEqual(result.data.items[0].from_[0].email, "sender@example.com")
        self.assertTrue(result.data.items[0].is_unread)
        self.assertEqual(result.data.total, 1)

    def test_message_get_and_delete(self) -> None:
        self.server.enqueue(
            data={
                "id": "msg_1",
                "threadId": "thread_1",
                "from": [{"name": "Sender", "email": "sender@example.com"}],
                "to": [{"name": "Support", "email": "support@brand.com"}],
                "cc": [],
                "bcc": [],
                "replyTo": [],
                "subject": "Hello",
                "preview": "Hi there",
                "textBody": "Hi there",
                "htmlBody": "<p>Hi there</p>",
                "attachments": [
                    {
                        "blobId": "blob_1",
                        "name": "file.pdf",
                        "type": "application/pdf",
                        "size": 42,
                    }
                ],
                "receivedAt": "2026-11-09T12:00:00Z",
                "isUnread": False,
                "sizeBytes": 123,
            }
        )
        detail = self.make_client().mailboxes.messages.get("mbx_123", "msg_1")
        self.assertEqual(
            self.server.last.path, "/api/v1/mailboxes/mbx_123/messages/msg_1"
        )
        self.assertEqual(detail.data.text_body, "Hi there")
        self.assertEqual(detail.data.attachments[0].content_type, "application/pdf")

        self.server.enqueue(data={})
        self.make_client().mailboxes.messages.delete("mbx_123", "msg_1")
        self.assertEqual(self.server.last.method, "DELETE")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
