"""Email units, credit packs, ledger history and purchases."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..models import (
    ApiResponse,
    LedgerEntry,
    Page,
    PurchaseUnitsResult,
    UnitPack,
    UnitsSummary,
)
from .base import Resource, parse_items, parse_page


class UnitsResource(Resource):
    """Inspect email credit balances and buy additional units."""

    def summary(self, *, timeout: Optional[float] = None) -> ApiResponse[UnitsSummary]:
        """Return the account's included and purchased email-unit balance."""

        return self._request(
            "GET",
            "/units/summary",
            timeout=timeout,
            parser=lambda data: UnitsSummary.from_dict(data),
        )

    def packs(self, *, timeout: Optional[float] = None) -> ApiResponse[List[UnitPack]]:
        """List active email-credit purchase packs."""

        return self._request(
            "GET",
            "/units/packs",
            timeout=timeout,
            parser=parse_items(UnitPack, "items"),
        )

    def ledger(
        self,
        *,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        descending: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Page[LedgerEntry]]:
        """List email-unit ledger entries, newest first.

        ``status`` filters by ledger source (for example ``purchase`` or
        ``usage``) because the upstream query reuses the status parameter.
        """

        return self._request(
            "GET",
            "/units/ledger",
            params={
                "page": page,
                "perPage": per_page,
                "status": status,
                "search": search,
                "sort": sort,
                "descending": descending,
            },
            timeout=timeout,
            parser=parse_page(LedgerEntry, "items"),
        )

    def purchase(
        self,
        pack_id: Optional[str] = None,
        *,
        currency: str = "NGN",
        units: Optional[int] = None,
        plan_id: Optional[str] = None,
        billing_interval: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[PurchaseUnitsResult]:
        """Create a pending invoice for an email-unit purchase.

        Supply ``pack_id`` to buy a catalog pack, or ``units`` for a variable
        quantity. Accounts without an active paid subscription must also pass
        ``plan_id`` (and optionally ``billing_interval``).
        """

        body: Dict[str, Any] = {"currency": currency}
        if pack_id is not None:
            body["packId"] = pack_id
        if units is not None:
            body["units"] = units
        if plan_id is not None:
            body["planId"] = plan_id
        if billing_interval is not None:
            body["billingInterval"] = billing_interval

        return self._request(
            "POST",
            "/units/purchases",
            json_body=body,
            timeout=timeout,
            parser=lambda data: PurchaseUnitsResult.from_dict(data),
        )

    # Ergonomic aliases
    get_summary = summary
    get_packs = packs
    get_ledger = ledger



__all__ = ["UnitsResource"]
