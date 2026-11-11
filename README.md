# WazobiaMail Python SDK

[![PyPI](https://img.shields.io/pypi/v/wazobiamail.svg)](https://pypi.org/project/wazobiamail/)

**Start free with 3,000 emails/month.** WazobiaMail is a Resend alternative for transactional email through an API or SMTP, with sending domains, hosted mailboxes and deliverability tools.

Official, zero-dependency Python client for the [WazobiaMail](https://wazobiamail.com) SaaS API.

Send transactional email, manage sending domains and DNS, provision hosted mailboxes, inspect
deliverability, buy email units, manage templates and support tickets, and verify webhooks from
one synchronous, fully typed client.

- **Zero runtime dependencies** — built on the Python standard library (`urllib`, `json`, `ssl`).
- **Typed responses** — every resource returns `ApiResponse[T]` with dataclass models.
- **Idiomatic Python** — model properties are `snake_case`; the wire format is `camelCase`.
- **Works with legacy servers** — parsing accepts both `camelCase` and legacy `snake_case` keys.
- **PEP 561 compliant** — ships `py.typed` for Mypy, Pyright and editor completion.
- **Python 3.9+** — no external packages required.

> 📚 **Official Platform Documentation**: Visit [docs.wazobiamail.com](https://docs.wazobiamail.com) for complete API documentation, DNS setup guides, webhooks, and deliverability best practices.

```bash
pip install wazobiamail
```

## Quick start

```python
from wazobiamail import WazobiaMail

client = WazobiaMail(api_key="wzbm_live_...")

receipt = client.messages.send(
    to="customer@example.com",
    sender="Acme Store <hello@mail.example.com>",
    subject="Your order has shipped",
    html="<p>Your order is on its way.</p>",
    text="Your order is on its way.",
)

print(receipt.data.status)       # "queued"
print(receipt.data.tracking_id)  # "trk_..."
```

Credentials can also come from the environment:

```bash
export WAZOBIA_API_KEY="wzbm_live_..."       # scoped sending key (X-API-Key)
export WAZOBIA_ACCESS_TOKEN="..."             # account token (Authorization: Bearer)
export WAZOBIA_BASE_URL="https://app.wazobiamail.com/api/v1"
export WAZOBIA_TIMEOUT="30"
```

`WAZOBIAMAIL_API_KEY`, `WAZOBIAMAIL_ACCESS_TOKEN` and `WAZOBIAMAIL_BASE_URL` are accepted as
alternate names. Explicit arguments always win.

## Authentication

### Sending API key

```python
client = WazobiaMail(api_key="wzbm_live_...")
```

Sends `X-API-Key: wzbm_live_...` on every request.

### Account access token

```python
public = WazobiaMail(allow_unauthenticated=True)
login = public.auth.login("you@example.com", "your-password")

client = WazobiaMail(
    access_token=login.data.access_token,
    auth_scheme="bearer",
)
```

`auth.login()` returns an `AuthPayload` with `access_token`, `refresh_token`, `account_id`,
`email`, `plan_id`, `saas_role` and related fields. Use `auth.refresh(refresh_token)` to rotate
tokens and `auth.me()` to read the current account.

### Both headers, custom headers and public endpoints

```python
client = WazobiaMail(
    api_key="wzbm_live_...",
    access_token="...",
    auth_scheme="both",             # "header", "bearer" or "both"
    headers={"X-Tenant": "acme"},
    user_agent="acme-service/1.0",
    timeout=15,
)

# Public endpoints work without credentials:
catalog = WazobiaMail(allow_unauthenticated=True).plans.list()
```

`auth_scheme` is inferred when omitted: a token becomes `bearer`, an API key becomes `header`,
and both become `both`.

## Responses

Every API call returns an `ApiResponse`:

```python
result = client.domains.list()

result.success       # True
result.status_code   # 200
result.message       # server message
result.raw           # complete decoded envelope
result.request_id    # X-Request-Id when present
result.data          # typed model, list, page or None
```

The client raises on failure instead of returning an unsuccessful response. See
[Error handling](#error-handling).

## Sending email

### Message payload

```python
receipt = client.messages.send(
    to=["one@example.com", "two@example.com"],
    cc="copy@example.com",
    bcc=["blind@example.com"],
    sender="Acme Store <hello@mail.example.com>",
    reply_to="support@example.com",
    subject="Welcome!",
    html="<p>Welcome to Acme.</p>",
    text="Welcome to Acme.",
    envelope_sender="bounce@example.com",
    idempotency_key="welcome-1042",
)
```

`to`, `cc` and `bcc` accept a string or a sequence. `sender` is the visible `From` address;
`from_` and `from_email` are accepted aliases. `html_body` and `text_body` are aliases for
`html` and `text`. You can also pass a complete API-shaped mapping as the first argument:

```python
client.messages.send({
    "to": ["customer@example.com"],
    "content": {
        "subject": "Hello",
        "from": "Acme <hello@mail.example.com>",
        "htmlBody": "<p>Hello</p>",
        "textBody": "Hello",
        "replyTo": "support@example.com",
    },
})
```

### URL attachments

```python
client.messages.send(
    to="customer@example.com",
    sender="Acme <hello@mail.example.com>",
    subject="Your invoice",
    html="<p>Invoice attached.</p>",
    attachments=[
        "https://cdn.example.com/invoices/1042.pdf",
        {"url": "https://cdn.example.com/receipts/1042.pdf", "name": "receipt.pdf"},
    ],
)
```

### Binary attachments (multipart)

```python
result = client.messages.send_with_attachments(
    to="customer@example.com",
    sender="Acme <hello@mail.example.com>",
    subject="Your invoice",
    html="<p>Invoice attached.</p>",
    files=["/path/to/invoice.pdf", b"raw-bytes", ("notes.txt", b"hello")],
)
```

The server accepts at most 5 MiB across attached files. Reusable uploads are available through
`upload_attachment`:

```python
uploaded = client.messages.upload_attachment("logo.png")
print(uploaded.data.public_url)
print(uploaded.data.file_name, uploaded.data.size_bytes)
```

### Spam and deliverability check

```python
check = client.messages.spam_check(
    subject="Your order has shipped",
    html="<p>Hello Ada, your order is on the way.</p>",
    text="Hello Ada, your order is on the way.",
    from_="Acme <hello@example.com>",
    reply_to="support@example.com",
    headers={"List-Unsubscribe": "<mailto:unsubscribe@example.com>"},
)

print(check.data.score, check.data.rating, check.data.is_spam)
for rule in check.data.rules:
    print(rule.code, rule.points, rule.recommendation)
```

Spam checks require a Business or Enterprise plan (administrators are also allowed).

### Delivery Tracking, Stats, Read Receipts & Click Receipts

WazobiaMail provides built-in, granular observability for every transactional email dispatched.

#### 1. Read Receipts (Open Tracking)
Every HTML email sent through WazobiaMail can automatically include an invisible, privacy-compliant 1x1 tracking pixel. When the recipient opens the email in their client (Apple Mail, Gmail, Outlook, etc.):
- An `email.opened` event is recorded.
- Captures exact timestamp, recipient IP geolocation, device type, and client user-agent.
- Tracks unique opens vs. total open counts to measure genuine recipient engagement.
- Queryable via `client.messages.get_tracking(tracking_id)` or streamed via Webhooks.

#### 2. Click Receipts (Link Tracking)
Links in your email content can be rewritten using your verified tracking domain (`email.mail.example.com` or `trk.wazobiamail.com`):
- When a recipient clicks any link, a `link.clicked` receipt is created with microsecond precision.
- Records the original destination URL, recipient email, click timestamp, and click count.
- Enables fraud detection, user engagement scoring, and automated lifecycle triggers.

#### 3. Delivery Lifecycle & Timeline
Every message transitions through well-defined lifecycle states:
`queued` ➔ `sent` ➔ `delivered` ➔ `opened` ➔ `clicked` ➔ `bounced` / `complained`

```python
# Inspect single message receipts and timeline
detail = client.messages.get_tracking("trk_123456789")
print("Status:", detail.data.status)
print("Delivered At:", detail.data.delivered_at)
print("Open Count (Read Receipts):", detail.data.open_count)
print("Click Count (Click Receipts):", detail.data.click_count)

for event in detail.data.events:
    print(f"[{event.occurred_at}] {event.event_type} - {event.recipient_email}")
    if event.link_url:
        print(f"  Clicked URL: {event.link_url}")
```

#### 4. Aggregated Delivery Stats & Logs
Query delivery rates, open rates, and bounce events across your account:

```python
tracking = client.messages.list_tracking(
    limit=20,
    offset=0,
    status="delivered",
    from_date="2026-11-01",
    to_date="2026-11-09",
)
for message in tracking.data.messages:
    print(message.tracking_id, message.delivered_count, message.open_count, message.click_count)

logs = client.messages.list_logs(limit=20)
for entry in logs.data.messages:
    print(entry.tracking_id, entry.subject, entry.status)
```

Tracking and email logs require a paid subscription. `client.tracking.list()` and
`client.tracking.get()` expose the same tracking endpoints.

## Domains and DNS

```python
domain = client.domains.create(
    "mail.example.com",
    is_default=False,
    mail_mode="hosted",          # "hosted" or "sending_only"
).data

client.domains.list()

fetched = client.domains.get(domain.id).data
client.domains.update(domain.id, is_default=True, mail_mode="hosted")

dns = client.domains.get_dns_records(domain.id).data
print(dns.provisioning, dns.verification_status, dns.copy_block)
for record in dns.records:
    print(record.record_type, record.host, record.value, record.status)

mail_dns = client.domains.get_mail_dns(domain.id).data
print(mail_dns["receiving"], mail_dns["dmarc"])

verification = client.domains.verify(domain.id, force=True).data
print(verification.verification_status, verification.verified_count)

client.domains.detect_dns_provider("mail.example.com")

client.domains.delete(domain.id)
```

DNS verification may return HTTP 503 when the server cannot reach DNS. Treat that as a
deployment/configuration condition, not a malformed request.

### Cloudflare DNS automation

```python
client.domains.cloudflare.status(domain_id=domain.id)
client.domains.cloudflare.connect(domain_id=domain.id, return_to="/dashboard")
client.domains.cloudflare.sync(domain.id)
client.domains.cloudflare.disconnect(domain_id=domain.id)
```

### Subdomain vs. Apex / Root Domain Architecture & Edge Cases

When configuring custom domains for transactional sending, choosing between a **subdomain** (e.g. `mail.example.com` or `send.example.com`) and an **apex/root domain** (`example.com`) is a critical architectural decision.

#### 1. Why Using a Subdomain is Recommended (Root Domain NOT Used)

In production environments, **we strongly recommend using a dedicated sending subdomain** rather than your root/apex domain:

- **Preserve Existing Business Email (Google Workspace / Microsoft 365):**
  If your root domain (`example.com`) already receives corporate email via Google Workspace or Microsoft 365, adding MX records pointing to WazobiaMail at the root apex `@` will **break your existing company email inbox routing**. Using `mail.example.com` isolates transactional email routing completely.
- **Isolate Sender Reputation:**
  Transactional emails (password resets, invoices, OTP codes) have high engagement and deliverability requirements. Sending from a subdomain (`mail.example.com`) ensures that any accidental marketing spam complaints won't degrade your corporate employee email deliverability.
- **Avoid SPF 10-Lookup Limit Exhaustion (RFC 7208):**
  SPF records have a strict limit of 10 DNS lookups. Root domains often accumulate multiple SaaS providers (Google, Zendesk, Salesforce, HubSpot). A dedicated subdomain gives WazobiaMail its own clean, independent SPF record without lookup count contention.

#### 2. DNS Hostnames When Root Domain is NOT Used

When verifying a subdomain like `mail.example.com`, ensure you configure your DNS provider (Cloudflare, Route53, Namecheap, GoDaddy) with the correct hostnames:

| Record Type | Host / Name (if domain is `mail.example.com`) | Target / Value | Notes |
| :--- | :--- | :--- | :--- |
| **TXT (SPF)** | `mail` (or `mail.example.com`) | `v=spf1 include:_spf.wazobiamail.com ~all` | **Do NOT** place on `@` root |
| **TXT (DKIM)** | `wzbm._domainkey.mail` | `k=rsa; p=MIGfMA0GCSqGSIb3...` | Selector is scoped to the subdomain |
| **MX (Hosted)**| `mail` (priority 10 / 20) | `mx1.wazobiamail.com` / `mx2.wazobiamail.com` | Only required if receiving mail or hosted inboxes |
| **CNAME (Tracking)** | `email.mail` | `trk.wazobiamail.com` | Used for custom branded click/open tracking |
| **TXT (DMARC)** | `_dmarc.mail` (or fallback to `_dmarc`) | `v=DMARC1; p=reject; rua=mailto:dmarc@...` | Resolvers fall back to apex `_dmarc` if omitted |

#### 3. Critical Edge Cases & Troubleshooting

##### ⚠️ Edge Case 1: `UnverifiedSenderDomain` (HTTP 422 / 403)
- If you verified `mail.example.com` in WazobiaMail, your `sender` or `from_` address **must** match that subdomain:
  - ✅ **Valid**: `sender="Acme Billing <billing@mail.example.com>"`
  - ❌ **Invalid**: `sender="Acme Billing <billing@example.com>"` (Fails because apex `example.com` is unverified)
- Attempting to send from an unverified parent domain will raise `WazobiaValidationError` or `WazobiaForbiddenError`.

##### 💡 Edge Case 2: Reply-To Decoupling (Best Practice)
- You can send from the verified subdomain while routing customer replies to your corporate root domain mailbox:
  ```python
  client.messages.send(
      sender="Acme Orders <orders@mail.example.com>",  # Verified sending subdomain
      reply_to="support@example.com",                  # Your corporate inbox on Google Workspace/Outlook
      to="customer@example.com",
      subject="Your receipt",
      html="<p>Thank you for your purchase!</p>",
  )
  ```
- This gives you the deliverability benefits of a dedicated sending subdomain while preserving user-friendly reply handling.

##### ☁️ Edge Case 3: Cloudflare Proxy Status (Grey Cloud vs. Orange Cloud)
- **Problem**: In Cloudflare DNS, leaving the proxy enabled (**Orange Cloud**) for mail or tracking records breaks SMTP traffic, DNS verification, and SSL certificate issuance.
- **Solution**: Always toggle Cloudflare records to **"DNS only" (Grey Cloud / Proxied: Off)** for all WazobiaMail SPF, DKIM, MX, and tracking records. If you use `client.domains.cloudflare.sync(domain_id)`, this is handled automatically.

##### ⏳ Edge Case 4: Negative DNS Caching (SOA Minimum TTL Delay)
- If you run `client.domains.verify(domain_id)` immediately after publishing DNS records before they propagate, recursive resolvers may cache the negative response (`NXDOMAIN` or empty record).
- Subsequent verification checks will continue to fail until the DNS TTL expires (often 5 to 60 minutes).
- **Tip**: Test propagation first with `dig TXT mail.example.com` or `dig TXT wzbm._domainkey.mail.example.com +trace` before triggering verification, or pass `force=True`.

##### 🛡️ Edge Case 5: DMARC Subdomain Policy (`sp=`) Inheritance
- If your apex domain (`example.com`) has a DMARC record with `sp=reject` or `sp=quarantine`:
  - Any subdomain (e.g. `mail.example.com`) automatically inherits that rejection policy unless it defines its own `_dmarc.mail.example.com` record.
  - If SPF or DKIM alignment fails on the subdomain, recipient mail servers (Gmail, Yahoo, Outlook) will reject or spam-folder your emails immediately. Ensure both SPF and DKIM pass before sending production traffic.

##### 📬 Edge Case 6: Headless Inboxes & Hosted Mailboxes on Subdomains
- When provisioning hosted mailboxes (`client.mailboxes.create(domain_id, local_part="support")`), the mailbox address is generated under the specific verified domain (e.g. `support@mail.example.com`).
- Inbound receiving requires the MX records for that exact subdomain to be pointing to WazobiaMail. Do not point the root domain MX to WazobiaMail if you have existing email services there.

##### 🔁 Edge Case 7: Network Timeouts & Idempotency
- If an HTTP request times out due to transient network issues, the email may already have been queued by the API Gateway.
- Always provide an `idempotency_key` when dispatching critical transactional messages. Retrying with the same key returns the existing tracking receipt without duplicate sending.

## Hosted mailboxes

A domain must be verified before a mailbox can be created.

```python
created = client.mailboxes.create(
    domain_id=domain.id,
    local_part="support",
    display_name="Support Team",
    quota_mb=2048,
    password="A-Strong-Password-123!",
).data

print(created.mailbox.address)
print(created.credential.credential.username)
print(created.credential.password)   # only returned here

client.mailboxes.list()
client.mailboxes.get(created.mailbox.id)
client.mailboxes.update(created.mailbox.id, display_name="Customer Care")
client.mailboxes.suspend(created.mailbox.id)
client.mailboxes.activate(created.mailbox.id)

connection = client.mailboxes.connection(created.mailbox.id).data
print(connection.smtp, connection.imap, connection.pop3)

password = client.mailboxes.password(created.mailbox.id).data
storage = client.mailboxes.storage().data
print(storage.plan.mailboxes_used, storage.plan.storage_remaining_bytes)

credential = client.mailboxes.create_credentials(created.mailbox.id).data
client.mailboxes.rotate_credentials(created.mailbox.id)
client.mailboxes.revoke_credential(created.mailbox.id, credential.credential.id)
client.mailboxes.webmail_login(created.mailbox.id)

client.mailboxes.delete(created.mailbox.id)
```

### Enterprise inbox messages

```python
page = client.mailboxes.messages.list(
    created.mailbox.id,
    page=1,
    limit=25,
    unread_only=True,
    search="invoice",
).data

for message in page.items:
    print(message.subject, message.from_[0].email, message.received_at)

detail = client.mailboxes.messages.get(created.mailbox.id, page.items[0].id).data
print(detail.text_body, detail.html_body, detail.attachments)
client.mailboxes.messages.delete(created.mailbox.id, detail.id)
```

Mailbox message endpoints require an Enterprise plan.

## Sending API keys

```python
created = client.api_keys.create(
    "Checkout sender",
    scope="domain",
    domain_id=domain.id,
    expires_at="2027-01-01T00:00:00Z",
).data

print(created.id, created.key_prefix, created.api_key)

for key in client.api_keys.list().data:
    print(key.id, key.name, key.key_prefix, key.last_used_at)

regenerated = client.api_keys.regenerate(created.id).data
print(regenerated.api_key)          # secret is returned only here

client.api_keys.revoke(created.id)
```

The secret `api_key` is only present on create/regenerate responses; it is masked in reprs.

## SMTP relays and SMTP access

```python
relay = client.smtp_relays.create(
    "Primary relay",
    host="smtp.sendgrid.net",
    port=587,
    username="apikey",
    password="SG.secret",
    tls_mode="starttls",             # starttls, ssl_tls or none
    status="active",
    is_default=True,
).data

client.smtp_relays.list()
client.smtp_relays.get(relay.id)
client.smtp_relays.update(relay.id, name="Primary relay v2")
client.smtp_relays.deactivate(relay.id)
client.smtp_relays.activate(relay.id)
client.smtp_relays.delete(relay.id)
```

The relay endpoint expects a valid email-like username (it must contain `@` and no spaces).

```python
access = client.smtp_access.get().data
print(access.paid, access.eligible, access.enabled, access.connection)

client.smtp_access.update(True)      # save the preference
fresh = client.smtp_access.get().data
```

## Plans, status and units

```python
plans = client.plans.list(product="wazobiamail").data
for plan in plans.items:
    print(plan.id, plan.name, plan.usd_price, plan.monthly_quota)

limits = client.plans.get_effective_limits().data
print(limits.plan_id, limits.domain_limit, limits.mailbox_limit)

status = client.status.get().data
print(status.plan.name, status.units.total_remaining, status.units.unlimited)

summary = client.units.summary().data
print(summary.included_remaining, summary.purchased_balance, summary.can_buy_credits)

packs = client.units.packs().data
ledger = client.units.ledger(page=1, per_page=20, status="purchase").data
for entry in ledger.items:
    print(entry.source, entry.quantity, entry.balance_after)

purchase = client.units.purchase(
    "pack_5000",
    currency="NGN",
    plan_id="starter",
    billing_interval="monthly",
).data
print(purchase.invoice_id, purchase.amount_minor, purchase.status)
```

`units.purchase()` creates a pending invoice; it does not silently charge a card. Supply
`units=` instead of `pack_id=` for a variable quantity.

## Billing

```python
invoices = client.billing.list_invoices().data
for invoice in invoices.items:
    print(invoice.id, invoice.amount, invoice.currency, invoice.status)

invoice = client.billing.get_invoice("inv_123").data

pdf = client.billing.download_invoice("inv_123")
print(pdf.content_type, pdf.filename)
open("invoice.pdf", "wb").write(pdf.content)

subscription = client.billing.get_current_subscription(product="wazobiamail").data
if subscription:
    print(subscription.plan_id, subscription.status, subscription.auto_renew)

currency = client.billing.detect_currency().data
print(currency.country, currency.currency)

client.billing.create_invoice(1500.0, currency="NGN", status="open")
```

## Templates

```python
template = client.templates.create(
    "Welcome email",
    "<h1>Hello {{name}}</h1>",
    subject="Welcome, {{name}}",
    category="marketing",
    text_body="Hello {{name}}",
    language="en_US",
).data

client.templates.list(channel="email", category="marketing", limit=20, offset=0)
client.templates.get(template.id)
client.templates.update(template.id, subject="Updated subject", status="paused")

preview = client.templates.preview(
    template.id,
    sample_variables={"name": "Ada"},
).data
print(preview.rendered_body, preview.rendered_text, preview.can_send)

client.templates.sync_meta(template.id)
client.templates.delete(template.id)
```

Template endpoints require Enterprise access or an administrator account.

## Support tickets

```python
ticket = client.support.create(
    "Cannot verify my domain",
    "The TXT record still shows as pending.",
    category="domain",
    priority="high",
    domain="mail.example.com",
    attachments=[
        ("dig.txt", b"TXT output"),
        "/path/to/screenshot.png",
        {"filename": "headers.txt", "content": b"Received: ..."},
    ],
).data

print(ticket.id, ticket.ticket_id)

client.support.list(status="open", page=1, limit=20)
detail = client.support.get(ticket.id).data
print(detail.subject, detail.status, detail.messages)

client.support.reply(ticket.id, "Any update?", content_type="text")
client.support.mark_read(ticket.id)
```

Authenticated calls fill a missing `name`/`email` from `GET /auth/me`. Public ticket creation
works without credentials when both `name=` and `email=` are supplied. Attachment values may be
paths, `(filename, bytes)` tuples, or mappings with `filename` and `data`/`content`.

## Webhooks

WazobiaMail signs webhook deliveries with HMAC-SHA256 over the raw request body.

```python
from wazobiamail import WazobiaWebhookError

payload = request.get_data()                    # exact bytes
signature = request.headers["X-Wazobia-Signature"]

try:
    event = client.webhooks.construct_event(payload, signature, "whsec_...")
except WazobiaWebhookError:
    abort(400)

print(event["event"], event["data"])
```

Lower-level helpers are available too:

```python
client.webhooks.sign(payload, secret)
client.webhooks.verify_signature(payload, signature, secret)   # bool
```

A `sha256=` prefix is accepted. Always verify the raw bytes before parsing JSON.

## Error handling

```python
from wazobiamail import (
    WazobiaApiError,
    WazobiaAuthenticationError,
    WazobiaForbiddenError,
    WazobiaNotFoundError,
    WazobiaValidationError,
    WazobiaRateLimitError,
    WazobiaServerError,
    WazobiaConnectionError,
    WazobiaTimeoutError,
    WazobiaWebhookError,
)

try:
    client.domains.create("not a domain")
except WazobiaValidationError as error:
    print(error.status_code)     # 400 or 422
    print(error.errors)          # {"domain": "..."} when provided
    print(error.code)            # optional server code
    print(error.request_id)      # X-Request-Id when present
except WazobiaRateLimitError as error:
    print(error.retry_after)     # seconds, or None
except WazobiaAuthenticationError:
    ...
except WazobiaApiError as error:
    print(error.status_code, error.message)
```

- `WazobiaConnectionError` — DNS, socket, TLS or proxy failure.
- `WazobiaTimeoutError` — request exceeded `timeout`.
- `WazobiaAuthenticationError` — HTTP 401.
- `WazobiaForbiddenError` — HTTP 403 (including plan gates).
- `WazobiaNotFoundError` — HTTP 404.
- `WazobiaConflictError` — HTTP 409.
- `WazobiaValidationError` — HTTP 422, or HTTP 400 with field errors.
- `WazobiaRateLimitError` — HTTP 429; includes `retry_after`.
- `WazobiaServerError` — HTTP 5xx.
- `WazobiaWebhookError` — invalid signature or webhook body.

All API errors expose `status_code`, `message`, `code`, `errors`, `raw_body`, `request_id`
and `response_headers`.

## Pagination and models

Collection responses use `Page[T]` and `Pagination`:

```python
invoices = client.billing.list_invoices().data
print(invoices.pagination.page)
print(invoices.pagination.total_items)

ledger = client.units.ledger(per_page=50).data
for entry in ledger.items:
    print(entry.created_at, entry.reason, entry.balance_after)
```

Models are dataclasses. They expose idiomatic `snake_case` properties, accept both camelCase and
legacy snake_case keys when parsing, and keep the original server object in `.raw`:

```python
domain = client.domains.list().data[0]
print(domain.verification_status)
print(domain.raw["verificationStatus"])
```

## Context manager

```python
with WazobiaMail(api_key="wzbm_live_...") as client:
    client.status.get()
```

The client uses one short-lived HTTP connection per request and has no persistent pool to
close; `close()` exists for symmetry.

## Legacy import path

```python
from wazobiamail.client import WazobiaMail  # compatibility alias
```

The canonical path is `from wazobiamail import WazobiaMail`.

## Development and tests

The package has no runtime dependencies. The test suite uses `unittest` and an in-process mock
server that exercises the real transport (headers, query strings, multipart bodies and binary
downloads).

```bash
python3 -m compileall -q sdks/python

PYTHONPATH=sdks/python python3 -m unittest discover -s sdks/python/tests -v
```

### Live integration tests

The live suite is opt-in and runs against a running WazobiaMail backend:

```bash
WAZOBIA_INTEGRATION=1 \
WAZOBIA_INTEGRATION_EMAIL="sdk-admin@example.com" \
WAZOBIA_INTEGRATION_PASSWORD="..." \
WAZOBIA_INTEGRATION_BASE_URL="http://127.0.0.1:18001/api/v1" \
PYTHONPATH=sdks/python python3 -m unittest discover \
  -s sdks/python/tests -p 'test_integration.py' -v
```

It covers auth, plans/status, units, billing, SMTP access, domains/DNS, API keys, SMTP relays,
templates, support, logs, spam checks, and plan-gated tracking. Created domains, keys, relays,
templates and mailboxes are cleaned up; support tickets are intentionally left open.

### Build and install a wheel

```bash
python3 -m venv /tmp/wazobiamail-venv
/tmp/wazobiamail-venv/bin/pip install --no-build-isolation --no-deps .
/tmp/wazobiamail-venv/bin/python -c "import wazobiamail; print(wazobiamail.__version__)"
```

## Plan gates and server-side limitations

The SDK faithfully exposes server authorization. Some endpoints require specific plans or
backend configuration:

- Tracking list/detail and email logs require a paid subscription.
- Mailbox message endpoints require Enterprise.
- Spam checks require Business or Enterprise (administrators are also allowed).
- Templates require Enterprise or administrator access.
- Creating a mailbox requires a verified domain.
- Domain verification returns HTTP 503 when the server cannot reach DNS.

These are server responses, not SDK bugs; the SDK maps them to the exception types above.

## License

MIT. See [LICENSE](LICENSE).

---

## Reading spam-check scores

The spam check returns a penalty `score`, a `threshold`, an `isSpam` boolean and an inverse `deliverabilityScore` (0–100, higher is better).

| `score` | `rating` | `isSpam` | `deliverabilityScore` | Decision |
| --- | --- | --- | --- | --- |
| `0.0 – 1.9` | `low_risk` | `false` | `81 – 100` | **Okay to send.** Clean or only minor findings. |
| `2.0 – 4.9` | `moderate_risk` | `false` | `51 – 80` | **Review first.** Not blocked, but fix the highest-point rules before sending. |
| `5.0 +` | `high_risk` | `true` | `0 – 50` | **Do not send.** Fix the findings and re-run the check. |

`isSpam` is the authoritative decision: it is true when `score >= threshold`. Read `threshold` from the response instead of hard-coding `5.0`; the server can change it. A green score is not a delivery guarantee — domain authentication, sender reputation and recipient engagement still matter.

## Official WazobiaMail SDKs

WazobiaMail is a **Resend alternative** for transactional email through an **API or SMTP**, with sending domains, hosted mailboxes and deliverability tools. Start free with **3,000 emails/month**.

The SDKs below all use the WazobiaMail API; SMTP/legacy clients that need SMTP submission can use WazobiaMail's SMTP access from the dashboard. Choose the package that matches your stack:

| Platform | Install | Registry | Source |
| --- | --- | --- | --- |
| TypeScript / Node.js | `npm install wazobiamail` | [npm](https://www.npmjs.com/package/wazobiamail) | [GitHub](https://github.com/WazobiaMail/wazobiamail-node) |
| Vue 3 | `npm install wazobiamail-vue wazobiamail` | [npm](https://www.npmjs.com/package/wazobiamail-vue) | [GitHub](https://github.com/WazobiaMail/wazobiamail-vue) |
| Nuxt 3 & 4 | `npm install wazobiamail-nuxt` | [npm](https://www.npmjs.com/package/wazobiamail-nuxt) | [GitHub](https://github.com/WazobiaMail/wazobiamail-nuxt) |
| Python | `pip install wazobiamail` | [PyPI](https://pypi.org/project/wazobiamail/) | [GitHub](https://github.com/WazobiaMail/wazobiamail-python) |
| PHP | `composer require wazobiamail/wazobiamail-php` | [Packagist](https://packagist.org/packages/wazobiamail/wazobiamail-php) | [GitHub](https://github.com/WazobiaMail/wazobiamail-php) |
| Laravel | `composer require wazobiamail/wazobiamail-laravel` | [Packagist](https://packagist.org/packages/wazobiamail/wazobiamail-laravel) | [GitHub](https://github.com/WazobiaMail/wazobiamail-laravel) |
| Rust | `cargo add wazobiamail` | [crates.io](https://crates.io/crates/wazobiamail) | [GitHub](https://github.com/WazobiaMail/wazobiamail-rust) |
| WordPress | Upload the plugin ZIP | [Packagist](https://packagist.org/packages/wazobiamail/wazobiamail-wordpress) · [GitHub releases](https://github.com/WazobiaMail/wazobiamail-wordpress/releases) | [GitHub](https://github.com/WazobiaMail/wazobiamail-wordpress) |

### What each package gives you

- **TypeScript / Node.js (`wazobiamail`)** — A zero-production-dependency typed client for Node.js 18+, Bun, Deno and edge runtimes. It ships ESM and CommonJS builds, typed errors, request builders, URL/multipart attachments, and resources for messages, domains, mailboxes, API keys, billing, units, plans, tracking, spam checks and support.
- **Vue 3 (`wazobiamail-vue`)** — A Vue plugin plus reactive composables: `useSendMail` for loading/success/error state, `useMailbox` for paginated headless inboxes with polling and optimistic delete, `useDomains` for domain/DNS workflows, and `useSpamCheck` for pre-flight deliverability checks.
- **Nuxt 3 & 4 (`wazobiamail-nuxt`)** — Keeps `runtimeConfig.wazobiamail.apiKey` on the Nitro server, adds the auto-imported `serverWazobiaClient(event)` helper, and auto-imports the Vue composables. Ideal for Nuxt apps that must not expose an API key to the browser bundle.
- **Python (`wazobiamail`)** — A synchronous, PEP 561-compliant client with **zero runtime dependencies** (standard library only), dataclass models and typed responses. Works in Django (sync views or `sync_to_async`), FastAPI (`def` endpoints or `run_in_threadpool`), Flask, scripts and workers. Includes webhook HMAC verification.
- **PHP (`wazobiamail/wazobiamail-php`)** — A Composer/Guzzle 7 client for PHP 8.1+. It accepts ergonomic flat send payloads or the canonical nested `content` shape, supports URL attachments and automatic multipart upload for inline files, and maps API failures to typed exceptions.
- **Laravel (`wazobiamail/wazobiamail-laravel`)** — Registers a native `wazobiamail` mail driver, service provider and `WazobiaMail` facade for Laravel 10–13. Existing `Mail`, Mailables and notifications keep working; the package also exposes domains, mailboxes and webhook verification.
- **Rust (`wazobiamail`)** — Async, strongly typed and `#![forbid(unsafe_code)]`, built on reqwest/tokio. Includes fluent request builders, typed response models, typed errors, secret masking in `Debug`, and resources for sending, domains, Cloudflare DNS, mailboxes, templates, tracking and billing.
- **WordPress (`wazobiamail-wordpress`)** — Routes every `wp_mail()` call through the WazobiaMail API without changing forms or plugins. It registers the site domain, displays SPF/DKIM/DMARC/MX records, verifies DNS, uploads attachments, and keeps recent delivery receipts in the admin screen.

### Documentation links

- [Official SDK guide and examples](https://docs.wazobiamail.com/docs/guides/sdks)
- [API reference](https://docs.wazobiamail.com/docs/api-reference)
- [Authentication and API keys](https://docs.wazobiamail.com/docs/guides/authentication)
- [Sending domains and DNS](https://docs.wazobiamail.com/docs/guides/domains)
- [Webhooks](https://docs.wazobiamail.com/docs/guides/webhooks)
