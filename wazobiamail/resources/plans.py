"""Subscription plans and effective account limits."""

from __future__ import annotations

from typing import Optional

from ..models import ApiResponse, EffectiveLimits, Page, Plan, normalize
from .base import Resource, parse_page


class PlansResource(Resource):
    """Read the public plan catalog and the account's effective limits."""

    def list(
        self,
        *,
        product: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Page[Plan]]:
        return self._request(
            "GET",
            "/plans",
            params={"product": product},
            timeout=timeout,
            parser=parse_page(Plan, "items"),
        )

    def get_effective_limits(
        self, *, timeout: Optional[float] = None
    ) -> ApiResponse[EffectiveLimits]:
        def _parse_limits(data: object) -> EffectiveLimits:
            norm = normalize(data) if isinstance(data, dict) else {}
            nested = norm.get("limits")
            if isinstance(nested, dict):
                return EffectiveLimits.from_dict(nested)
            return EffectiveLimits.from_dict(norm)

        return self._request(
            "GET",
            "/plans/effective",
            timeout=timeout,
            parser=_parse_limits,
        )


__all__ = ["PlansResource"]
