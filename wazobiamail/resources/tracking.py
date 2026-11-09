"""Tracked outbound messages and engagement events."""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote

from ..models import ApiResponse, TrackingDetail, TrackingList, normalize
from .base import Resource


class TrackingResource(Resource):
    """Read tracked messages, delivery events, opens and clicks.

    These endpoints require a paid subscription; otherwise the API returns
    HTTP 403 (``WazobiaForbiddenError``).
    """

    def list(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[TrackingList]:
        """List tracked messages with open/click counters and a summary.

        ``from_date``/``to_date`` are inclusive calendar dates (``YYYY-MM-DD``).
        """

        return self._request(
            "GET",
            "/sending/tracking/messages",
            params={
                "limit": limit,
                "offset": offset,
                "status": status,
                "from": from_date,
                "to": to_date,
            },
            timeout=timeout,
            parser=lambda data: TrackingList.from_dict(data),
        )

    def get(
        self, tracking_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[TrackingDetail]:
        """Read one tracked message and its full event timeline."""

        return self._request(
            "GET",
            f"/sending/tracking/messages/{quote(str(tracking_id), safe='')}",
            timeout=timeout,
            parser=lambda data: TrackingDetail.from_dict(
                normalize(data).get("message") or {}
            ),
        )


__all__ = ["TrackingResource"]
