"""Typed response models for the WazobiaMail API.

The API uses camelCase on the wire. Public properties on these models are
idiomatic snake_case, and parsing also accepts legacy snake_case keys from
older servers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Mapping, Optional, TypeVar

T = TypeVar("T")

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])([A-Z])")


def snake_case(name: str) -> str:
    """Convert a camelCase, PascalCase or acronym-prefixed API field to snake_case."""

    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return _CAMEL_BOUNDARY.sub(r"_\1", first_pass).lower()


def normalize(data: Any) -> Dict[str, Any]:
    """Return a copy of an API object that also aliases camelCase keys to snake_case."""

    if not isinstance(data, Mapping):
        return {}
    result = dict(data)
    for key, value in data.items():
        if isinstance(key, str):
            alias = snake_case(key)
            result.setdefault(alias, value)
    return result


def _get(data: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return default


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return value if isinstance(value, str) else str(value)


def _optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value if isinstance(value, str) else str(value)


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


@dataclass
class Pagination:
    page: int = 1
    page_size: int = 0
    total_items: int = 0
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "Pagination":
        d = normalize(data)
        model = cls(
            page=_int(_get(d, "page"), 1),
            page_size=_int(_get(d, "page_size", "pageSize"), 0),
            total_items=_int(_get(d, "total_items", "totalItems"), 0),
            total_pages=_int(_get(d, "total_pages", "totalPages"), 0),
            has_next=_bool(_get(d, "has_next", "hasNext"), False),
            has_prev=_bool(_get(d, "has_prev", "hasPrev"), False),
        )
        model.raw = d
        return model


@dataclass
class Page(Generic[T]):
    """A collection plus optional pagination metadata."""

    items: List[T] = field(default_factory=list)
    pagination: Optional[Pagination] = None


@dataclass
class ApiResponse(Generic[T]):
    """The canonical WazobiaMail response envelope.

    ``data`` is parsed into the resource's typed model (or a list/page), while
    ``raw`` keeps the complete decoded envelope for forward compatibility.
    """

    success: bool
    message: str
    data: T
    status_code: int = 200
    headers: Mapping[str, str] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def request_id(self) -> Optional[str]:
        for key, value in self.headers.items():
            if key.lower() == "x-request-id":
                return value
        return None

    def __bool__(self) -> bool:
        return bool(self.success)


@dataclass
class AuthPayload:
    account_id: int = 0
    email: str = ""
    username: Optional[str] = None
    name: Optional[str] = None
    plan_id: str = ""
    selected_plan_id: str = ""
    saas_role: str = ""
    auth_provider: str = ""
    access_token: str = field(default="", repr=False)
    refresh_token: str = field(default="", repr=False)
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "AuthPayload":
        d = normalize(data)
        model = cls(
            account_id=_int(_get(d, "account_id", "accountId")),
            email=_text(_get(d, "email")),
            username=_optional_text(_get(d, "username")),
            name=_optional_text(_get(d, "name")),
            plan_id=_text(_get(d, "plan_id", "planId")),
            selected_plan_id=_text(_get(d, "selected_plan_id", "selectedPlanId")),
            saas_role=_text(_get(d, "saas_role", "saasRole")),
            auth_provider=_text(_get(d, "auth_provider", "authProvider")),
            access_token=_text(_get(d, "access_token", "accessToken")),
            refresh_token=_text(_get(d, "refresh_token", "refreshToken")),
        )
        model.raw = d
        return model


@dataclass
class Account:
    account_id: int = 0
    email: str = ""
    username: Optional[str] = None
    name: Optional[str] = None
    plan_id: str = ""
    selected_plan_id: str = ""
    saas_role: str = ""
    auth_provider: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "Account":
        d = normalize(data)
        model = cls(
            account_id=_int(_get(d, "account_id", "accountId")),
            email=_text(_get(d, "email")),
            username=_optional_text(_get(d, "username")),
            name=_optional_text(_get(d, "name")),
            plan_id=_text(_get(d, "plan_id", "planId")),
            selected_plan_id=_text(_get(d, "selected_plan_id", "selectedPlanId")),
            saas_role=_text(_get(d, "saas_role", "saasRole")),
            auth_provider=_text(_get(d, "auth_provider", "authProvider")),
        )
        model.raw = d
        return model


@dataclass
class SendResult:
    status: str = ""
    tracking_id: Optional[str] = None
    recipients: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SendResult":
        d = normalize(data)
        model = cls(
            status=_text(_get(d, "status")),
            tracking_id=_optional_text(_get(d, "tracking_id", "trackingId")),
            recipients=_int(_get(d, "recipients")),
        )
        model.raw = d
        return model


@dataclass
class UploadedFile:
    file_name: str = ""
    content_type: Optional[str] = None
    size_bytes: int = 0
    public_url: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "UploadedFile":
        d = normalize(data)
        model = cls(
            file_name=_text(_get(d, "file_name", "fileName")),
            content_type=_optional_text(_get(d, "content_type", "contentType")),
            size_bytes=_int(_get(d, "size_bytes", "sizeBytes")),
            public_url=_optional_text(_get(d, "public_url", "publicUrl")),
        )
        model.raw = d
        return model


@dataclass
class SpamFinding:
    rule: str = ""
    score: float = 0.0
    description: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SpamFinding":
        d = normalize(data)
        model = cls(
            rule=_text(_get(d, "rule", "code", "name")),
            score=_float(_get(d, "score", "points")),
            description=_text(_get(d, "description", "title")),
        )
        model.raw = d
        return model


@dataclass
class SpamRule:
    code: str = ""
    points: float = 0.0
    title: str = ""
    description: str = ""
    recommendation: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SpamRule":
        d = normalize(data)
        model = cls(
            code=_text(_get(d, "code", "rule")),
            points=_float(_get(d, "points", "score")),
            title=_text(_get(d, "title", "description")),
            description=_text(_get(d, "description")),
            recommendation=_text(_get(d, "recommendation")),
        )
        model.raw = d
        return model


@dataclass
class SpamCheckResult:
    score: float = 0.0
    threshold: float = 0.0
    is_spam: bool = False
    rating: str = ""
    badge_color: str = ""
    deliverability_score: int = 0
    summary: str = ""
    rules: List[SpamRule] = field(default_factory=list)
    findings: List[SpamFinding] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SpamCheckResult":
        d = normalize(data)
        raw_rules = _list(_get(d, "rules"))
        raw_findings = _list(_get(d, "findings"))
        if not raw_findings and raw_rules:
            findings = [SpamFinding.from_dict(item) for item in raw_rules]
        else:
            findings = [SpamFinding.from_dict(item) for item in raw_findings]

        if not raw_rules and raw_findings:
            rules = [SpamRule.from_dict(item) for item in raw_findings]
        else:
            rules = [SpamRule.from_dict(item) for item in raw_rules]

        raw_recs = _list(_get(d, "recommendations"))
        recs = [str(r) for r in raw_recs if r is not None]

        model = cls(
            score=_float(_get(d, "score")),
            threshold=_float(_get(d, "threshold")),
            is_spam=_bool(_get(d, "is_spam", "isSpam")),
            rating=_text(_get(d, "rating")),
            badge_color=_text(_get(d, "badge_color", "badgeColor")),
            deliverability_score=_int(_get(d, "deliverability_score", "deliverabilityScore")),
            summary=_text(_get(d, "summary")),
            rules=rules,
            findings=findings,
            recommendations=recs,
        )
        model.raw = d
        return model


@dataclass
class TrackingMessage:
    tracking_id: str = ""
    sender_domain: str = ""
    subject: Optional[str] = None
    recipients_count: int = 0
    accepted_count: int = 0
    delivered_count: int = 0
    bounced_count: int = 0
    open_count: int = 0
    opens_count: int = 0
    click_count: int = 0
    clicks_count: int = 0
    status: str = ""
    created_at: Optional[str] = None
    last_opened_at: Optional[str] = None
    last_clicked_at: Optional[str] = None
    last_delivery_event_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "TrackingMessage":
        d = normalize(data)
        opens = _int(_get(d, "opens_count", "opensCount", "open_count", "openCount"))
        clicks = _int(_get(d, "clicks_count", "clicksCount", "click_count", "clickCount"))
        model = cls(
            tracking_id=_text(_get(d, "tracking_id", "trackingId")),
            sender_domain=_text(_get(d, "sender_domain", "senderDomain")),
            subject=_optional_text(_get(d, "subject")),
            recipients_count=_int(_get(d, "recipients_count", "recipientsCount")),
            accepted_count=_int(_get(d, "accepted_count", "acceptedCount")),
            delivered_count=_int(_get(d, "delivered_count", "deliveredCount")),
            bounced_count=_int(_get(d, "bounced_count", "bouncedCount")),
            open_count=opens,
            opens_count=opens,
            click_count=clicks,
            clicks_count=clicks,
            status=_text(_get(d, "status")),
            created_at=_optional_text(
                _get(d, "created_at", "createdAt", "sent_at", "sentAt")
            ),
            last_opened_at=_optional_text(_get(d, "last_opened_at", "lastOpenedAt")),
            last_clicked_at=_optional_text(_get(d, "last_clicked_at", "lastClickedAt")),
            last_delivery_event_at=_optional_text(
                _get(d, "last_delivery_event_at", "lastDeliveryEventAt")
            ),
        )
        model.raw = d
        return model


@dataclass
class TrackingEvent:
    id: str = ""
    event_type: str = ""
    recipient_email: Optional[str] = None
    click_url: Optional[str] = None
    occurred_at: Optional[str] = None
    engagement: Any = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "TrackingEvent":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            event_type=_text(_get(d, "event_type", "eventType")),
            recipient_email=_optional_text(_get(d, "recipient_email", "recipientEmail")),
            click_url=_optional_text(_get(d, "click_url", "clickUrl")),
            occurred_at=_optional_text(_get(d, "occurred_at", "occurredAt")),
            engagement=_get(d, "engagement"),
        )
        model.raw = d
        return model


@dataclass
class TrackingSummary:
    messages: int = 0
    recipients: int = 0
    accepted: int = 0
    delivered: int = 0
    bounced: int = 0
    opens: int = 0
    clicks: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "TrackingSummary":
        d = normalize(data)
        model = cls(
            messages=_int(_get(d, "messages")),
            recipients=_int(_get(d, "recipients")),
            accepted=_int(_get(d, "accepted")),
            delivered=_int(_get(d, "delivered")),
            bounced=_int(_get(d, "bounced")),
            opens=_int(_get(d, "opens")),
            clicks=_int(_get(d, "clicks")),
        )
        model.raw = d
        return model


@dataclass
class TrackingDetail:
    message: Optional[TrackingMessage] = None
    events: List[TrackingEvent] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "TrackingDetail":
        d = normalize(data)
        message = _get(d, "message")
        model = cls(
            message=TrackingMessage.from_dict(message) if isinstance(message, Mapping) else None,
            events=[TrackingEvent.from_dict(item) for item in _list(_get(d, "events"))],
        )
        model.raw = d
        return model


@dataclass
class TrackingList:
    messages: List[TrackingMessage] = field(default_factory=list)
    items: List[TrackingMessage] = field(default_factory=list)
    total: int = 0
    summary: Optional[TrackingSummary] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "TrackingList":
        d = normalize(data)
        summary = _get(d, "summary")
        raw_items = _list(_get(d, "items", "messages"))
        items = [TrackingMessage.from_dict(item) for item in raw_items]
        total = _int(_get(d, "total"), len(items))
        model = cls(
            messages=items,
            items=items,
            total=total,
            summary=TrackingSummary.from_dict(summary) if isinstance(summary, Mapping) else None,
        )
        model.raw = d
        return model


@dataclass
class EmailLog:
    account_id: int = 0
    tracking_id: str = ""
    subject: Optional[str] = None
    sender_domain: str = ""
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    method: str = ""
    to: List[str] = field(default_factory=list)
    cc: List[str] = field(default_factory=list)
    received_at: Optional[str] = None
    status: Optional[str] = None
    recipients_count: int = 0
    delivered_count: int = 0
    bounced_count: int = 0
    diagnostic: Optional[str] = None
    events: List[Any] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "EmailLog":
        d = normalize(data)
        model = cls(
            account_id=_int(_get(d, "account_id", "accountId")),
            tracking_id=_text(_get(d, "tracking_id", "trackingId")),
            subject=_optional_text(_get(d, "subject")),
            sender_domain=_text(_get(d, "sender_domain", "senderDomain")),
            from_address=_optional_text(_get(d, "from")),
            from_name=_optional_text(_get(d, "from_name", "fromName")),
            method=_text(_get(d, "method")),
            to=[_text(item) for item in _list(_get(d, "to"))],
            cc=[_text(item) for item in _list(_get(d, "cc"))],
            received_at=_optional_text(_get(d, "received_at", "receivedAt")),
            status=_optional_text(_get(d, "status")),
            recipients_count=_int(_get(d, "recipients_count", "recipientsCount")),
            delivered_count=_int(_get(d, "delivered_count", "deliveredCount")),
            bounced_count=_int(_get(d, "bounced_count", "bouncedCount")),
            diagnostic=_optional_text(_get(d, "diagnostic")),
            events=_list(_get(d, "events")),
        )
        model.raw = d
        return model


@dataclass
class EmailLogs:
    available: bool = False
    messages: List[EmailLog] = field(default_factory=list)
    has_more: bool = False
    event_details_available: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "EmailLogs":
        d = normalize(data)
        model = cls(
            available=_bool(_get(d, "available")),
            messages=[EmailLog.from_dict(item) for item in _list(_get(d, "messages"))],
            has_more=_bool(_get(d, "has_more", "hasMore")),
            event_details_available=_bool(
                _get(d, "event_details_available", "eventDetailsAvailable")
            ),
        )
        model.raw = d
        return model


@dataclass
class Domain:
    id: str = ""
    account_id: int = 0
    domain: str = ""
    requested_domain: Optional[str] = None
    verification_status: str = ""
    status: str = ""
    verified: bool = False
    is_default: bool = False
    domain_role: str = ""
    parent_domain_id: Optional[str] = None
    create_default_inboxes: bool = False
    mail_mode: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @property
    def is_verified(self) -> bool:
        return self.verified

    @classmethod
    def from_dict(cls, data: Any) -> "Domain":
        d = normalize(data)
        verification_status = _text(
            _get(d, "verification_status", "verificationStatus")
        )
        status = _text(_get(d, "status"))
        verified_val = _get(d, "verified", "is_verified", "isVerified")
        verified = (
            _bool(verified_val, False)
            if verified_val is not None
            else (
                verification_status.lower() in ("verified", "active")
                or status.lower() in ("verified", "active")
            )
        )
        model = cls(
            id=_text(_get(d, "id")),
            account_id=_int(_get(d, "account_id", "accountId")),
            domain=_text(_get(d, "domain")),
            requested_domain=_optional_text(_get(d, "requested_domain", "requestedDomain")),
            verification_status=verification_status or status,
            status=status or verification_status,
            verified=verified,
            is_default=_bool(_get(d, "is_default", "isDefault")),
            domain_role=_text(_get(d, "domain_role", "domainRole")),
            parent_domain_id=_optional_text(_get(d, "parent_domain_id", "parentDomainId")),
            create_default_inboxes=_bool(
                _get(d, "create_default_inboxes", "createDefaultInboxes")
            ),
            mail_mode=_text(_get(d, "mail_mode", "mailMode")),
            created_at=_optional_text(_get(d, "created_at", "createdAt")),
            updated_at=_optional_text(_get(d, "updated_at", "updatedAt")),
        )
        model.raw = d
        return model


@dataclass
class DnsRecord:
    id: str = ""
    record_type: str = ""
    host: str = ""
    value: str = ""
    ttl: int = 0
    status: str = ""
    last_checked_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "DnsRecord":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            record_type=_text(_get(d, "record_type", "recordType", "type")),
            host=_text(_get(d, "host", "name")),
            value=_text(_get(d, "value", "content")),
            ttl=_int(_get(d, "ttl")),
            status=_text(_get(d, "status")),
            last_checked_at=_optional_text(_get(d, "last_checked_at", "lastCheckedAt")),
        )
        model.raw = d
        return model


@dataclass
class DomainDns:
    provisioning: bool = False
    domain_id: str = ""
    domain: str = ""
    verification_status: str = ""
    records: List[DnsRecord] = field(default_factory=list)
    copy_block: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "DomainDns":
        d = normalize(data)
        model = cls(
            provisioning=_bool(_get(d, "provisioning")),
            domain_id=_text(_get(d, "domain_id", "domainId")),
            domain=_text(_get(d, "domain")),
            verification_status=_text(_get(d, "verification_status", "verificationStatus")),
            records=[DnsRecord.from_dict(item) for item in _list(_get(d, "records"))],
            copy_block=_text(_get(d, "copy_block", "copyBlock")),
        )
        model.raw = d
        return model


@dataclass
class VerificationCheck:
    record_type: str = ""
    host: str = ""
    expected_value: str = ""
    matched: bool = False
    observed_values: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "VerificationCheck":
        d = normalize(data)
        model = cls(
            record_type=_text(_get(d, "record_type", "recordType")),
            host=_text(_get(d, "host")),
            expected_value=_text(_get(d, "expected_value", "expectedValue")),
            matched=_bool(_get(d, "matched")),
            observed_values=[
                _text(item) for item in _list(_get(d, "observed_values", "observedValues"))
            ],
        )
        model.raw = d
        return model


@dataclass
class DomainVerification:
    domain_id: str = ""
    domain: str = ""
    verification_status: str = ""
    verified_count: int = 0
    pending_count: int = 0
    checks: List[VerificationCheck] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @property
    def verified(self) -> bool:
        return self.verification_status == "verified" or bool(self.raw.get("verified"))

    @classmethod
    def from_dict(cls, data: Any) -> "DomainVerification":
        d = normalize(data)
        model = cls(
            domain_id=_text(_get(d, "domain_id", "domainId")),
            domain=_text(_get(d, "domain")),
            verification_status=_text(_get(d, "verification_status", "verificationStatus")),
            verified_count=_int(_get(d, "verified_count", "verifiedCount")),
            pending_count=_int(_get(d, "pending_count", "pendingCount")),
            checks=[VerificationCheck.from_dict(item) for item in _list(_get(d, "checks"))],
        )
        model.raw = d
        return model



@dataclass
class ApiKey:
    id: str = ""
    name: str = ""
    scope: str = ""
    domain_id: Optional[str] = None
    domain: Optional[str] = None
    key_prefix: str = ""
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None
    created_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "ApiKey":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            name=_text(_get(d, "name")),
            scope=_text(_get(d, "scope")),
            domain_id=_optional_text(_get(d, "domain_id", "domainId")),
            domain=_optional_text(_get(d, "domain")),
            key_prefix=_text(_get(d, "key_prefix", "keyPrefix")),
            last_used_at=_optional_text(_get(d, "last_used_at", "lastUsedAt")),
            expires_at=_optional_text(_get(d, "expires_at", "expiresAt")),
            revoked_at=_optional_text(_get(d, "revoked_at", "revokedAt")),
            created_at=_optional_text(_get(d, "created_at", "createdAt")),
        )
        model.raw = d
        return model


@dataclass
class CreatedApiKey:
    id: str = ""
    name: str = ""
    scope: str = ""
    domain_id: Optional[str] = None
    key_prefix: str = ""
    api_key: str = field(default="", repr=False)
    expires_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "CreatedApiKey":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            name=_text(_get(d, "name")),
            scope=_text(_get(d, "scope")),
            domain_id=_optional_text(_get(d, "domain_id", "domainId")),
            key_prefix=_text(_get(d, "key_prefix", "keyPrefix")),
            api_key=_text(_get(d, "api_key", "apiKey")),
            expires_at=_optional_text(_get(d, "expires_at", "expiresAt")),
        )
        model.raw = d
        return model


@dataclass
class Mailbox:
    id: str = ""
    domain_id: str = ""
    address: str = ""
    email: str = ""
    local_part: str = ""
    display_name: Optional[str] = None
    status: str = ""
    storage_usage_bytes: int = 0
    is_platform_subdomain: bool = False
    auto_provisioned: bool = False
    role: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "Mailbox":
        d = normalize(data)
        addr = _text(_get(d, "address", "email"))
        model = cls(
            id=_text(_get(d, "id")),
            domain_id=_text(_get(d, "domain_id", "domainId")),
            address=addr,
            email=addr,
            local_part=_text(_get(d, "local_part", "localPart")),
            display_name=_optional_text(_get(d, "display_name", "displayName")),
            status=_text(_get(d, "status")),
            storage_usage_bytes=_int(
                _get(d, "storage_usage_bytes", "storageUsageBytes")
            ),
            is_platform_subdomain=_bool(
                _get(d, "is_platform_subdomain", "isPlatformSubdomain")
            ),
            auto_provisioned=_bool(_get(d, "auto_provisioned", "autoProvisioned")),
            role=_text(_get(d, "role")),
            created_at=_optional_text(_get(d, "created_at", "createdAt")),
            updated_at=_optional_text(_get(d, "updated_at", "updatedAt")),
        )
        model.raw = d
        return model


@dataclass
class MailboxCredential:
    id: str = ""
    mailbox_id: str = ""
    username: str = ""
    password: Optional[str] = field(default=None, repr=False)
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None
    created_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "MailboxCredential":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            mailbox_id=_text(_get(d, "mailbox_id", "mailboxId")),
            username=_text(_get(d, "username")),
            password=_optional_text(_get(d, "password")),
            expires_at=_optional_text(_get(d, "expires_at", "expiresAt")),
            revoked_at=_optional_text(_get(d, "revoked_at", "revokedAt")),
            created_at=_optional_text(_get(d, "created_at", "createdAt")),
        )
        model.raw = d
        return model


@dataclass
class CreatedMailboxCredential:
    credential: Optional[MailboxCredential] = None
    password: str = field(default="", repr=False)
    id: str = ""
    username: str = ""
    created_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "CreatedMailboxCredential":
        d = normalize(data)
        credential = _get(d, "credential")
        cred_obj = (
            MailboxCredential.from_dict(credential)
            if isinstance(credential, Mapping)
            else (
                MailboxCredential.from_dict(d)
                if ("username" in d or "id" in d)
                else None
            )
        )
        pwd = _text(_get(d, "password"))
        if not pwd and isinstance(credential, Mapping):
            pwd = _text(_get(credential, "password"))
        model = cls(
            credential=cred_obj,
            password=pwd,
            id=_text(_get(d, "id")) or (cred_obj.id if cred_obj else ""),
            username=_text(_get(d, "username"))
            or (cred_obj.username if cred_obj else ""),
            created_at=_optional_text(_get(d, "created_at", "createdAt"))
            or (cred_obj.created_at if cred_obj else None),
        )
        model.raw = d
        return model


@dataclass
class CreatedMailbox:
    mailbox: Optional[Mailbox] = None
    credential: Optional[CreatedMailboxCredential] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "CreatedMailbox":
        d = normalize(data)
        mailbox = _get(d, "mailbox")
        credential = _get(d, "credential")
        model = cls(
            mailbox=Mailbox.from_dict(mailbox) if isinstance(mailbox, Mapping) else None,
            credential=CreatedMailboxCredential.from_dict(credential)
            if isinstance(credential, Mapping)
            else None,
        )
        model.raw = d
        return model


@dataclass
class MailboxStoragePlan:
    mailbox_limit: int = 0
    base_mailbox_limit: int = 0
    additional_mailbox_limit: int = 0
    mailboxes_used: int = 0
    mailbox_remaining: Optional[int] = None
    storage_total_bytes: Optional[int] = None
    storage_allocated_bytes: int = 0
    storage_remaining_bytes: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "MailboxStoragePlan":
        d = normalize(data)
        model = cls(
            mailbox_limit=_int(_get(d, "mailbox_limit", "mailboxLimit")),
            base_mailbox_limit=_int(_get(d, "base_mailbox_limit", "baseMailboxLimit")),
            additional_mailbox_limit=_int(
                _get(d, "additional_mailbox_limit", "additionalMailboxLimit")
            ),
            mailboxes_used=_int(_get(d, "mailboxes_used", "mailboxesUsed")),
            mailbox_remaining=_optional_int(_get(d, "mailbox_remaining", "mailboxRemaining")),
            storage_total_bytes=_optional_int(
                _get(d, "storage_total_bytes", "storageTotalBytes")
            ),
            storage_allocated_bytes=_int(
                _get(d, "storage_allocated_bytes", "storageAllocatedBytes")
            ),
            storage_remaining_bytes=_optional_int(
                _get(d, "storage_remaining_bytes", "storageRemainingBytes")
            ),
        )
        model.raw = d
        return model


@dataclass
class MailboxStorage:
    mailboxes: List[Dict[str, Any]] = field(default_factory=list)
    customers: List[Dict[str, Any]] = field(default_factory=list)
    domains: List[Dict[str, Any]] = field(default_factory=list)
    measurement: str = ""
    plan: Optional[MailboxStoragePlan] = None
    total_bytes: int = 0
    quota_bytes: int = 0
    percent_used: float = 0.0
    mailboxes_count: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "MailboxStorage":
        d = normalize(data)
        plan = _get(d, "plan")
        mailboxes_list = [_dict(item) for item in _list(_get(d, "mailboxes"))]
        model = cls(
            mailboxes=mailboxes_list,
            customers=[_dict(item) for item in _list(_get(d, "customers"))],
            domains=[_dict(item) for item in _list(_get(d, "domains"))],
            measurement=_text(_get(d, "measurement")),
            plan=MailboxStoragePlan.from_dict(plan) if isinstance(plan, Mapping) else None,
            total_bytes=_int(_get(d, "total_bytes", "totalBytes")),
            quota_bytes=_int(_get(d, "quota_bytes", "quotaBytes")),
            percent_used=_float(_get(d, "percent_used", "percentUsed")),
            mailboxes_count=_int(
                _get(d, "mailboxes_count", "mailboxesCount", default=len(mailboxes_list))
            ),
        )
        model.raw = d
        return model



@dataclass
class MailboxConnection:
    mailbox_id: str = ""
    domain_id: str = ""
    username: str = ""
    status: str = ""
    smtp: Dict[str, Any] = field(default_factory=dict)
    imap: Dict[str, Any] = field(default_factory=dict)
    pop3: Dict[str, Any] = field(default_factory=dict)
    authentication: str = ""
    password_hint: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "MailboxConnection":
        d = normalize(data)
        model = cls(
            mailbox_id=_text(_get(d, "mailbox_id", "mailboxId")),
            domain_id=_text(_get(d, "domain_id", "domainId")),
            username=_text(_get(d, "username")),
            status=_text(_get(d, "status")),
            smtp=_dict(_get(d, "smtp")),
            imap=_dict(_get(d, "imap")),
            pop3=_dict(_get(d, "pop3")),
            authentication=_text(_get(d, "authentication")),
            password_hint=_text(_get(d, "password_hint", "passwordHint")),
        )
        model.raw = d
        return model


@dataclass
class EmailAddress:
    name: Optional[str] = None
    email: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "EmailAddress":
        if isinstance(data, str):
            model = cls(email=data)
            model.raw = {"email": data}
            return model
        d = normalize(data)
        model = cls(name=_optional_text(_get(d, "name")), email=_text(_get(d, "email")))
        model.raw = d
        return model


@dataclass
class AttachmentMetadata:
    blob_id: str = ""
    name: str = ""
    content_type: str = ""
    size: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "AttachmentMetadata":
        d = normalize(data)
        model = cls(
            blob_id=_text(_get(d, "blob_id", "blobId")),
            name=_text(_get(d, "name", "file_name", "fileName")),
            content_type=_text(_get(d, "content_type", "contentType", "type")),
            size=_int(_get(d, "size", "size_bytes", "sizeBytes")),
        )
        model.raw = d
        return model


@dataclass
class MailboxMessageSummary:
    id: str = ""
    thread_id: Optional[str] = None
    from_: List[EmailAddress] = field(default_factory=list)
    to: List[EmailAddress] = field(default_factory=list)
    subject: Optional[str] = None
    preview: Optional[str] = None
    received_at: Optional[str] = None
    is_unread: bool = False
    has_attachments: bool = False
    size_bytes: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "MailboxMessageSummary":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            thread_id=_optional_text(_get(d, "thread_id", "threadId")),
            from_=[EmailAddress.from_dict(item) for item in _list(_get(d, "from", "from_"))],
            to=[EmailAddress.from_dict(item) for item in _list(_get(d, "to"))],
            subject=_optional_text(_get(d, "subject")),
            preview=_optional_text(_get(d, "preview")),
            received_at=_optional_text(_get(d, "received_at", "receivedAt")),
            is_unread=_bool(_get(d, "is_unread", "isUnread")),
            has_attachments=_bool(_get(d, "has_attachments", "hasAttachments")),
            size_bytes=_int(_get(d, "size_bytes", "sizeBytes")),
        )
        model.raw = d
        return model


@dataclass
class MailboxMessageDetail:
    id: str = ""
    thread_id: Optional[str] = None
    from_: List[EmailAddress] = field(default_factory=list)
    to: List[EmailAddress] = field(default_factory=list)
    cc: List[EmailAddress] = field(default_factory=list)
    bcc: List[EmailAddress] = field(default_factory=list)
    reply_to: List[EmailAddress] = field(default_factory=list)
    subject: Optional[str] = None
    preview: Optional[str] = None
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    attachments: List[AttachmentMetadata] = field(default_factory=list)
    received_at: Optional[str] = None
    is_unread: bool = False
    size_bytes: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "MailboxMessageDetail":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            thread_id=_optional_text(_get(d, "thread_id", "threadId")),
            from_=[EmailAddress.from_dict(item) for item in _list(_get(d, "from", "from_"))],
            to=[EmailAddress.from_dict(item) for item in _list(_get(d, "to"))],
            cc=[EmailAddress.from_dict(item) for item in _list(_get(d, "cc"))],
            bcc=[EmailAddress.from_dict(item) for item in _list(_get(d, "bcc"))],
            reply_to=[
                EmailAddress.from_dict(item)
                for item in _list(_get(d, "reply_to", "replyTo"))
            ],
            subject=_optional_text(_get(d, "subject")),
            preview=_optional_text(_get(d, "preview")),
            text_body=_optional_text(_get(d, "text_body", "textBody")),
            html_body=_optional_text(_get(d, "html_body", "htmlBody")),
            attachments=[
                AttachmentMetadata.from_dict(item) for item in _list(_get(d, "attachments"))
            ],
            received_at=_optional_text(_get(d, "received_at", "receivedAt")),
            is_unread=_bool(_get(d, "is_unread", "isUnread")),
            size_bytes=_int(_get(d, "size_bytes", "sizeBytes")),
        )
        model.raw = d
        return model


@dataclass
class MailboxMessagesPage:
    items: List[MailboxMessageSummary] = field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "MailboxMessagesPage":
        d = normalize(data)
        model = cls(
            items=[
                MailboxMessageSummary.from_dict(item) for item in _list(_get(d, "items"))
            ],
            total=_int(_get(d, "total")),
            page=_int(_get(d, "page"), 1),
            limit=_int(_get(d, "limit")),
        )
        model.raw = d
        return model


@dataclass
class SmtpRelay:
    id: str = ""
    account_id: int = 0
    name: str = ""
    smtp_host: str = ""
    smtp_port: int = 0
    smtp_username: str = ""
    smtp_security: str = ""
    status: str = ""
    is_default: bool = False
    has_password: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SmtpRelay":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            account_id=_int(_get(d, "account_id", "accountId")),
            name=_text(_get(d, "name")),
            smtp_host=_text(_get(d, "smtp_host", "smtpHost")),
            smtp_port=_int(_get(d, "smtp_port", "smtpPort")),
            smtp_username=_text(_get(d, "smtp_username", "smtpUsername")),
            smtp_security=_text(_get(d, "smtp_security", "smtpSecurity")),
            status=_text(_get(d, "status")),
            is_default=_bool(_get(d, "is_default", "isDefault")),
            has_password=_bool(_get(d, "has_password", "hasPassword")),
            created_at=_optional_text(_get(d, "created_at", "createdAt")),
            updated_at=_optional_text(_get(d, "updated_at", "updatedAt")),
        )
        model.raw = d
        return model


@dataclass
class SmtpConnection:
    host: str = ""
    port: int = 0
    security: str = ""
    usernames: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SmtpConnection":
        d = normalize(data)
        model = cls(
            host=_text(_get(d, "host")),
            port=_int(_get(d, "port")),
            security=_text(_get(d, "security")),
            usernames=[_text(item) for item in _list(_get(d, "usernames"))],
        )
        model.raw = d
        return model


@dataclass
class SmtpAccess:
    paid: bool = False
    eligible: bool = False
    enabled: bool = False
    persona: Optional[str] = None
    configured: bool = False
    connection: Optional[SmtpConnection] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SmtpAccess":
        d = normalize(data)
        connection = _get(d, "connection")
        model = cls(
            paid=_bool(_get(d, "paid")),
            eligible=_bool(_get(d, "eligible")),
            enabled=_bool(_get(d, "enabled")),
            persona=_optional_text(_get(d, "persona")),
            configured=_bool(_get(d, "configured")),
            connection=SmtpConnection.from_dict(connection)
            if isinstance(connection, Mapping)
            else None,
        )
        model.raw = d
        return model


@dataclass
class Plan:
    id: str = ""
    name: str = ""
    usd_price: float = 0.0
    naira_price: float = 0.0
    yearly_usd_price: Optional[float] = None
    yearly_naira_price: Optional[float] = None
    interval_prices: Any = None
    hourly_quota: int = 0
    daily_quota: int = 0
    monthly_quota: int = 0
    send_rate_limit_per_minute: int = 0
    data_retention_days: int = 0
    features: Any = None
    limits: Any = None
    overage_usd_per_1000: float = 0.0
    dedicated_ip_addon_usd: float = 0.0
    status: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "Plan":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            name=_text(_get(d, "name")),
            usd_price=_float(_get(d, "usd_price", "usdPrice")),
            naira_price=_float(_get(d, "naira_price", "nairaPrice")),
            yearly_usd_price=(
                None
                if _get(d, "yearly_usd_price", "yearlyUsdPrice") is None
                else _float(_get(d, "yearly_usd_price", "yearlyUsdPrice"))
            ),
            yearly_naira_price=(
                None
                if _get(d, "yearly_naira_price", "yearlyNairaPrice") is None
                else _float(_get(d, "yearly_naira_price", "yearlyNairaPrice"))
            ),
            interval_prices=_get(d, "interval_prices", "intervalPrices"),
            hourly_quota=_int(_get(d, "hourly_quota", "hourlyQuota")),
            daily_quota=_int(_get(d, "daily_quota", "dailyQuota")),
            monthly_quota=_int(_get(d, "monthly_quota", "monthlyQuota")),
            send_rate_limit_per_minute=_int(
                _get(d, "send_rate_limit_per_minute", "sendRateLimitPerMinute")
            ),
            data_retention_days=_int(_get(d, "data_retention_days", "dataRetentionDays")),
            features=_get(d, "features"),
            limits=_get(d, "limits"),
            overage_usd_per_1000=_float(
                _get(d, "overage_usd_per_1000", "overageUsdPer1000")
            ),
            dedicated_ip_addon_usd=_float(
                _get(d, "dedicated_ip_addon_usd", "dedicatedIpAddonUsd")
            ),
            status=_text(_get(d, "status")),
        )
        model.raw = d
        return model


@dataclass
class EffectiveLimits:
    account_id: int = 0
    plan_id: str = ""
    send_rate_limit_per_minute: int = 0
    mailbox_ops_per_minute: int = 0
    mailbox_limit: int = 0
    base_mailbox_limit: int = 0
    additional_mailbox_limit: int = 0
    custom_domain_sending_enabled: bool = False
    domain_limit: int = 0
    receiving_enabled: bool = False
    mailbox_storage_gb: int = 0
    plan_name: str = ""
    can_send: bool = False
    can_receive: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "EffectiveLimits":
        d = normalize(data)
        plan_id = _text(_get(d, "plan_id", "planId"))
        custom_domain = _bool(
            _get(d, "custom_domain_sending_enabled", "customDomainSendingEnabled")
        )
        receiving = _bool(_get(d, "receiving_enabled", "receivingEnabled"))
        model = cls(
            account_id=_int(_get(d, "account_id", "accountId")),
            plan_id=plan_id,
            send_rate_limit_per_minute=_int(
                _get(d, "send_rate_limit_per_minute", "sendRateLimitPerMinute")
            ),
            mailbox_ops_per_minute=_int(
                _get(d, "mailbox_ops_per_minute", "mailboxOpsPerMinute")
            ),
            mailbox_limit=_int(_get(d, "mailbox_limit", "mailboxLimit")),
            base_mailbox_limit=_int(_get(d, "base_mailbox_limit", "baseMailboxLimit")),
            additional_mailbox_limit=_int(
                _get(d, "additional_mailbox_limit", "additionalMailboxLimit")
            ),
            custom_domain_sending_enabled=custom_domain,
            domain_limit=_int(_get(d, "domain_limit", "domainLimit")),
            receiving_enabled=receiving,
            mailbox_storage_gb=_int(_get(d, "mailbox_storage_gb", "mailboxStorageGb")),
            plan_name=_text(_get(d, "plan_name", "planName")) or plan_id,
            can_send=_bool(_get(d, "can_send", "canSend", default=custom_domain)),
            can_receive=_bool(_get(d, "can_receive", "canReceive", default=receiving)),
        )
        model.raw = d
        return model



@dataclass
class Invoice:
    id: str = ""
    account_id: int = 0
    amount: float = 0.0
    currency: str = ""
    status: str = ""
    purpose: str = ""
    metadata: Any = None
    due_date: Optional[str] = None
    paid_at: Optional[str] = None
    created_at: Optional[str] = None
    invoice_number: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "Invoice":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            account_id=_int(_get(d, "account_id", "accountId")),
            amount=_float(_get(d, "amount")),
            currency=_text(_get(d, "currency")),
            status=_text(_get(d, "status")),
            purpose=_text(_get(d, "purpose")),
            metadata=_get(d, "metadata"),
            due_date=_optional_text(_get(d, "due_date", "dueDate")),
            paid_at=_optional_text(_get(d, "paid_at", "paidAt")),
            created_at=_optional_text(_get(d, "created_at", "createdAt")),
            invoice_number=_text(_get(d, "invoice_number", "invoiceNumber", default=_get(d, "id"))),
        )
        model.raw = d
        return model



@dataclass
class SubscriptionPlanSummary:
    id: str = ""
    name: str = ""
    usd_price: float = 0.0
    naira_price: float = 0.0
    monthly_quota: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SubscriptionPlanSummary":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            name=_text(_get(d, "name")),
            usd_price=_float(_get(d, "usd_price", "usdPrice")),
            naira_price=_float(_get(d, "naira_price", "nairaPrice")),
            monthly_quota=_int(_get(d, "monthly_quota", "monthlyQuota")),
        )
        model.raw = d
        return model


@dataclass
class Subscription:
    id: str = ""
    account_id: int = 0
    plan_id: str = ""
    status: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    auto_renew: bool = False
    billing_interval: str = ""
    plan: Optional[SubscriptionPlanSummary] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "Subscription":
        d = normalize(data)
        plan = _get(d, "plan")
        model = cls(
            id=_text(_get(d, "id")),
            account_id=_int(_get(d, "account_id", "accountId")),
            plan_id=_text(_get(d, "plan_id", "planId")),
            status=_text(_get(d, "status")),
            start_date=_optional_text(_get(d, "start_date", "startDate")),
            end_date=_optional_text(_get(d, "end_date", "endDate")),
            auto_renew=_bool(_get(d, "auto_renew", "autoRenew")),
            billing_interval=_text(_get(d, "billing_interval", "billingInterval")),
            plan=SubscriptionPlanSummary.from_dict(plan)
            if isinstance(plan, Mapping)
            else None,
        )
        model.raw = d
        return model


@dataclass
class Currency:
    country: str = ""
    currency: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "Currency":
        d = normalize(data)
        model = cls(country=_text(_get(d, "country")), currency=_text(_get(d, "currency")))
        model.raw = d
        return model


@dataclass
class UnitsSummary:
    included_allowance: int = 0
    included_used: int = 0
    included_remaining: int = 0
    purchased_balance: int = 0
    unlimited: bool = False
    can_buy_credits: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @property
    def balance(self) -> int:
        return self.purchased_balance or self.included_remaining or _int(self.raw.get("balance", 0))

    @classmethod
    def from_dict(cls, data: Any) -> "UnitsSummary":
        d = normalize(data)
        model = cls(
            included_allowance=_int(_get(d, "included_allowance", "includedAllowance")),
            included_used=_int(_get(d, "included_used", "includedUsed")),
            included_remaining=_int(_get(d, "included_remaining", "includedRemaining")),
            purchased_balance=_int(
                _get(d, "purchased_balance", "purchasedBalance", default=_get(d, "balance", default=0))
            ),
            unlimited=_bool(_get(d, "unlimited")),
            can_buy_credits=_bool(_get(d, "can_buy_credits", "canBuyCredits")),
        )
        model.raw = d
        return model



@dataclass
class UnitPack:
    id: str = ""
    name: str = ""
    description: str = ""
    units: int = 0
    price_ngn_minor: int = 0
    price_usd_minor: int = 0
    is_active: bool = False
    sort_order: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "UnitPack":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            name=_text(_get(d, "name")),
            description=_text(_get(d, "description")),
            units=_int(_get(d, "units")),
            price_ngn_minor=_int(_get(d, "price_ngn_minor", "priceNgnMinor")),
            price_usd_minor=_int(_get(d, "price_usd_minor", "priceUsdMinor")),
            is_active=_bool(_get(d, "is_active", "isActive")),
            sort_order=_int(_get(d, "sort_order", "sortOrder")),
        )
        model.raw = d
        return model


@dataclass
class LedgerEntry:
    id: str = ""
    account_id: int = 0
    email: str = ""
    quantity: int = 0
    balance_after: int = 0
    source: str = ""
    reference: Optional[str] = None
    actor_id: Optional[int] = None
    reason: Optional[str] = None
    created_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "LedgerEntry":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            account_id=_int(_get(d, "account_id", "accountId")),
            email=_text(_get(d, "email")),
            quantity=_int(_get(d, "quantity")),
            balance_after=_int(_get(d, "balance_after", "balanceAfter")),
            source=_text(_get(d, "source")),
            reference=_optional_text(_get(d, "reference")),
            actor_id=_optional_int(_get(d, "actor_id", "actorId")),
            reason=_optional_text(_get(d, "reason")),
            created_at=_optional_text(_get(d, "created_at", "createdAt")),
        )
        model.raw = d
        return model


@dataclass
class PurchaseUnitsResult:
    invoice_id: str = ""
    units: int = 0
    amount_minor: int = 0
    credit_amount_minor: int = 0
    service_amount_minor: int = 0
    currency: str = ""
    status: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "PurchaseUnitsResult":
        d = normalize(data)
        model = cls(
            invoice_id=_text(_get(d, "invoice_id", "invoiceId")),
            units=_int(_get(d, "units")),
            amount_minor=_int(_get(d, "amount_minor", "amountMinor")),
            credit_amount_minor=_int(_get(d, "credit_amount_minor", "creditAmountMinor")),
            service_amount_minor=_int(
                _get(d, "service_amount_minor", "serviceAmountMinor")
            ),
            currency=_text(_get(d, "currency")),
            status=_text(_get(d, "status")),
        )
        model.raw = d
        return model


@dataclass
class AccountStatusPlan:
    id: str = ""
    name: str = ""
    status: str = ""
    billing_interval: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    auto_renew: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "AccountStatusPlan":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            name=_text(_get(d, "name")),
            status=_text(_get(d, "status")),
            billing_interval=_text(_get(d, "billing_interval", "billingInterval")),
            start_date=_optional_text(_get(d, "start_date", "startDate")),
            end_date=_optional_text(_get(d, "end_date", "endDate")),
            auto_renew=_bool(_get(d, "auto_renew", "autoRenew")),
        )
        model.raw = d
        return model


@dataclass
class AccountStatusUnits:
    monthly_allocation: int = 0
    subscription_used: int = 0
    subscription_remaining: int = 0
    purchased_balance: int = 0
    total_remaining: int = 0
    unlimited: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "AccountStatusUnits":
        d = normalize(data)
        model = cls(
            monthly_allocation=_int(
                _get(d, "monthly_allocation", "monthlyAllocation")
            ),
            subscription_used=_int(_get(d, "subscription_used", "subscriptionUsed")),
            subscription_remaining=_int(
                _get(d, "subscription_remaining", "subscriptionRemaining")
            ),
            purchased_balance=_int(_get(d, "purchased_balance", "purchasedBalance")),
            total_remaining=_int(_get(d, "total_remaining", "totalRemaining")),
            unlimited=_bool(_get(d, "unlimited")),
        )
        model.raw = d
        return model


@dataclass
class AccountStatus:
    plan: Optional[AccountStatusPlan] = None
    units: Optional[AccountStatusUnits] = None
    status: str = "healthy"
    account_id: str = ""
    email: str = ""
    verified: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "AccountStatus":
        d = normalize(data)
        plan = _get(d, "plan")
        units = _get(d, "units")
        model = cls(
            plan=AccountStatusPlan.from_dict(plan) if isinstance(plan, Mapping) else None,
            units=AccountStatusUnits.from_dict(units) if isinstance(units, Mapping) else None,
            status=_text(_get(d, "status", default="healthy")),
            account_id=_text(_get(d, "account_id", "accountId")),
            email=_text(_get(d, "email")),
            verified=_bool(_get(d, "verified")),
        )
        model.raw = d
        return model



@dataclass
class SupportAttachment:
    id: str = ""
    filename: str = ""
    size_bytes: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SupportAttachment":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            filename=_text(_get(d, "filename")),
            size_bytes=_int(_get(d, "size_bytes", "sizeBytes")),
        )
        model.raw = d
        return model


@dataclass
class SupportMessage:
    id: str = ""
    ticket_id: str = ""
    sender_name: str = ""
    sender_email: str = ""
    message: str = ""
    is_from_staff: bool = False
    content_type: str = ""
    attachments: List[SupportAttachment] = field(default_factory=list)
    created_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SupportMessage":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            ticket_id=_text(_get(d, "ticket_id", "ticketId")),
            sender_name=_text(_get(d, "sender_name", "senderName")),
            sender_email=_text(_get(d, "sender_email", "senderEmail")),
            message=_text(_get(d, "message")),
            is_from_staff=_bool(_get(d, "is_from_staff", "isFromStaff")),
            content_type=_text(_get(d, "content_type", "contentType")),
            attachments=[
                SupportAttachment.from_dict(item)
                for item in _list(_get(d, "attachments"))
            ],
            created_at=_optional_text(_get(d, "created_at", "createdAt")),
        )
        model.raw = d
        return model


@dataclass
class SupportTicket:
    id: str = ""
    account_id: Optional[int] = None
    name: str = ""
    email: str = ""
    subject: str = ""
    domain: Optional[str] = None
    category: str = ""
    priority: str = ""
    status: str = ""
    messages: List[SupportMessage] = field(default_factory=list)
    customer_read_at: Optional[str] = None
    staff_read_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SupportTicket":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            account_id=_optional_int(_get(d, "account_id", "accountId")),
            name=_text(_get(d, "name")),
            email=_text(_get(d, "email")),
            subject=_text(_get(d, "subject")),
            domain=_optional_text(_get(d, "domain")),
            category=_text(_get(d, "category")),
            priority=_text(_get(d, "priority")),
            status=_text(_get(d, "status")),
            messages=[
                SupportMessage.from_dict(item) for item in _list(_get(d, "messages"))
            ],
            customer_read_at=_optional_text(
                _get(d, "customer_read_at", "customerReadAt")
            ),
            staff_read_at=_optional_text(_get(d, "staff_read_at", "staffReadAt")),
            created_at=_optional_text(_get(d, "created_at", "createdAt")),
            updated_at=_optional_text(_get(d, "updated_at", "updatedAt")),
        )
        model.raw = d
        return model


@dataclass
class SupportTicketPage:
    items: List[SupportTicket] = field(default_factory=list)
    total: int = 0
    page: int = 1
    pages: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SupportTicketPage":
        d = normalize(data)
        model = cls(
            items=[SupportTicket.from_dict(item) for item in _list(_get(d, "items"))],
            total=_int(_get(d, "total")),
            page=_int(_get(d, "page"), 1),
            pages=_int(_get(d, "pages")),
        )
        model.raw = d
        return model


@dataclass
class SupportTicketCreated:
    id: str = ""
    ticket_id: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "SupportTicketCreated":
        d = normalize(data)
        model = cls(id=_text(_get(d, "id")), ticket_id=_text(_get(d, "ticket_id", "ticketId")))
        model.raw = d
        return model


@dataclass
class Template:
    id: str = ""
    account_id: Optional[int] = None
    name: str = ""
    slug: str = ""
    channel: str = ""
    category: str = ""
    status: str = ""
    rejection_reason: Optional[str] = None
    subject: str = ""
    body: str = ""
    text_body: str = ""
    meta_template_id: Optional[str] = None
    meta_template_name: Optional[str] = None
    language: str = ""
    components: Any = None
    variables: Any = None
    design: Any = None
    preview_image_url: Optional[str] = None
    is_system: bool = False
    revision: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "Template":
        d = normalize(data)
        model = cls(
            id=_text(_get(d, "id")),
            account_id=_optional_int(_get(d, "account_id", "accountId")),
            name=_text(_get(d, "name")),
            slug=_text(_get(d, "slug")),
            channel=_text(_get(d, "channel")),
            category=_text(_get(d, "category")),
            status=_text(_get(d, "status")),
            rejection_reason=_optional_text(
                _get(d, "rejection_reason", "rejectionReason")
            ),
            subject=_text(_get(d, "subject")),
            body=_text(_get(d, "body")),
            text_body=_text(_get(d, "text_body", "textBody")),
            meta_template_id=_optional_text(
                _get(d, "meta_template_id", "metaTemplateId")
            ),
            meta_template_name=_optional_text(
                _get(d, "meta_template_name", "metaTemplateName")
            ),
            language=_text(_get(d, "language")),
            components=_get(d, "components"),
            variables=_get(d, "variables"),
            design=_get(d, "design"),
            preview_image_url=_optional_text(
                _get(d, "preview_image_url", "previewImageUrl")
            ),
            is_system=_bool(_get(d, "is_system", "isSystem")),
            revision=_int(_get(d, "revision")),
            created_at=_optional_text(_get(d, "created_at", "createdAt")),
            updated_at=_optional_text(_get(d, "updated_at", "updatedAt")),
        )
        model.raw = d
        return model


@dataclass
class TemplatePage:
    items: List[Template] = field(default_factory=list)
    total: int = 0
    limit: int = 0
    offset: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "TemplatePage":
        d = normalize(data)
        model = cls(
            items=[Template.from_dict(item) for item in _list(_get(d, "items"))],
            total=_int(_get(d, "total")),
            limit=_int(_get(d, "limit")),
            offset=_int(_get(d, "offset")),
        )
        model.raw = d
        return model


@dataclass
class TemplatePreview:
    channel: str = ""
    subject: str = ""
    rendered_body: str = ""
    rendered_text: str = ""
    status: str = ""
    can_send: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Any) -> "TemplatePreview":
        d = normalize(data)
        model = cls(
            channel=_text(_get(d, "channel")),
            subject=_text(_get(d, "subject")),
            rendered_body=_text(_get(d, "rendered_body", "renderedBody")),
            rendered_text=_text(_get(d, "rendered_text", "renderedText")),
            status=_text(_get(d, "status")),
            can_send=_bool(_get(d, "can_send", "canSend")),
        )
        model.raw = d
        return model


__all__ = [
    "ApiResponse",
    "Page",
    "Pagination",
    "AuthPayload",
    "Account",
    "SendResult",
    "UploadedFile",
    "SpamFinding",
    "SpamRule",
    "SpamCheckResult",
    "TrackingMessage",
    "TrackingEvent",
    "TrackingSummary",
    "TrackingDetail",
    "TrackingList",
    "EmailLog",
    "EmailLogs",
    "Domain",
    "DnsRecord",
    "DomainDns",
    "VerificationCheck",
    "DomainVerification",
    "ApiKey",
    "CreatedApiKey",
    "Mailbox",
    "MailboxCredential",
    "CreatedMailboxCredential",
    "CreatedMailbox",
    "MailboxStoragePlan",
    "MailboxStorage",
    "MailboxConnection",
    "EmailAddress",
    "AttachmentMetadata",
    "MailboxMessageSummary",
    "MailboxMessageDetail",
    "MailboxMessagesPage",
    "SmtpRelay",
    "SmtpConnection",
    "SmtpAccess",
    "Plan",
    "EffectiveLimits",
    "Invoice",
    "SubscriptionPlanSummary",
    "Subscription",
    "Currency",
    "UnitsSummary",
    "UnitPack",
    "LedgerEntry",
    "PurchaseUnitsResult",
    "AccountStatusPlan",
    "AccountStatusUnits",
    "AccountStatus",
    "SupportAttachment",
    "SupportMessage",
    "SupportTicket",
    "SupportTicketPage",
    "SupportTicketCreated",
    "Template",
    "TemplatePage",
    "TemplatePreview",
    "snake_case",
    "normalize",
]
