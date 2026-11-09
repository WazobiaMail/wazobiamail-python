# WazobiaMail Python SDK

Official Python SDK for the [WazobiaMail](https://wazobiamail.com) API. Deliver transactional emails, manage custom sending domains, inspect DNS records, provision hosted mailboxes, and automate enterprise headless inboxes with **zero runtime dependencies** and strict Python type hints.

[![PyPI version](https://img.shields.io/pypi/v/wazobiamail.svg)](https://pypi.org/project/wazobiamail/)
[![Python versions](https://img.shields.io/pypi/pyversions/wazobiamail.svg)](https://pypi.org/project/wazobiamail/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

---

## Features

- 🔑 **Ergonomic API Key Authentication** — Direct key initialization or automatic fallback to `WAZOBIA_API_KEY` / `WAZOBIAMAIL_API_KEY`.
- ⚡ **Zero External Dependencies** — Built entirely on the standard Python library (`urllib.request`, `json`, `ssl`). Instant installation without version conflicts.
- 🛡️ **PEP 561 Type Hints** — Fully typed dataclasses and method signatures with `py.typed` marker for Mypy, Pyright, and modern IDE auto-complete.
- 📬 **Complete Platform Surface** — Send transactional emails, check spam deliverability scores, manage sending domains and DNS, configure Cloudflare DNS, provision mailboxes, query enterprise inboxes, manage API keys, and download billing invoices.

---

## Installation

```bash
pip install wazobiamail
```

---

## Authentication & API Keys

WazobiaMail authenticates API requests using customer API keys prefixed with `wzbm_`. The key is automatically attached to the `X-API-Key` HTTP header.

### 1. Initialize with an explicit API key

```python
from wazobiamail import WazobiaMail

client = WazobiaMail("wzbm_live_your_api_key_here")
```

### 2. Initialize from environment variables

Set `WAZOBIA_API_KEY` in your environment:

```bash
export WAZOBIA_API_KEY="wzbm_live_your_api_key_here"
```

Then initialize without arguments:

```python
from wazobiamail import WazobiaMail

client = WazobiaMail()
```

### 3. Context Manager Support

```python
from wazobiamail import WazobiaMail

with WazobiaMail() as client:
    response = client.send(
        to="customer@example.com",
        subject="Welcome!",
        html="<p>Welcome to our service!</p>",
    )
    print("Tracking ID:", response.data.tracking_id)
```

> **Security Note:** The SDK implements safe `__repr__` masking (`wzbm_...3a9f`). Secrets are never leaked into logs, tracebacks, or interactive shells.

---

## Quick Start: Sending Transactional Emails

```python
from wazobiamail import WazobiaMail

client = WazobiaMail()

# High-level shortcut: client.send()
response = client.send(
    from_email="Acme Store <orders@mail.yourdomain.com>",
    to="customer@example.com",
    subject="Your order has shipped! 📦",
    html="<h1>Order Confirmation</h1><p>Thank you for your order.</p>",
    text="Thank you for your order.",
    reply_to="support@yourdomain.com",
)

print("Queued! Tracking ID:", response.data.tracking_id)
print("Status:", response.data.status)
print("Recipients Count:", response.data.recipients)
```

### Preventing duplicates with Idempotency Keys

```python
response = client.send(
    to="customer@example.com",
    subject="Monthly Receipt",
    html="<p>Invoice attached</p>",
    idempotency_key="invoice_2026_11_order_99812",
)
```

### Adding URL Attachments

```python
response = client.messages.send(
    from_email="Billing <billing@mail.yourdomain.com>",
    to="client@example.com",
    subject="Invoice #1042",
    html="<p>Please find your invoice attached.</p>",
    attachments=[
        {
            "url": "https://cdn.yourdomain.com/invoices/1042.pdf",
            "fileName": "invoice-1042.pdf",
        }
    ],
)
```

---

## Deliverability & Spam Pre-flight Inspection

Analyze drafts before broadcasting to verify SpamAssassin scores and deliverability:

```python
report = client.messages.spam_check(
    subject="Claim your reward now!",
    html_body="<p>Click here to win a free prize.</p>",
)

print("Deliverability Score (0-100):", report.data.deliverability_score)
print("Spam Score:", report.data.score)
print("Findings:", report.data.findings)
print("Recommendations:", report.data.recommendations)
```

---

## Sending Domains & DNS Management

```python
# 1. Register a new sending domain
domain = client.domains.create(
    domain="mail.yourdomain.com",
    mail_mode="hosted",  # 'hosted' or 'sending_only'
)
print("Domain ID:", domain.data.id)

# 2. Fetch required DNS records (SPF, DKIM, MX, DMARC)
dns = client.domains.get_dns_records(domain.data.id)
for record in dns.data.records:
    print(f"{record.record_type} {record.name} -> {record.value}")

# 3. Trigger verification check
check = client.domains.verify(domain.data.id, force=True)
print("Verified:", check.data.verified)

# 4. One-click Cloudflare DNS Sync
client.domains.cloudflare.sync(domain.data.id)
```

---

## Hosted Mailboxes & Enterprise Headless Inbox

```python
# 1. Create a hosted mailbox
mailbox = client.mailboxes.create(
    domain_id="domain_id_here",
    local_part="support",
    display_name="Support Team",
)
print("Mailbox email:", mailbox.data.mailbox.email)
print("Generated IMAP/SMTP Password:", mailbox.data.credential.password)

# 2. Query enterprise headless inbox messages (Enterprise Plan required)
inbox = client.mailboxes.messages.list(
    mailbox.data.mailbox.id,
    unread_only=True,
    limit=20,
)

for msg in inbox.data.items:
    print(f"[{msg.id}] From: {msg.from_address} | Subject: {msg.subject}")

# 3. Read full message body and attachments
detail = client.mailboxes.messages.get(mailbox.data.mailbox.id, inbox.data.items[0].id)
print("HTML Body:", detail.data.html_body)
print("Attachments:", detail.data.attachments)

# 4. Delete processed message
client.mailboxes.messages.delete(mailbox.data.mailbox.id, inbox.data.items[0].id)
```

---

## Scoped Sending API Keys & SMTP Relays

```python
# Create a scoped sending key (restricted exclusively to email delivery)
key = client.api_keys.create(
    name="Store Checkout Sender",
    scope="general",
)
print("New Scoped Secret:", key.data.api_key)

# Rotate key
rotated = client.api_keys.regenerate(key.data.id)
print("Rotated Secret:", rotated.data.api_key)
```

---

## Billing, Invoices & Email Credits

```python
# Check credit balance
units = client.units.get_summary()
print("Available email credits:", units.data.balance)

# List invoices
invoices = client.billing.list_invoices()

# Download invoice PDF bytes
pdf_bytes = client.billing.download_invoice(invoices.data.items[0].id)
with open("invoice.pdf", "wb") as f:
    f.write(pdf_bytes.content)
```

---

## Error Handling

All SDK exceptions inherit from `WazobiaError`. Non-2xx API responses raise `WazobiaApiError` (or a specialized subclass) containing HTTP status codes, error codes, and field validation dictionaries:

```python
from wazobiamail import (
    WazobiaMail,
    WazobiaAuthenticationError,
    WazobiaForbiddenError,
    WazobiaValidationError,
    WazobiaRateLimitError,
    WazobiaNotFoundError,
)

client = WazobiaMail()

try:
    client.send(
        from_email="invalid-email",
        to="customer@example.com",
        subject="Hello",
    )
except WazobiaValidationError as exc:
    print(f"Validation failed (HTTP {exc.status_code}):", exc.errors)
    # e.g. {'from': 'Invalid email address format'}
except WazobiaAuthenticationError:
    print("Invalid or expired API key (HTTP 401)")
except WazobiaForbiddenError as exc:
    print(f"Feature requires plan upgrade (HTTP 403): {exc.code}")
except WazobiaRateLimitError as exc:
    print(f"Rate limited (HTTP 429). Retry in {exc.retry_after}s")
except WazobiaNotFoundError:
    print("Resource not found (HTTP 404)")
except Exception as exc:
    print("API Error:", exc)
```

---

## License

MIT License &copy; 2026 [Bonifade Technologies](https://bonifade.com) / Bowofade Oyerinde ([@oyenet1](https://github.com/oyenet1)).
