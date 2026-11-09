"""Scoped sending API keys, SMTP relays and SMTP access tests."""

from __future__ import annotations

import unittest

from wazobiamail.models import CreatedApiKey, SmtpAccess

try:
    from ._server import MockServerTestCase
except ImportError:  # pragma: no cover
    from _server import MockServerTestCase


API_KEY = {
    "id": "mw95j90vk7IkKc5jtfHG",
    "name": "Checkout sender",
    "scope": "domain",
    "domainId": "dom_123",
    "domain": "mail.example.com",
    "keyPrefix": "wzbm_abcd1234",
    "lastUsedAt": None,
    "expiresAt": None,
    "revokedAt": None,
    "createdAt": "2026-11-09T00:00:00",
}

CREATED_KEY = {
    "id": "mw95j90vk7IkKc5jtfHG",
    "name": "Checkout sender",
    "scope": "domain",
    "domainId": "dom_123",
    "keyPrefix": "wzbm_abcd1234",
    "apiKey": "wzbm_live_newlygeneratedsecret",
    "expiresAt": None,
}

RELAY = {
    "id": "mw95j90vk7IkKc5jtfHG",
    "accountId": 7,
    "name": "Primary relay",
    "smtpHost": "smtp.sendgrid.net",
    "smtpPort": 587,
    "smtpUsername": "apikey",
    "smtpSecurity": "starttls",
    "status": "active",
    "isDefault": True,
    "hasPassword": True,
    "createdAt": "2026-11-09T00:00:00",
    "updatedAt": "2026-11-09T00:00:00",
}


class TestApiKeys(MockServerTestCase):
    def test_list_api_keys(self) -> None:
        self.server.enqueue(data={"items": [API_KEY]})
        result = self.make_client().api_keys.list()
        self.assertEqual(self.server.last.path, "/api/v1/sending/api-keys")
        self.assertEqual(result.data[0].name, "Checkout sender")
        self.assertEqual(result.data[0].key_prefix, "wzbm_abcd1234")
        self.assertEqual(result.data[0].domain_id, "dom_123")

    def test_create_and_regenerate(self) -> None:
        self.server.enqueue(status=201, data={"apiKey": CREATED_KEY})
        created = self.make_client().api_keys.create(
            "Checkout sender",
            scope="domain",
            domain_id="dom_123",
            expires_at="2027-01-01T00:00:00Z",
        )
        self.assertEqual(self.server.last.method, "POST")
        self.assertEqual(
            self.server.last.json,
            {
                "name": "Checkout sender",
                "scope": "domain",
                "domainId": "dom_123",
                "expiresAt": "2027-01-01T00:00:00Z",
            },
        )
        self.assertIsInstance(created.data, CreatedApiKey)
        self.assertEqual(
            created.data.api_key, "wzbm_live_newlygeneratedsecret"
        )
        self.assertNotIn("newlygeneratedsecret", repr(created.data))

        self.server.enqueue(data={"apiKey": CREATED_KEY})
        regenerated = self.make_client().api_keys.regenerate("key_1")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/sending/api-keys/key_1/regenerate",
        )
        self.assertEqual(regenerated.data.id, "mw95j90vk7IkKc5jtfHG")

    def test_create_accepts_direct_created_object(self) -> None:
        self.server.enqueue(data=CREATED_KEY)
        result = self.make_client().api_keys.create("Direct")
        self.assertEqual(result.data.api_key, "wzbm_live_newlygeneratedsecret")

    def test_create_accepts_nested_key_object(self) -> None:
        self.server.enqueue(data={"api_key": CREATED_KEY})
        result = self.make_client().api_keys.create("Nested")
        self.assertEqual(result.data.id, "mw95j90vk7IkKc5jtfHG")
        self.assertEqual(result.data.api_key, "wzbm_live_newlygeneratedsecret")

    def test_revoke(self) -> None:
        self.server.enqueue(data={"keyId": "key_1"})
        result = self.make_client().api_keys.revoke("key_1")
        self.assertEqual(self.server.last.method, "POST")
        self.assertEqual(
            self.server.last.path, "/api/v1/sending/api-keys/key_1/revoke"
        )
        self.assertEqual(result.data["keyId"], "key_1")

    def test_key_ids_are_encoded(self) -> None:
        self.server.enqueue(data={"keyId": "a/b"})
        self.make_client().api_keys.revoke("a/b")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/sending/api-keys/a%2Fb/revoke",
        )


class TestSmtpRelays(MockServerTestCase):
    def test_list_uses_smtp_relays_wrapper(self) -> None:
        self.server.enqueue(data={"smtpRelays": [RELAY]})
        result = self.make_client().smtp_relays.list()
        self.assertEqual(self.server.last.path, "/api/v1/smtp-relays")
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].smtp_host, "smtp.sendgrid.net")
        self.assertTrue(result.data[0].has_password)

    def test_get_uses_smtp_relay_wrapper(self) -> None:
        self.server.enqueue(data={"smtpRelay": RELAY})
        result = self.make_client().smtp_relays.get("relay_1")
        self.assertEqual(self.server.last.path, "/api/v1/smtp-relays/relay_1")
        self.assertEqual(result.data.smtp_port, 587)

    def test_create_sends_snake_case_contract(self) -> None:
        self.server.enqueue(status=201, data={"smtpRelay": RELAY})
        result = self.make_client().smtp_relays.create(
            "Primary relay",
            host="smtp.example.com",
            port=465,
            username="sdk@example.com",
            password="SecretPass123!",
            tls_mode="ssl_tls",
            status="active",
            is_default=True,
        )
        self.assertEqual(
            self.server.last.json,
            {
                "name": "Primary relay",
                "smtp_host": "smtp.example.com",
                "smtp_port": 465,
                "smtp_username": "sdk@example.com",
                "smtp_password": "SecretPass123!",
                "smtp_security": "ssl_tls",
                "status": "active",
                "is_default": True,
            },
        )
        self.assertEqual(result.data.smtp_security, "starttls")

    def test_create_accepts_smtp_prefixed_arguments(self) -> None:
        self.server.enqueue(data={"smtpRelay": RELAY})
        self.make_client().smtp_relays.create(
            "Prefixed",
            smtp_host="smtp.mailgun.org",
            smtp_port=2525,
            smtp_username="postmaster@example.com",
            smtp_password="SecretPass123!",
        )
        payload = self.server.last.json
        self.assertEqual(payload["smtp_host"], "smtp.mailgun.org")
        self.assertEqual(payload["smtp_port"], 2525)
        self.assertEqual(payload["smtp_username"], "postmaster@example.com")
        self.assertEqual(payload["smtp_security"], "starttls")

    def test_update_delete_activate_and_deactivate(self) -> None:
        self.server.enqueue(data={"smtpRelay": {**RELAY, "name": "Updated"}})
        updated = self.make_client().smtp_relays.update(
            "relay_1",
            name="Updated",
            smtp_host="smtp.new.example.com",
            smtp_port=2525,
            smtp_username="new@example.com",
            smtp_password="NewSecret123!",
            smtp_security="none",
            status="inactive",
            is_default=False,
        )
        self.assertEqual(self.server.last.method, "PATCH")
        self.assertEqual(
            self.server.last.json,
            {
                "name": "Updated",
                "smtp_host": "smtp.new.example.com",
                "smtp_port": 2525,
                "smtp_username": "new@example.com",
                "smtp_password": "NewSecret123!",
                "smtp_security": "none",
                "status": "inactive",
                "is_default": False,
            },
        )
        self.assertEqual(updated.data.name, "Updated")

        self.server.enqueue(data={"smtpRelay": {**RELAY, "status": "inactive"}})
        deactivated = self.make_client().smtp_relays.deactivate("relay_1")
        self.assertEqual(
            self.server.last.path, "/api/v1/smtp-relays/relay_1/deactivate"
        )
        self.assertEqual(deactivated.data.status, "inactive")

        self.server.enqueue(data={"smtpRelay": RELAY})
        activated = self.make_client().smtp_relays.activate("relay_1")
        self.assertEqual(
            self.server.last.path, "/api/v1/smtp-relays/relay_1/activate"
        )
        self.assertEqual(activated.data.status, "active")

        self.server.enqueue(data={"relayId": "relay_1"})
        deleted = self.make_client().smtp_relays.delete("relay_1")
        self.assertEqual(self.server.last.method, "DELETE")
        self.assertEqual(self.server.last.body, b"")
        self.assertEqual(deleted.data["relayId"], "relay_1")


class TestSmtpAccess(MockServerTestCase):
    def test_get_entitlement(self) -> None:
        self.server.enqueue(
            data={
                "paid": True,
                "eligible": True,
                "enabled": True,
                "persona": "developer",
                "configured": True,
                "connection": {
                    "host": "smtp.example.com",
                    "port": 587,
                    "security": "STARTTLS",
                    "usernames": ["support@brand.com"],
                },
            }
        )
        result = self.make_client().smtp_access.get()
        self.assertEqual(self.server.last.path, "/api/v1/sending/smtp-access")
        self.assertIsInstance(result.data, SmtpAccess)
        self.assertTrue(result.data.enabled)
        self.assertEqual(result.data.connection.usernames, ["support@brand.com"])

    def test_update_preference(self) -> None:
        self.server.enqueue(data={"enabled": True})
        result = self.make_client().smtp_access.update(True)
        self.assertEqual(self.server.last.method, "PUT")
        self.assertEqual(self.server.last.json, {"enabled": True})
        self.assertEqual(result.data, {"enabled": True})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
