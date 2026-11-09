"""Webhook signature verification helpers.

WazobiaMail signs webhook deliveries with HMAC-SHA256 over the raw request
body. Always verify the exact bytes you received, before parsing JSON.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict, Mapping, Union

from ..errors import WazobiaWebhookError

Payload = Union[str, bytes, bytearray]
SIGNATURE_HEADER = "X-Wazobia-Signature"


def _bytes(value: Payload) -> bytes:
    return value.encode("utf-8") if isinstance(value, str) else bytes(value)


def _signature_digest(signature: str) -> str:
    digest = signature.strip()
    if digest.lower().startswith("sha256="):
        digest = digest.split("=", 1)[1].strip()
    return digest


class WebhooksResource:
    """Verify HMAC signatures and decode webhook events.

    This resource performs no network requests.
    """

    signature_header = SIGNATURE_HEADER

    def sign(self, payload: Payload, secret: Union[str, bytes]) -> str:
        """Return the lowercase hex HMAC-SHA256 signature for a payload."""

        if not secret:
            raise WazobiaWebhookError("A webhook signing secret is required")
        return hmac.new(
            _bytes(secret), _bytes(payload), hashlib.sha256
        ).hexdigest()

    def verify_signature(
        self, payload: Payload, signature: str, secret: Union[str, bytes]
    ) -> bool:
        """Return ``True`` when the signature matches the raw payload.

        A leading ``sha256=`` prefix is accepted. Empty signatures or secrets
        never verify.
        """

        if not signature or not secret:
            return False
        expected = self.sign(payload, secret)
        provided = _signature_digest(signature)
        return hmac.compare_digest(expected, provided)

    def construct_event(
        self, payload: Payload, signature: str, secret: Union[str, bytes]
    ) -> Dict[str, Any]:
        """Verify then decode a webhook body into a JSON object.

        Raises:
            WazobiaWebhookError: if the signature is invalid or the body is not
                a JSON object.
        """

        if not self.verify_signature(payload, signature, secret):
            raise WazobiaWebhookError("Invalid webhook signature")
        try:
            decoded = json.loads(_bytes(payload).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WazobiaWebhookError("Invalid JSON webhook payload") from exc
        if not isinstance(decoded, Mapping):
            raise WazobiaWebhookError("Webhook payload must be a JSON object")
        return dict(decoded)


__all__ = ["WebhooksResource", "SIGNATURE_HEADER"]
