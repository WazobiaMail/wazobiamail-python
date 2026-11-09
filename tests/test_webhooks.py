"""Webhook signature verification and event decoding tests."""

from __future__ import annotations

import hashlib
import hmac
import unittest

from wazobiamail import WazobiaMail, WazobiaWebhookError
from wazobiamail.resources.webhooks import SIGNATURE_HEADER


class TestWebhooks(unittest.TestCase):
    def setUp(self) -> None:
        self.webhooks = WazobiaMail("wzbm_mock_key").webhooks

    def test_signature_header_constant(self) -> None:
        self.assertEqual(SIGNATURE_HEADER, "X-Wazobia-Signature")
        self.assertEqual(self.webhooks.signature_header, SIGNATURE_HEADER)

    def test_sign_matches_hmac_sha256(self) -> None:
        payload = b'{"event":"message.delivered"}'
        secret = "whsec_test_secret"
        expected = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        self.assertEqual(self.webhooks.sign(payload, secret), expected)

    def test_sign_accepts_text_and_byte_payloads_and_secrets(self) -> None:
        text_signature = self.webhooks.sign('{"a":1}', "secret")
        byte_signature = self.webhooks.sign(b'{"a":1}', b"secret")
        self.assertEqual(text_signature, byte_signature)

    def test_verify_accepts_plain_and_prefixed_signatures(self) -> None:
        payload = '{"event":"message.delivered"}'
        secret = "whsec_test_secret"
        signature = self.webhooks.sign(payload, secret)
        self.assertTrue(self.webhooks.verify_signature(payload, signature, secret))
        self.assertTrue(
            self.webhooks.verify_signature(payload, f"sha256={signature}", secret)
        )
        self.assertTrue(
            self.webhooks.verify_signature(payload, f"SHA256={signature}", secret)
        )

    def test_verify_rejects_tampered_payload(self) -> None:
        secret = "whsec_test_secret"
        signature = self.webhooks.sign('{"amount":100}', secret)
        self.assertFalse(
            self.webhooks.verify_signature('{"amount":1000}', signature, secret)
        )

    def test_verify_rejects_missing_signature_or_secret(self) -> None:
        self.assertFalse(self.webhooks.verify_signature("{}", "", "secret"))
        self.assertFalse(self.webhooks.verify_signature("{}", "abc", ""))
        self.assertFalse(self.webhooks.verify_signature("{}", None, "secret"))  # type: ignore[arg-type]

    def test_sign_requires_secret(self) -> None:
        with self.assertRaises(WazobiaWebhookError):
            self.webhooks.sign("{}", "")

    def test_construct_event_returns_dict(self) -> None:
        payload = '{"event":"message.delivered","data":{"trackingId":"trk_1"}}'
        signature = self.webhooks.sign(payload, "secret")
        event = self.webhooks.construct_event(payload, signature, "secret")
        self.assertEqual(event["event"], "message.delivered")
        self.assertEqual(event["data"]["trackingId"], "trk_1")

    def test_construct_event_raises_for_bad_signature(self) -> None:
        with self.assertRaises(WazobiaWebhookError):
            self.webhooks.construct_event("{}", "bad-signature", "secret")

    def test_construct_event_raises_for_invalid_json(self) -> None:
        signature = self.webhooks.sign("not json", "secret")
        with self.assertRaises(WazobiaWebhookError):
            self.webhooks.construct_event("not json", signature, "secret")

    def test_construct_event_requires_json_object(self) -> None:
        payload = '["not", "an", "object"]'
        signature = self.webhooks.sign(payload, "secret")
        with self.assertRaises(WazobiaWebhookError):
            self.webhooks.construct_event(payload, signature, "secret")

    def test_construct_event_handles_unicode(self) -> None:
        payload = '{"name":"Ada \u2764\ufe0f"}'
        signature = self.webhooks.sign(payload, "secret")
        event = self.webhooks.construct_event(payload, signature, "secret")
        self.assertEqual(event["name"], "Ada \u2764\ufe0f")

    def test_webhooks_resource_performs_no_network_calls(self) -> None:
        self.assertFalse(hasattr(self.webhooks, "_http"))
        self.assertFalse(hasattr(self.webhooks, "_request"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
