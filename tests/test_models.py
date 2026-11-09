"""Model parsing, alias and export-integrity tests."""

from __future__ import annotations

import dataclasses
import unittest

import wazobiamail
from wazobiamail import models as model_module
from wazobiamail.models import (
    Account,
    ApiResponse,
    AuthPayload,
    Domain,
    DomainVerification,
    EmailAddress,
    Invoice,
    Mailbox,
    MailboxConnection,
    Pagination,
    Plan,
    SupportTicket,
    Template,
    TrackingDetail,
    TrackingMessage,
    normalize,
    snake_case,
)


class TestNormalization(unittest.TestCase):
    def test_snake_case_conversion(self) -> None:
        self.assertEqual(snake_case("trackingId"), "tracking_id")
        self.assertEqual(snake_case("HTMLBody"), "html_body")
        self.assertEqual(snake_case("usdPrice"), "usd_price")
        self.assertEqual(snake_case("already_snake"), "already_snake")

    def test_normalize_adds_aliases_without_overwriting_explicit_keys(self) -> None:
        normalized = normalize(
            {
                "trackingId": "camel",
                "tracking_id": "explicit",
                "HTMLBody": "<p>x</p>",
                "count": 1,
            }
        )
        self.assertEqual(normalized["tracking_id"], "explicit")
        self.assertEqual(normalized["trackingId"], "camel")
        self.assertEqual(normalized["html_body"], "<p>x</p>")
        self.assertEqual(normalized["HTMLBody"], "<p>x</p>")
        self.assertEqual(normalized["count"], 1)

    def test_normalize_non_mapping_returns_empty_dict(self) -> None:
        self.assertEqual(normalize(None), {})
        self.assertEqual(normalize([]), {})
        self.assertEqual(normalize("text"), {})


class TestEnvelopes(unittest.TestCase):
    def test_api_response_truthiness(self) -> None:
        response = ApiResponse(
            success=False, message="failed", data=None, status_code=500
        )
        self.assertFalse(response)
        response.success = True
        self.assertTrue(response)

    def test_request_id_is_case_insensitive(self) -> None:
        response = ApiResponse(
            success=True,
            message="ok",
            data=None,
            headers={"X-Request-Id": "req_1", "Content-Type": "application/json"},
        )
        self.assertEqual(response.request_id, "req_1")

    def test_request_id_absent(self) -> None:
        self.assertIsNone(ApiResponse(success=True, message="ok", data=None).request_id)

    def test_pagination_parses_camel_and_legacy_keys(self) -> None:
        camel = Pagination.from_dict(
            {
                "page": 2,
                "pageSize": 25,
                "totalItems": 51,
                "totalPages": 3,
                "hasNext": True,
                "hasPrev": True,
            }
        )
        self.assertEqual(
            (camel.page, camel.page_size, camel.total_items, camel.total_pages),
            (2, 25, 51, 3),
        )
        self.assertTrue(camel.has_next)
        self.assertTrue(camel.has_prev)

        legacy = Pagination.from_dict(
            {"page": 1, "page_size": 10, "total_items": 4, "total_pages": 1}
        )
        self.assertEqual(legacy.page_size, 10)
        self.assertFalse(legacy.has_next)


class TestModelParsing(unittest.TestCase):
    def test_auth_payload_parses_camel_case(self) -> None:
        payload = AuthPayload.from_dict(
            {
                "accountId": 7,
                "email": "ada@example.com",
                "username": "ada",
                "name": "Ada",
                "planId": "starter",
                "selectedPlanId": "starter",
                "saasRole": "user",
                "authProvider": "email",
                "accessToken": "access",
                "refreshToken": "refresh",
            }
        )
        self.assertEqual(payload.account_id, 7)
        self.assertEqual(payload.plan_id, "starter")
        self.assertEqual(payload.saas_role, "user")
        self.assertEqual(payload.access_token, "access")
        self.assertEqual(payload.refresh_token, "refresh")
        self.assertNotIn("access", repr(payload))

    def test_account_parses_legacy_snake_case(self) -> None:
        account = Account.from_dict(
            {
                "account_id": 9,
                "email": "legacy@example.com",
                "plan_id": "business",
                "selected_plan_id": "business",
                "saas_role": "admin",
                "auth_provider": "google",
            }
        )
        self.assertEqual(account.account_id, 9)
        self.assertEqual(account.plan_id, "business")
        self.assertEqual(account.auth_provider, "google")

    def test_domain_parses_camel_and_legacy_keys(self) -> None:
        domain = Domain.from_dict(
            {
                "id": "dom_1",
                "account_id": 7,
                "domain": "example.com",
                "requested_domain": "www.example.com",
                "verification_status": "verified",
                "is_default": True,
                "domain_role": "primary",
                "parent_domain_id": None,
                "create_default_inboxes": True,
                "mail_mode": "hosted",
                "created_at": "2026-11-09T00:00:00",
            }
        )
        self.assertEqual(domain.account_id, 7)
        self.assertEqual(domain.requested_domain, "www.example.com")
        self.assertEqual(domain.verification_status, "verified")
        self.assertTrue(domain.is_default)
        self.assertEqual(domain.mail_mode, "hosted")

    def test_domain_verification_nested_checks(self) -> None:
        verification = DomainVerification.from_dict(
            {
                "domainId": "dom_1",
                "domain": "example.com",
                "verificationStatus": "pending",
                "verifiedCount": 1,
                "pendingCount": 2,
                "checks": [
                    {
                        "recordType": "TXT",
                        "host": "_dmarc.example.com",
                        "expectedValue": "v=DMARC1; p=none",
                        "matched": False,
                        "observedValues": ["other"],
                    }
                ],
            }
        )
        self.assertEqual(verification.verified_count, 1)
        self.assertFalse(verification.checks[0].matched)
        self.assertEqual(verification.checks[0].observed_values, ["other"])

    def test_mailbox_and_connection_models(self) -> None:
        mailbox = Mailbox.from_dict(
            {
                "id": "mbx_1",
                "domainId": "dom_1",
                "address": "support@example.com",
                "localPart": "support",
                "displayName": "Support",
                "status": "active",
                "storageUsageBytes": 1024,
                "isPlatformSubdomain": False,
                "autoProvisioned": False,
            }
        )
        self.assertEqual(mailbox.domain_id, "dom_1")
        self.assertEqual(mailbox.local_part, "support")
        self.assertEqual(mailbox.storage_usage_bytes, 1024)

        connection = MailboxConnection.from_dict(
            {
                "mailboxId": "mbx_1",
                "domainId": "dom_1",
                "username": "support@example.com",
                "status": "active",
                "smtp": {"host": "smtp.example.com", "port": 587, "security": "STARTTLS"},
                "imap": {"host": "imap.example.com", "port": 993, "security": "SSL/TLS"},
                "pop3": {"host": "pop3.example.com", "port": 995, "security": "SSL/TLS"},
                "authentication": "Normal password",
                "passwordHint": "Use mailbox password",
            }
        )
        self.assertEqual(connection.smtp["port"], 587)
        self.assertEqual(connection.password_hint, "Use mailbox password")

        address = EmailAddress.from_dict({"name": "Ada", "email": "ada@example.com"})
        self.assertEqual(address.email, "ada@example.com")

    def test_plan_invoice_and_template_parse_aliases(self) -> None:
        plan = Plan.from_dict(
            {
                "id": "starter",
                "name": "Starter",
                "usd_price": 9.0,
                "naira_price": 7000.0,
                "send_rate_limit_per_minute": 60,
                "data_retention_days": 30,
                "features": ["custom_domains"],
                "limits": {"domainLimit": 3},
            }
        )
        self.assertEqual(plan.usd_price, 9.0)
        self.assertEqual(plan.send_rate_limit_per_minute, 60)
        self.assertEqual(plan.limits, {"domainLimit": 3})

        invoice = Invoice.from_dict(
            {
                "id": "inv_1",
                "accountId": 7,
                "amount": 5000.0,
                "currency": "NGN",
                "status": "paid",
                "purpose": "Subscription",
                "metadata": {"planId": "starter"},
                "dueDate": "2026-11-15",
                "paidAt": "2026-11-10T10:00:00",
                "createdAt": "2026-11-01T00:00:00",
            }
        )
        self.assertEqual(invoice.account_id, 7)
        self.assertEqual(invoice.due_date, "2026-11-15")
        self.assertEqual(invoice.metadata["planId"], "starter")

        template = Template.from_dict(
            {
                "id": "tpl_1",
                "text_body": "Plain",
                "meta_template_id": "meta_1",
                "preview_image_url": "https://cdn.example.com/x.png",
                "is_system": True,
            }
        )
        self.assertEqual(template.text_body, "Plain")
        self.assertEqual(template.meta_template_id, "meta_1")
        self.assertTrue(template.is_system)

    def test_support_ticket_parses_nested_messages(self) -> None:
        ticket = SupportTicket.from_dict(
            {
                "id": "ticket_1",
                "accountId": 7,
                "subject": "Help",
                "messages": [
                    {
                        "id": "msg_1",
                        "ticketId": "ticket_1",
                        "senderName": "Ada",
                        "senderEmail": "ada@example.com",
                        "message": "Hello",
                        "isFromStaff": True,
                        "attachments": [
                            {"id": "a1", "filename": "log.txt", "sizeBytes": 3}
                        ],
                    }
                ],
            }
        )
        self.assertEqual(ticket.account_id, 7)
        self.assertTrue(ticket.messages[0].is_from_staff)
        self.assertEqual(ticket.messages[0].attachments[0].filename, "log.txt")

    def test_tracking_message_accepts_both_counter_names(self) -> None:
        camel = TrackingMessage.from_dict(
            {"trackingId": "trk_1", "openCount": 3, "clickCount": 2}
        )
        self.assertEqual(camel.tracking_id, "trk_1")
        self.assertEqual(camel.open_count, 3)
        self.assertEqual(camel.click_count, 2)

        legacy = TrackingMessage.from_dict(
            {"tracking_id": "trk_2", "opens_count": 5, "clicks_count": 4}
        )
        self.assertEqual(legacy.tracking_id, "trk_2")
        self.assertEqual(legacy.opens_count, 5)
        self.assertEqual(legacy.clicks_count, 4)

    def test_tracking_detail(self) -> None:
        detail = TrackingDetail.from_dict(
            {
                "message": {
                    "trackingId": "trk_1",
                    "subject": "Hello",
                    "status": "delivered",
                },
                "events": [
                    {
                        "id": "evt_1",
                        "eventType": "open",
                        "recipientEmail": "to@example.com",
                        "occurredAt": "2026-11-09T00:00:00",
                        "engagement": {"count": 2},
                    }
                ],
            }
        )
        self.assertEqual(detail.message.subject, "Hello")
        self.assertEqual(detail.events[0].event_type, "open")
        self.assertEqual(detail.events[0].engagement, {"count": 2})

    def test_all_models_accept_empty_and_none_input(self) -> None:
        dataclasses_to_check = []
        for name in model_module.__all__:
            candidate = getattr(model_module, name)
            if dataclasses.is_dataclass(candidate) and hasattr(candidate, "from_dict"):
                dataclasses_to_check.append((name, candidate))
        self.assertGreater(len(dataclasses_to_check), 40)
        for name, candidate in dataclasses_to_check:
            with self.subTest(model=name):
                from_empty = candidate.from_dict({})
                from_none = candidate.from_dict(None)
                self.assertIsInstance(from_empty, candidate)
                self.assertIsInstance(from_none, candidate)


class TestExports(unittest.TestCase):
    def test_every_model_export_is_available(self) -> None:
        for name in model_module.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(model_module, name))
                self.assertTrue(hasattr(wazobiamail, name))

    def test_every_package_export_is_importable(self) -> None:
        for name in wazobiamail.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(wazobiamail, name))

    def test_version_is_consistent(self) -> None:
        from wazobiamail.config import SDK_VERSION

        self.assertEqual(wazobiamail.__version__, SDK_VERSION)
        self.assertEqual(SDK_VERSION, "0.1.0")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
