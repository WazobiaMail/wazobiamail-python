"""Billing invoices and subscriptions."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import quote

from ..http import BinaryResult
from ..models import (
    ApiResponse,
    Currency,
    Invoice,
    Page,
    Subscription,
    normalize,
)
from .base import Resource, parse_page


class BillingResource(Resource):
    """Read invoices, download invoice PDFs and inspect subscriptions."""

    def list_invoices(
        self, *, timeout: Optional[float] = None
    ) -> ApiResponse[Page[Invoice]]:
        return self._request(
            "GET",
            "/billing/invoices",
            timeout=timeout,
            parser=parse_page(Invoice, "items"),
        )

    def get_invoice(
        self, invoice_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Optional[Invoice]]:
        return self._request(
            "GET",
            f"/billing/invoices/{quote(str(invoice_id), safe='')}",
            timeout=timeout,
            parser=lambda data: (
                Invoice.from_dict(normalize(data).get("invoice"))
                if isinstance(normalize(data).get("invoice"), dict)
                else None
            ),
        )

    def download_invoice(
        self, invoice_id: str, *, timeout: Optional[float] = None
    ) -> BinaryResult:
        """Download an account-owned invoice PDF."""

        return self._binary(
            f"/billing/invoices/{quote(str(invoice_id), safe='')}/download",
            timeout=timeout,
        )

    def get_current_subscription(
        self,
        *,
        product: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Optional[Subscription]]:
        def parser(data: Any) -> Optional[Subscription]:
            value = normalize(data).get("subscription")
            return Subscription.from_dict(value) if isinstance(value, dict) else None

        return self._request(
            "GET",
            "/subscriptions/current",
            params={"product": product},
            timeout=timeout,
            parser=parser,
        )

    def detect_currency(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Currency]:
        """Detect the pricing currency from the request's edge country headers."""

        return self._request(
            "GET",
            "/payments/currency",
            timeout=timeout,
            parser=lambda data: Currency.from_dict(data),
        )

    def create_invoice(
        self,
        amount: float,
        *,
        currency: str,
        status: str = "open",
        timeout: Optional[float] = None,
    ) -> ApiResponse[Dict[str, Any]]:
        """Create a custom invoice (billing invoice write permission).

        The upstream contract accepts only ``amount``, ``currency`` and
        ``status``; the status must be ``open``.
        """

        body: Dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "status": status,
        }
        return self._request(
            "POST",
            "/billing/invoices",
            json_body=body,
            timeout=timeout,
        )


__all__ = ["BillingResource"]
