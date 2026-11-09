"""HTTP error mapping and exception compatibility tests."""

from __future__ import annotations

import unittest

from wazobiamail import (
    WazobiaApiError,
    WazobiaAuthenticationError,
    WazobiaConflictError,
    WazobiaForbiddenError,
    WazobiaNotFoundError,
    WazobiaRateLimitError,
    WazobiaServerError,
    WazobiaValidationError,
)
from wazobiamail.errors import WazobiaError

try:
    from ._server import MockServerTestCase
except ImportError:  # pragma: no cover
    from _server import MockServerTestCase


class TestErrorMapping(MockServerTestCase):
    def _fail(self, status: int, message: str, **kwargs):
        self.server.enqueue_error(status, message, **kwargs)
        return self.make_client().domains.list()

    def test_authentication_error(self) -> None:
        with self.assertRaises(WazobiaAuthenticationError) as caught:
            self._fail(401, "Invalid API key or token has expired")
        error = caught.exception
        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.message, "Invalid API key or token has expired")
        self.assertIn("HTTP 401", str(error))

    def test_forbidden_error_includes_code_and_request_id(self) -> None:
        self.server.enqueue_error(
            403,
            "Enterprise plan required",
            code="plan_upgrade_required",
            headers={"X-Request-Id": "req_abc123"},
        )
        with self.assertRaises(WazobiaForbiddenError) as caught:
            self.make_client().mailboxes.messages.list("mbx_1")
        error = caught.exception
        self.assertEqual(error.status_code, 403)
        self.assertEqual(error.code, "plan_upgrade_required")
        self.assertEqual(error.request_id, "req_abc123")
        self.assertEqual(error.response_headers["x-request-id"], "req_abc123")

    def test_not_found_error(self) -> None:
        with self.assertRaises(WazobiaNotFoundError) as caught:
            self._fail(404, "We could not find that item")
        self.assertEqual(caught.exception.status_code, 404)

    def test_conflict_error(self) -> None:
        with self.assertRaises(WazobiaConflictError) as caught:
            self._fail(409, "Domain already exists")
        self.assertEqual(caught.exception.status_code, 409)

    def test_validation_error_for_422(self) -> None:
        with self.assertRaises(WazobiaValidationError) as caught:
            self._fail(422, "Please check the details you entered")
        self.assertEqual(caught.exception.status_code, 422)

    def test_validation_error_for_400_with_field_errors(self) -> None:
        with self.assertRaises(WazobiaValidationError) as caught:
            self._fail(
                400,
                "Please check the details you entered",
                errors={"domain": "Invalid domain name"},
            )
        self.assertEqual(caught.exception.errors, {"domain": "Invalid domain name"})

    def test_generic_400_without_field_errors(self) -> None:
        with self.assertRaises(WazobiaApiError) as caught:
            self._fail(400, "Create an API key before sending")
        self.assertNotIsInstance(caught.exception, WazobiaValidationError)
        self.assertEqual(caught.exception.status_code, 400)

    def test_rate_limit_error_parses_retry_after(self) -> None:
        self.server.enqueue_error(
            429,
            "Rate limit exceeded",
            headers={"Retry-After": "37"},
        )
        with self.assertRaises(WazobiaRateLimitError) as caught:
            self.make_client().domains.list()
        self.assertEqual(caught.exception.retry_after, 37)
        self.assertEqual(caught.exception.status_code, 429)

    def test_rate_limit_without_retry_after_header(self) -> None:
        self.server.enqueue_error(429, "Too many requests")
        with self.assertRaises(WazobiaRateLimitError) as caught:
            self.make_client().domains.list()
        self.assertIsNone(caught.exception.retry_after)

    def test_server_error_for_5xx(self) -> None:
        with self.assertRaises(WazobiaServerError) as caught:
            self._fail(503, "This service is temporarily unavailable")
        self.assertEqual(caught.exception.status_code, 503)

    def test_success_false_in_http_200_envelope_raises(self) -> None:
        self.server.enqueue(success=False, data=None, message="Background failure")
        with self.assertRaises(WazobiaApiError) as caught:
            self.make_client().domains.list()
        self.assertEqual(caught.exception.status_code, 200)
        self.assertEqual(caught.exception.message, "Background failure")

    def test_error_without_message_uses_fallback(self) -> None:
        self.server.enqueue(
            500,
            raw_body=b'{"success":false,"data":null}',
        )
        with self.assertRaises(WazobiaServerError) as caught:
            self.make_client().domains.list()
        self.assertIn("500", str(caught.exception))

    def test_error_inherits_from_wazobia_error(self) -> None:
        with self.assertRaises(WazobiaError):
            self._fail(404, "missing")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
