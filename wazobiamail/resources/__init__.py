"""Resource classes exposed by :class:`wazobiamail.WazobiaMail`."""

from .api_keys import ApiKeysResource
from .auth import AuthResource
from .base import Resource
from .billing import BillingResource
from .domains import CloudflareResource, DomainsResource
from .mailboxes import MailboxMessagesResource, MailboxesResource
from .messages import MessagesResource
from .plans import PlansResource
from .smtp_access import SmtpAccessResource
from .smtp_relays import SmtpRelaysResource
from .status import StatusResource
from .support import SupportResource
from .templates import TemplatesResource
from .tracking import TrackingResource
from .units import UnitsResource
from .webhooks import SIGNATURE_HEADER, WebhooksResource

__all__ = [
    "ApiKeysResource",
    "AuthResource",
    "BillingResource",
    "CloudflareResource",
    "DomainsResource",
    "MailboxMessagesResource",
    "MailboxesResource",
    "MessagesResource",
    "PlansResource",
    "Resource",
    "SmtpAccessResource",
    "SmtpRelaysResource",
    "StatusResource",
    "SupportResource",
    "TemplatesResource",
    "TrackingResource",
    "UnitsResource",
    "WebhooksResource",
    "SIGNATURE_HEADER",
]
