"""Sending domains, DNS records and Cloudflare DNS automation."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import quote

from ..models import (
    ApiResponse,
    Domain,
    DomainDns,
    DomainVerification,
    normalize,
)
from .base import Resource, parse_items, parse_one


def _domain_id(value: str) -> str:
    return quote(str(value), safe="")


class CloudflareResource(Resource):
    """Cloudflare DNS connection endpoints for sending domains."""

    def status(
        self,
        *,
        domain_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "GET",
            "/sending/domains/cloudflare/status",
            params={"domainId": domain_id},
            timeout=timeout,
        )

    def connect(
        self,
        *,
        domain_id: Optional[str] = None,
        return_to: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "GET",
            "/sending/domains/cloudflare/connect",
            params={"domainId": domain_id, "returnTo": return_to},
            timeout=timeout,
        )

    def sync(
        self, domain_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "POST",
            "/sending/domains/cloudflare/sync",
            json_body={"domainId": domain_id},
            timeout=timeout,
        )

    def disconnect(
        self,
        *,
        domain_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "DELETE",
            "/sending/domains/cloudflare/disconnect",
            params={"domain_id": domain_id},
            send_json=False,
            timeout=timeout,
        )


class DomainsResource(Resource):
    """Register and verify domains used for outbound sending."""

    def __init__(self, http: Any) -> None:
        super().__init__(http)
        self.cloudflare = CloudflareResource(http)

    def list(
        self, *, timeout: Optional[float] = None
    ) -> ApiResponse[List[Domain]]:
        return self._request(
            "GET",
            "/sending/domains",
            timeout=timeout,
            parser=parse_items(Domain, "items"),
        )

    def get(
        self, domain_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Optional[Domain]]:
        return self._request(
            "GET",
            f"/sending/domains/{_domain_id(domain_id)}",
            timeout=timeout,
            parser=parse_one(Domain, "domain"),
        )

    def create(
        self,
        domain: str,
        *,
        is_default: Optional[bool] = None,
        use_root_domain: Optional[bool] = None,
        host_inboxes_on_main_domain: Optional[bool] = None,
        sending_subdomain: Optional[str] = None,
        mail_mode: Optional[str] = None,
        create_default_inboxes: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Optional[Domain]]:
        body: Dict[str, Any] = {"domain": domain}
        if is_default is not None:
            body["is_default"] = is_default
        if use_root_domain is not None:
            body["use_root_domain"] = use_root_domain
        if host_inboxes_on_main_domain is not None:
            body["host_inboxes_on_main_domain"] = host_inboxes_on_main_domain
        if sending_subdomain is not None:
            body["sending_subdomain"] = sending_subdomain
        if mail_mode is not None:
            body["mail_mode"] = mail_mode
        if create_default_inboxes is not None:
            body["create_default_inboxes"] = create_default_inboxes

        return self._request(
            "POST",
            "/sending/domains",
            json_body=body,
            timeout=timeout,
            parser=parse_one(Domain, "domain"),
        )

    def update(
        self,
        domain_id: str,
        *,
        domain: Optional[str] = None,
        is_default: Optional[bool] = None,
        use_root_domain: Optional[bool] = None,
        mail_mode: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Optional[Domain]]:
        body: Dict[str, Any] = {}
        if domain is not None:
            body["domain"] = domain
        if is_default is not None:
            body["is_default"] = is_default
        if use_root_domain is not None:
            body["use_root_domain"] = use_root_domain
        if mail_mode is not None:
            body["mail_mode"] = mail_mode

        return self._request(
            "PATCH",
            f"/sending/domains/{_domain_id(domain_id)}",
            json_body=body,
            timeout=timeout,
            parser=parse_one(Domain, "domain"),
        )

    def delete(
        self, domain_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "DELETE",
            f"/sending/domains/{_domain_id(domain_id)}",
            send_json=False,
            timeout=timeout,
        )

    def get_dns_records(
        self, domain_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[DomainDns]:
        return self._request(
            "GET",
            f"/sending/domains/{_domain_id(domain_id)}/dns-records",
            timeout=timeout,
            parser=lambda data: DomainDns.from_dict(
                normalize(data).get("domain")
                if isinstance(normalize(data).get("domain"), Mapping)
                else data
            ),
        )

    def get_mail_dns(
        self, domain_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "GET",
            f"/sending/domains/{_domain_id(domain_id)}/mail-dns",
            timeout=timeout,
        )

    def verify(
        self,
        domain_id: str,
        *,
        force: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[DomainVerification]:
        return self._request(
            "POST",
            f"/sending/domains/{_domain_id(domain_id)}/verify",
            json_body={} if force is None else {"force": force},
            timeout=timeout,
            parser=lambda data: DomainVerification.from_dict(
                normalize(data).get("verification")
                if isinstance(normalize(data).get("verification"), Mapping)
                else data
            ),
        )


    def refresh_dns(
        self,
        domain_id: str,
        *,
        force: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[DomainVerification]:
        return self._request(
            "POST",
            f"/sending/domains/{_domain_id(domain_id)}/dns-refresh",
            json_body={} if force is None else {"force": force},
            timeout=timeout,
            parser=lambda data: DomainVerification.from_dict(
                normalize(data).get("verification") or {}
            ),
        )

    def detect_dns_provider(
        self, domain: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Dict[str, Any]]:
        return self._request(
            "GET",
            "/sending/domains/dns-provider",
            params={"domain": domain},
            timeout=timeout,
        )


__all__ = ["DomainsResource", "CloudflareResource"]
