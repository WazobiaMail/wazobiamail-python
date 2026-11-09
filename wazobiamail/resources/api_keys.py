"""Scoped sending API keys."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import quote

from ..models import ApiResponse, ApiKey, CreatedApiKey, normalize
from .base import Resource, parse_items


def _parse_created_key(data: Any) -> CreatedApiKey:
    if not isinstance(data, Mapping):
        return CreatedApiKey()
    d = normalize(data)
    inner = d.get("api_key") or d.get("key")
    if isinstance(inner, Mapping):
        return CreatedApiKey.from_dict(inner)
    return CreatedApiKey.from_dict(data)


class ApiKeysResource(Resource):
    """Create, rotate and revoke sending API keys.

    The secret ``api_key`` value is only present on create/regenerate responses.
    """

    def list(self, *, timeout: Optional[float] = None) -> ApiResponse[List[ApiKey]]:
        return self._request(
            "GET",
            "/sending/api-keys",
            timeout=timeout,
            parser=parse_items(ApiKey, "items"),
        )

    def create(
        self,
        name: str,
        *,
        scope: Optional[str] = None,
        domain_id: Optional[str] = None,
        expires_at: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[CreatedApiKey]:
        body: Dict[str, Any] = {"name": name}
        if scope is not None:
            body["scope"] = scope
        if domain_id is not None:
            body["domainId"] = domain_id
        if expires_at is not None:
            body["expiresAt"] = expires_at
        return self._request(
            "POST",
            "/sending/api-keys",
            json_body=body,
            timeout=timeout,
            parser=_parse_created_key,
        )

    def regenerate(
        self, key_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[CreatedApiKey]:
        return self._request(
            "POST",
            f"/sending/api-keys/{quote(str(key_id), safe='')}/regenerate",
            timeout=timeout,
            parser=_parse_created_key,
        )

    def revoke(
        self, key_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "POST",
            f"/sending/api-keys/{quote(str(key_id), safe='')}/revoke",
            timeout=timeout,
        )


__all__ = ["ApiKeysResource"]
