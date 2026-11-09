"""Client configuration, authentication and construction tests."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from wazobiamail import Wazobia, WazobiaMail
from wazobiamail.errors import WazobiaAuthenticationError

try:  # Supports both package and top-level unittest discovery.
    from ._server import MockServerTestCase
except ImportError:  # pragma: no cover
    from _server import MockServerTestCase


class TestClientConfiguration(unittest.TestCase):
    def setUp(self) -> None:
        self._env = patch.dict(os.environ, {}, clear=False)
        self._env.start()
        for name in list(os.environ):
            if name.startswith("WAZOBIA"):
                os.environ.pop(name)
        self.addCleanup(self._env.stop)

    def test_initialize_with_positional_api_key(self) -> None:
        client = WazobiaMail("wzbm_live_1234567890abcdef")
        self.assertEqual(client.config.api_key, "wzbm_live_1234567890abcdef")
        self.assertEqual(client.config.auth_scheme, "header")

    def test_initialize_with_keyword_options(self) -> None:
        client = WazobiaMail(
            api_key="wzbm_live_1234567890abcdef",
            timeout=15.0,
            auth_scheme="header",
            headers={"X-Tenant": "acme"},
            user_agent="acme/1.0",
        )
        self.assertEqual(client.config.timeout, 15.0)
        self.assertEqual(client.config.headers, {"X-Tenant": "acme"})
        self.assertEqual(client.config.user_agent, "acme/1.0")

    def test_environment_fallbacks(self) -> None:
        os.environ["WAZOBIA_API_KEY"] = "wzbm_env_key_1"
        self.assertEqual(WazobiaMail().config.api_key, "wzbm_env_key_1")

    def test_secondary_environment_name(self) -> None:
        os.environ["WAZOBIAMAIL_API_KEY"] = "wzbm_secondary_env_key"
        self.assertEqual(
            WazobiaMail().config.api_key, "wzbm_secondary_env_key"
        )

    def test_access_token_infers_bearer_scheme(self) -> None:
        client = WazobiaMail(access_token="access-token-value")
        self.assertEqual(client.config.auth_scheme, "bearer")
        self.assertIsNone(client.config.api_key)

    def test_access_token_from_environment(self) -> None:
        os.environ["WAZOBIA_ACCESS_TOKEN"] = "env-access-token"
        client = WazobiaMail()
        self.assertEqual(client.config.access_token, "env-access-token")
        self.assertEqual(client.config.auth_scheme, "bearer")

    def test_missing_credentials_raise(self) -> None:
        with self.assertRaises(WazobiaAuthenticationError):
            WazobiaMail()

    def test_empty_or_whitespace_api_key_raises(self) -> None:
        with self.assertRaises(WazobiaAuthenticationError):
            WazobiaMail("")
        with self.assertRaises(WazobiaAuthenticationError):
            WazobiaMail("   ")

    def test_unauthenticated_client_is_allowed(self) -> None:
        client = WazobiaMail(allow_unauthenticated=True)
        self.assertIsNone(client.config.api_key)
        self.assertIsNone(client.config.access_token)

    def test_whitespace_is_trimmed(self) -> None:
        client = WazobiaMail("  wzbm_trimmed_key  ")
        self.assertEqual(client.config.api_key, "wzbm_trimmed_key")

    def test_base_url_trailing_slashes_are_removed(self) -> None:
        client = WazobiaMail(
            "wzbm_mock", base_url="https://custom.api.wazobiamail.com/api/v1///"
        )
        self.assertEqual(
            client.config.base_url, "https://custom.api.wazobiamail.com/api/v1"
        )

    def test_invalid_base_url_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            WazobiaMail("wzbm_mock", base_url="api.wazobiamail.com/v1")

    def test_invalid_auth_scheme_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            WazobiaMail("wzbm_mock", auth_scheme="query")

    def test_invalid_timeout_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            WazobiaMail("wzbm_mock", timeout=0)

    def test_environment_timeout_is_parsed(self) -> None:
        os.environ["WAZOBIA_TIMEOUT"] = "12.5"
        self.assertEqual(WazobiaMail("wzbm_mock").config.timeout, 12.5)

    def test_wazobia_alias_and_resource_aliases(self) -> None:
        self.assertIs(Wazobia, WazobiaMail)
        client = Wazobia("wzbm_mock")
        self.assertIs(client.emails, client.messages)

    def test_repr_and_to_dict_mask_secrets(self) -> None:
        client = WazobiaMail(
            "wzbm_live_supersecretsecret9999",
            access_token="access-token-super-secret",
            auth_scheme="both",
        )
        rendered = repr(client)
        self.assertNotIn("supersecretsecret", rendered)
        self.assertNotIn("access-token-super-secret", rendered)
        self.assertIn("wzbm_...9999", rendered)
        serialized = client.to_dict()
        self.assertEqual(serialized["api_key"], "wzbm_...9999")
        self.assertEqual(serialized["access_token"], "acces...cret")

    def test_context_manager(self) -> None:
        with WazobiaMail("wzbm_mock") as client:
            self.assertIsInstance(client, WazobiaMail)

    def test_client_module_compatibility_import(self) -> None:
        from wazobiamail.client import WazobiaMail as LegacyClient

        self.assertIs(LegacyClient, WazobiaMail)


class TestRequestHeaders(MockServerTestCase):
    def test_api_key_header_and_default_headers(self) -> None:
        self.server.enqueue(
            data={
                "accountId": 1,
                "email": "user@example.com",
                "planId": "starter",
                "selectedPlanId": "starter",
                "saasRole": "user",
                "authProvider": "email",
            }
        )
        client = self.make_client()
        client.auth.me()
        request = self.server.last
        self.assertEqual(request.headers["x-api-key"], "wzbm_test_key_1234567890")
        self.assertNotIn("authorization", request.headers)
        self.assertEqual(request.headers["accept"], "application/json")
        self.assertTrue(request.headers["user-agent"].startswith("wazobiamail-python/"))

    def test_bearer_scheme(self) -> None:
        self.server.enqueue(data=[])
        client = WazobiaMail(
            access_token="token-123", base_url=self.server.base_url, auth_scheme="bearer"
        )
        client.domains.list()
        request = self.server.last
        self.assertEqual(request.headers["authorization"], "Bearer token-123")
        self.assertNotIn("x-api-key", request.headers)

    def test_both_scheme(self) -> None:
        self.server.enqueue(data=[])
        client = WazobiaMail(
            api_key="wzbm_both_key",
            access_token="token-123",
            base_url=self.server.base_url,
            auth_scheme="both",
        )
        client.domains.list()
        request = self.server.last
        self.assertEqual(request.headers["x-api-key"], "wzbm_both_key")
        self.assertEqual(request.headers["authorization"], "Bearer token-123")

    def test_custom_headers_override_defaults(self) -> None:
        self.server.enqueue(data=[])
        client = self.make_client(
            headers={"X-Tenant": "acme", "Accept": "application/vnd.wazobia+json"},
            user_agent="acme-sdk/2.0",
        )
        client.domains.list()
        request = self.server.last
        self.assertEqual(request.headers["x-tenant"], "acme")
        self.assertEqual(
            request.headers["accept"], "application/vnd.wazobia+json"
        )
        self.assertEqual(request.headers["user-agent"], "acme-sdk/2.0")

    def test_unauthenticated_requests_send_no_credentials(self) -> None:
        self.server.enqueue(data=[])
        client = WazobiaMail(
            allow_unauthenticated=True, base_url=self.server.base_url
        )
        client.plans.list()
        request = self.server.last
        self.assertNotIn("x-api-key", request.headers)
        self.assertNotIn("authorization", request.headers)

    def test_api_key_is_used_as_bearer_when_no_token(self) -> None:
        self.server.enqueue(data=[])
        client = WazobiaMail(
            api_key="wzbm_only_key", base_url=self.server.base_url, auth_scheme="bearer"
        )
        client.domains.list()
        self.assertEqual(
            self.server.last.headers["authorization"], "Bearer wzbm_only_key"
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
