"""Client configuration and credential resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Optional

from .errors import WazobiaAuthenticationError

DEFAULT_BASE_URL = "https://app.wazobiamail.com/api/v1"
DEFAULT_TIMEOUT = 30.0
SDK_VERSION = "0.1.0"
DEFAULT_USER_AGENT = f"wazobiamail-python/{SDK_VERSION}"

_AUTH_SCHEMES = {"header", "bearer", "both"}


@dataclass(frozen=True)
class ClientConfig:
    """Resolved, immutable client configuration."""

    api_key: Optional[str] = None
    access_token: Optional[str] = None
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    auth_scheme: str = "header"
    headers: Mapping[str, str] = field(default_factory=dict)
    user_agent: str = DEFAULT_USER_AGENT

    def masked_api_key(self) -> str:
        return mask_secret(self.api_key)

    def masked_access_token(self) -> str:
        return mask_secret(self.access_token)


def mask_secret(value: Optional[str]) -> str:
    """Return a safe, non-reversible representation for logs and reprs."""

    if not value:
        return "***"
    if len(value) <= 8:
        return "***"
    return f"{value[:5]}...{value[-4:]}"


def _first_env(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def resolve_config(
    api_key: Optional[str] = None,
    *,
    access_token: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[float] = None,
    auth_scheme: Optional[str] = None,
    headers: Optional[Mapping[str, str]] = None,
    user_agent: Optional[str] = None,
    allow_unauthenticated: bool = False,
) -> ClientConfig:
    """Validate options, apply environment fallbacks and return a config object."""

    resolved_key = (api_key or "").strip() or _first_env(
        "WAZOBIA_API_KEY", "WAZOBIAMAIL_API_KEY"
    )
    resolved_token = (access_token or "").strip() or _first_env(
        "WAZOBIA_ACCESS_TOKEN", "WAZOBIAMAIL_ACCESS_TOKEN"
    )

    if not resolved_key and not resolved_token and not allow_unauthenticated:
        raise WazobiaAuthenticationError(
            "Missing WazobiaMail credentials. Pass api_key=... (or access_token=...), "
            "set WAZOBIA_API_KEY, or pass allow_unauthenticated=True for public endpoints."
        )

    resolved_scheme = (auth_scheme or os.environ.get("WAZOBIA_AUTH_SCHEME") or "").strip().lower()
    if not resolved_scheme:
        if resolved_token and resolved_key:
            resolved_scheme = "both"
        elif resolved_token:
            resolved_scheme = "bearer"
        else:
            resolved_scheme = "header"
    if resolved_scheme not in _AUTH_SCHEMES:
        raise ValueError(
            "auth_scheme must be one of 'header', 'bearer' or 'both'"
        )
    if resolved_scheme in {"header", "both"} and not resolved_key and not allow_unauthenticated:
        raise WazobiaAuthenticationError(
            "The selected auth_scheme requires an API key (X-API-Key)."
        )
    if resolved_scheme in {"bearer", "both"} and not resolved_token:
        if resolved_key:
            resolved_token = resolved_key
        elif not allow_unauthenticated:
            raise WazobiaAuthenticationError(
                "The selected auth_scheme requires an access token (Authorization: Bearer)."
            )

    resolved_base_url = (
        base_url or os.environ.get("WAZOBIA_BASE_URL") or DEFAULT_BASE_URL
    ).strip()
    resolved_base_url = resolved_base_url.rstrip("/")
    if not resolved_base_url.startswith(("http://", "https://")):
        raise ValueError("base_url must start with http:// or https://")

    if timeout is None:
        raw_timeout = os.environ.get("WAZOBIA_TIMEOUT")
        if raw_timeout:
            try:
                timeout = float(raw_timeout)
            except ValueError as exc:
                raise ValueError("WAZOBIA_TIMEOUT must be a number of seconds") from exc
    resolved_timeout = DEFAULT_TIMEOUT if timeout is None else float(timeout)
    if resolved_timeout <= 0:
        raise ValueError("timeout must be greater than zero seconds")

    return ClientConfig(
        api_key=resolved_key,
        access_token=resolved_token,
        base_url=resolved_base_url,
        timeout=resolved_timeout,
        auth_scheme=resolved_scheme,
        headers=dict(headers or {}),
        user_agent=(user_agent or DEFAULT_USER_AGENT).strip(),
    )


__all__ = [
    "ClientConfig",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "SDK_VERSION",
    "DEFAULT_USER_AGENT",
    "resolve_config",
    "mask_secret",
]
