"""Official WazobiaMail Python SDK.

Zero-dependency, synchronous client for the WazobiaMail SaaS API.

Example:
    >>> from wazobiamail import WazobiaMail
    >>> client = WazobiaMail(api_key="wzbm_live_...")
    >>> receipt = client.messages.send(
    ...     to="customer@example.com",
    ...     sender="Acme <hello@mail.example.com>",
    ...     subject="Your order shipped",
    ...     html="<p>On its way!</p>",
    ... )
    >>> receipt.data.status
    'queued'
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from .config import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    SDK_VERSION,
    ClientConfig,
    mask_secret,
    resolve_config,
)
from .errors import (
    WazobiaApiError,
    WazobiaAuthenticationError,
    WazobiaConflictError,
    WazobiaConnectionError,
    WazobiaError,
    WazobiaForbiddenError,
    WazobiaNotFoundError,
    WazobiaRateLimitError,
    WazobiaServerError,
    WazobiaTimeoutError,
    WazobiaValidationError,
    WazobiaWebhookError,
)
from .http import BinaryResult, FileUpload, HttpClient, HttpResult, prepare_file
from .models import (
    Account,
    AccountStatus,
    ApiKey,
    ApiResponse,
    AuthPayload,
    CreatedApiKey,
    CreatedMailbox,
    CreatedMailboxCredential,
    Currency,
    DnsRecord,
    Domain,
    DomainDns,
    DomainVerification,
    EffectiveLimits,
    EmailLog,
    EmailLogs,
    Invoice,
    LedgerEntry,
    Mailbox,
    MailboxConnection,
    MailboxCredential,
    MailboxMessageDetail,
    MailboxMessageSummary,
    MailboxMessagesPage,
    MailboxStorage,
    Page,
    Pagination,
    Plan,
    PurchaseUnitsResult,
    SendResult,
    SmtpAccess,
    SmtpRelay,
    SpamCheckResult,
    SpamFinding,
    SpamRule,
    Subscription,
    SupportTicket,
    SupportTicketCreated,
    SupportTicketPage,
    Template,
    TemplatePage,
    TemplatePreview,
    TrackingDetail,
    TrackingList,
    TrackingMessage,
    UnitPack,
    UnitsSummary,
    UploadedFile,
)
from .resources import (
    ApiKeysResource,
    AuthResource,
    BillingResource,
    DomainsResource,
    MailboxesResource,
    MessagesResource,
    PlansResource,
    SmtpAccessResource,
    SmtpRelaysResource,
    StatusResource,
    SupportResource,
    TemplatesResource,
    TrackingResource,
    UnitsResource,
    WebhooksResource,
)


class WazobiaMail:
    """Synchronous WazobiaMail API client.

    Args:
        api_key: Scoped sending API key (``wzbm_...``). Falls back to
            ``WAZOBIA_API_KEY`` / ``WAZOBIAMAIL_API_KEY``.
        access_token: Account access token from ``auth.login``. Falls back to
            ``WAZOBIA_ACCESS_TOKEN`` / ``WAZOBIAMAIL_ACCESS_TOKEN``.
        base_url: API root, default ``https://app.wazobiamail.com/api/v1``.
        timeout: Request timeout in seconds (default 30).
        auth_scheme: ``header`` (X-API-Key), ``bearer`` (Authorization) or
            ``both``. Inferred from the supplied credentials when omitted.
        headers: Extra headers sent on every request.
        user_agent: Override the default SDK user agent.
        allow_unauthenticated: Permit construction without credentials for
            public endpoints such as the plan catalog.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        access_token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        auth_scheme: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        user_agent: Optional[str] = None,
        allow_unauthenticated: bool = False,
    ) -> None:
        self._config = resolve_config(
            api_key,
            access_token=access_token,
            base_url=base_url,
            timeout=timeout,
            auth_scheme=auth_scheme,
            headers=headers,
            user_agent=user_agent,
            allow_unauthenticated=allow_unauthenticated,
        )
        self._http = HttpClient(self._config)

        self.auth = AuthResource(self._http)
        self.messages = MessagesResource(self._http)
        self.emails = self.messages
        self.domains = DomainsResource(self._http)
        self.mailboxes = MailboxesResource(self._http)
        self.api_keys = ApiKeysResource(self._http)
        self.smtp_relays = SmtpRelaysResource(self._http)
        self.smtp_access = SmtpAccessResource(self._http)
        self.billing = BillingResource(self._http)
        self.units = UnitsResource(self._http)
        self.plans = PlansResource(self._http)
        self.status = StatusResource(self._http)
        self.support = SupportResource(self._http)
        self.templates = TemplatesResource(self._http)
        self.tracking = TrackingResource(self._http)
        self.webhooks = WebhooksResource()

    @property
    def config(self) -> ClientConfig:
        """The resolved, immutable client configuration."""

        return self._config

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def send(self, message: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> ApiResponse[SendResult]:
        """Shortcut for :meth:`messages.send`."""

        return self.messages.send(message, **kwargs)

    def close(self) -> None:
        """Release client resources.

        The client uses one short-lived HTTP connection per request, so there
        is nothing persistent to close. Provided for context-manager symmetry.
        """

    def __enter__(self) -> "WazobiaMail":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def to_dict(self) -> Dict[str, Any]:
        """Return a log-safe representation with credentials masked."""

        return {
            "base_url": self._config.base_url,
            "api_key": mask_secret(self._config.api_key),
            "access_token": mask_secret(self._config.access_token),
            "auth_scheme": self._config.auth_scheme,
            "timeout": self._config.timeout,
        }

    def __repr__(self) -> str:
        return (
            f"WazobiaMail(base_url={self._config.base_url!r}, "
            f"api_key={mask_secret(self._config.api_key)!r}, "
            f"access_token={mask_secret(self._config.access_token)!r})"
        )


Wazobia = WazobiaMail

__version__ = SDK_VERSION

__all__ = [
    "WazobiaMail",
    "Wazobia",
    "__version__",
    # Configuration and transport
    "ClientConfig",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USER_AGENT",
    "SDK_VERSION",
    "mask_secret",
    "HttpClient",
    "HttpResult",
    "BinaryResult",
    "FileUpload",
    "prepare_file",
    # Resources
    "AuthResource",
    "MessagesResource",
    "DomainsResource",
    "MailboxesResource",
    "ApiKeysResource",
    "SmtpRelaysResource",
    "SmtpAccessResource",
    "BillingResource",
    "UnitsResource",
    "PlansResource",
    "StatusResource",
    "SupportResource",
    "TemplatesResource",
    "TrackingResource",
    "WebhooksResource",
    # Errors
    "WazobiaError",
    "WazobiaConnectionError",
    "WazobiaTimeoutError",
    "WazobiaApiError",
    "WazobiaAuthenticationError",
    "WazobiaForbiddenError",
    "WazobiaNotFoundError",
    "WazobiaConflictError",
    "WazobiaValidationError",
    "WazobiaRateLimitError",
    "WazobiaServerError",
    "WazobiaWebhookError",
    # Models
    "ApiResponse",
    "Page",
    "Pagination",
    "Account",
    "AuthPayload",
    "SendResult",
    "UploadedFile",
    "SpamCheckResult",
    "SpamFinding",
    "SpamRule",
    "TrackingMessage",
    "TrackingDetail",
    "TrackingList",
    "EmailLog",
    "EmailLogs",
    "Domain",
    "DnsRecord",
    "DomainDns",
    "DomainVerification",
    "ApiKey",
    "CreatedApiKey",
    "Mailbox",
    "MailboxCredential",
    "CreatedMailbox",
    "CreatedMailboxCredential",
    "MailboxStorage",
    "MailboxConnection",
    "MailboxMessageSummary",
    "MailboxMessageDetail",
    "MailboxMessagesPage",
    "SmtpRelay",
    "SmtpAccess",
    "Plan",
    "EffectiveLimits",
    "Invoice",
    "Subscription",
    "Currency",
    "UnitsSummary",
    "UnitPack",
    "LedgerEntry",
    "PurchaseUnitsResult",
    "AccountStatus",
    "SupportTicket",
    "SupportTicketPage",
    "SupportTicketCreated",
    "Template",
    "TemplatePage",
    "TemplatePreview",
]
