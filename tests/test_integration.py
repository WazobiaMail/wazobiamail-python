"""Opt-in live integration tests against a running WazobiaMail backend.

Run with::

    WAZOBIA_INTEGRATION=1 \
    WAZOBIA_INTEGRATION_EMAIL=sdk-admin@example.com \
    WAZOBIA_INTEGRATION_PASSWORD='...' \
    PYTHONPATH=sdks/python python3 -m unittest discover -s sdks/python/tests -p 'test_integration.py' -v

Set ``WAZOBIA_INTEGRATION_BASE_URL`` to point at a different server. The
suite is skipped unless the opt-in flag and credentials are supplied.
"""

from __future__ import annotations

import os
import time
import unittest

from wazobiamail import WazobiaMail
from wazobiamail.errors import WazobiaForbiddenError, WazobiaServerError
from wazobiamail.models import (
    Account,
    AccountStatus,
    ApiKey,
    CreatedApiKey,
    Currency,
    Domain,
    DomainDns,
    DomainVerification,
    EffectiveLimits,
    EmailLogs,
    Invoice,
    LedgerEntry,
    Mailbox,
    MailboxStorage,
    Page,
    Plan,
    PurchaseUnitsResult,
    SmtpAccess,
    SmtpRelay,
    SpamCheckResult,
    Subscription,
    SupportTicket,
    SupportTicketCreated,
    SupportTicketPage,
    Template,
    TemplatePage,
    TemplatePreview,
    TrackingList,
    UnitPack,
    UnitsSummary,
    UploadedFile,
)

INTEGRATION = os.environ.get("WAZOBIA_INTEGRATION") == "1"
EMAIL = os.environ.get("WAZOBIA_INTEGRATION_EMAIL", "")
PASSWORD = os.environ.get("WAZOBIA_INTEGRATION_PASSWORD", "")
BASE_URL = os.environ.get(
    "WAZOBIA_INTEGRATION_BASE_URL", "http://127.0.0.1:18001/api/v1"
)


@unittest.skipUnless(
    INTEGRATION and EMAIL and PASSWORD,
    "Set WAZOBIA_INTEGRATION=1, WAZOBIA_INTEGRATION_EMAIL and "
    "WAZOBIA_INTEGRATION_PASSWORD to run live integration tests",
)
class TestLiveIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.public = WazobiaMail(allow_unauthenticated=True, base_url=BASE_URL)
        login = cls.public.auth.login(EMAIL, PASSWORD)
        assert login.data.access_token, "login returned an empty access token"
        cls.client = WazobiaMail(
            access_token=login.data.access_token,
            base_url=BASE_URL,
            auth_scheme="bearer",
        )
        cls.suffix = str(time.time_ns())[-10:]

    def assert_wrapper(self, response, status: int = 200) -> None:
        self.assertTrue(response.success)
        self.assertEqual(response.status_code, status)
        self.assertIn("data", response.raw)

    # ------------------------------------------------------------------ auth

    def test_login_me_plans_and_status(self) -> None:
        me = self.client.auth.me()
        self.assert_wrapper(me)
        self.assertIsInstance(me.data, Account)
        self.assertEqual(me.data.email, EMAIL)
        self.assertGreater(me.data.account_id, 0)

        plans = self.client.plans.list(product="wazobiamail")
        self.assert_wrapper(plans)
        self.assertIsInstance(plans.data, Page)
        self.assertGreaterEqual(len(plans.data.items), 1)
        self.assertIsInstance(plans.data.items[0], Plan)
        self.assertTrue(plans.data.items[0].id)

        limits = self.client.plans.get_effective_limits()
        self.assert_wrapper(limits)
        self.assertIsInstance(limits.data, EffectiveLimits)
        self.assertTrue(limits.data.plan_id)

        status = self.client.status.get()
        self.assert_wrapper(status)
        self.assertIsInstance(status.data, AccountStatus)
        self.assertTrue(status.data.plan.name)
        self.assertIsNotNone(status.data.units)

    def test_public_plan_catalog_without_credentials(self) -> None:
        plans = self.public.plans.list()
        self.assert_wrapper(plans)
        self.assertGreaterEqual(len(plans.data.items), 1)

    # ----------------------------------------------------------- read surfaces

    def test_units_billing_and_smtp_access(self) -> None:
        summary = self.client.units.summary()
        self.assert_wrapper(summary)
        self.assertIsInstance(summary.data, UnitsSummary)

        packs = self.client.units.packs()
        self.assert_wrapper(packs)
        self.assertIsInstance(packs.data, list)
        if packs.data:
            self.assertIsInstance(packs.data[0], UnitPack)

        ledger = self.client.units.ledger(page=1, per_page=5)
        self.assert_wrapper(ledger)
        self.assertIsInstance(ledger.data, Page)
        if ledger.data.items:
            self.assertIsInstance(ledger.data.items[0], LedgerEntry)

        invoices = self.client.billing.list_invoices()
        self.assert_wrapper(invoices)
        self.assertIsInstance(invoices.data, Page)
        if invoices.data.items:
            self.assertIsInstance(invoices.data.items[0], Invoice)

        currency = self.client.billing.detect_currency()
        self.assert_wrapper(currency)
        self.assertIsInstance(currency.data, Currency)
        self.assertIn(currency.data.currency, {"NGN", "USD"})

        subscription = self.client.billing.get_current_subscription()
        self.assert_wrapper(subscription)
        self.assertTrue(
            subscription.data is None or isinstance(subscription.data, Subscription)
        )

        access = self.client.smtp_access.get()
        self.assert_wrapper(access)
        self.assertIsInstance(access.data, SmtpAccess)
        toggled = self.client.smtp_access.update(access.data.enabled)
        self.assert_wrapper(toggled)
        self.assertEqual(toggled.data["enabled"], access.data.enabled)

    def test_domains_mailboxes_and_templates_lists(self) -> None:
        domains = self.client.domains.list()
        self.assert_wrapper(domains)
        self.assertIsInstance(domains.data, list)
        for domain in domains.data:
            self.assertIsInstance(domain, Domain)

        mailboxes = self.client.mailboxes.list()
        self.assert_wrapper(mailboxes)
        self.assertIsInstance(mailboxes.data, list)
        for mailbox in mailboxes.data:
            self.assertIsInstance(mailbox, Mailbox)

        storage = self.client.mailboxes.storage()
        self.assert_wrapper(storage)
        self.assertIsInstance(storage.data, MailboxStorage)
        self.assertIsNotNone(storage.data.plan)

        keys = self.client.api_keys.list()
        self.assert_wrapper(keys)
        self.assertIsInstance(keys.data, list)
        for key in keys.data:
            self.assertIsInstance(key, ApiKey)

        relays = self.client.smtp_relays.list()
        self.assert_wrapper(relays)
        self.assertIsInstance(relays.data, list)
        for relay in relays.data:
            self.assertIsInstance(relay, SmtpRelay)

        templates = self.client.templates.list(limit=5)
        self.assert_wrapper(templates)
        self.assertIsInstance(templates.data, TemplatePage)
        for template in templates.data.items:
            self.assertIsInstance(template, Template)

        support = self.client.support.list(limit=5)
        self.assert_wrapper(support)
        self.assertIsInstance(support.data, SupportTicketPage)
        for ticket in support.data.items:
            self.assertIsInstance(ticket, SupportTicket)

    def test_deliverability_and_logs(self) -> None:
        spam = self.client.messages.spam_check(
            subject="Your order has shipped",
            html="<p>Hello Ada, your order is on the way.</p>",
            text="Hello Ada, your order is on the way.",
            from_="Acme <hello@example.com>",
        )
        self.assert_wrapper(spam)
        self.assertIsInstance(spam.data, SpamCheckResult)
        self.assertGreaterEqual(spam.data.score, 0)
        self.assertEqual(spam.data.threshold, 5.0)

        logs = self.client.messages.list_logs(limit=5)
        self.assert_wrapper(logs)
        self.assertIsInstance(logs.data, EmailLogs)

    def test_tracking_is_gated_or_available(self) -> None:
        try:
            tracking = self.client.tracking.list(limit=5)
        except WazobiaForbiddenError:
            return
        self.assert_wrapper(tracking)
        self.assertIsInstance(tracking.data, TrackingList)

    # ------------------------------------------------------------- domain CRUD

    def test_domain_crud_and_dns_inspection(self) -> None:
        domain_name = f"sdk-it-{self.suffix}.example.com"
        created = None
        try:
            response = self.client.domains.create(domain_name, mail_mode="hosted")
            self.assertTrue(response.success)
            self.assertIn(response.status_code, {200, 201})
            created = response.data
            self.assertIsInstance(created, Domain)
            self.assertTrue(created.id)
            domain_id = created.id

            fetched = self.client.domains.get(domain_id)
            self.assert_wrapper(fetched)
            self.assertEqual(fetched.data.id, domain_id)

            updated = self.client.domains.update(domain_id, is_default=False)
            self.assert_wrapper(updated)
            self.assertEqual(updated.data.id, domain_id)
            self.assertFalse(updated.data.is_default)

            dns = self.client.domains.get_dns_records(domain_id)
            self.assert_wrapper(dns)
            self.assertIsInstance(dns.data, DomainDns)
            self.assertIsInstance(dns.data.records, list)
            # Freshly created domains may still be provisioning their records.
            for record in dns.data.records:
                self.assertTrue(record.record_type)

            mail_dns = self.client.domains.get_mail_dns(domain_id)
            self.assert_wrapper(mail_dns)
            self.assertIsInstance(mail_dns.data, dict)
            self.assertTrue(mail_dns.data)

            try:
                provider = self.client.domains.detect_dns_provider(domain_name)
                self.assert_wrapper(provider)
                self.assertIn("provider", provider.data)
            except WazobiaServerError as error:
                self.assertEqual(error.status_code, 503)

            try:
                verification = self.client.domains.verify(domain_id)
                self.assert_wrapper(verification)
                self.assertIsInstance(verification.data, DomainVerification)
            except WazobiaServerError as error:
                # The local development stack has no DNS resolver configured.
                self.assertEqual(error.status_code, 503)

            # A freshly created, unverified domain cannot host a mailbox yet.
            try:
                self.client.mailboxes.create(domain_id, f"sdk{self.suffix}")
            except Exception as error:  # noqa: BLE001 - assert the API contract
                from wazobiamail.errors import WazobiaApiError

                self.assertIsInstance(error, WazobiaApiError)
                self.assertIn(error.status_code, {400, 422})
        finally:
            if created is not None:
                deleted = self.client.domains.delete(created.id)
                self.assertTrue(deleted.success)

    def test_domain_cloudflare_status_is_readable_or_unsupported(self) -> None:
        try:
            result = self.client.domains.cloudflare.status(domain_id="dom_missing")
        except Exception as error:  # noqa: BLE001 - feature may be unconfigured
            from wazobiamail.errors import WazobiaApiError

            self.assertIsInstance(error, WazobiaApiError)
            return
        self.assertTrue(result.success)

    # ------------------------------------------------------------ API keys

    def test_api_key_lifecycle(self) -> None:
        created = None
        revoked = False
        try:
            response = self.client.api_keys.create(f"SDK integration {self.suffix}")
            self.assertTrue(response.success)
            self.assertIn(response.status_code, {200, 201})
            created = response.data
            self.assertIsInstance(created, CreatedApiKey)
            self.assertTrue(created.id)
            self.assertTrue(created.api_key)

            listed = self.client.api_keys.list()
            self.assert_wrapper(listed)
            self.assertIn(created.id, [key.id for key in listed.data])

            regenerated = self.client.api_keys.regenerate(created.id)
            self.assert_wrapper(regenerated)
            self.assertEqual(regenerated.data.id, created.id)
            self.assertTrue(regenerated.data.api_key)

            revoked_response = self.client.api_keys.revoke(created.id)
            self.assert_wrapper(revoked_response)
            revoked = True
        finally:
            if created is not None and not revoked:
                try:
                    self.client.api_keys.revoke(created.id)
                except Exception:  # pragma: no cover - best-effort cleanup
                    pass

    # ----------------------------------------------------------- SMTP relays

    def test_smtp_relay_lifecycle(self) -> None:
        created = None
        try:
            response = self.client.smtp_relays.create(
                f"SDK relay {self.suffix}",
                host="smtp.example.com",
                port=587,
                username="sdk@example.com",
                password="SecretPass123!",
                tls_mode="starttls",
            )
            self.assertTrue(response.success)
            self.assertIn(response.status_code, {200, 201})
            created = response.data
            self.assertIsInstance(created, SmtpRelay)
            self.assertEqual(created.smtp_security, "starttls")

            fetched = self.client.smtp_relays.get(created.id)
            self.assert_wrapper(fetched)
            self.assertEqual(fetched.data.id, created.id)

            updated = self.client.smtp_relays.update(
                created.id, name=f"SDK relay updated {self.suffix}"
            )
            self.assert_wrapper(updated)
            self.assertIn("updated", updated.data.name)

            deactivated = self.client.smtp_relays.deactivate(created.id)
            self.assert_wrapper(deactivated)
            self.assertEqual(deactivated.data.status, "inactive")

            activated = self.client.smtp_relays.activate(created.id)
            self.assert_wrapper(activated)
            self.assertEqual(activated.data.status, "active")
        finally:
            if created is not None:
                deleted = self.client.smtp_relays.delete(created.id)
                self.assertTrue(deleted.success)

    # ------------------------------------------------------------- templates

    def test_template_lifecycle(self) -> None:
        created = None
        try:
            response = self.client.templates.create(
                f"SDK template {self.suffix}",
                "<h1>Hello {{name}}</h1>",
                subject="Hello {{name}}",
                category="marketing",
                text_body="Hello {{name}}",
            )
            self.assertTrue(response.success)
            self.assertIn(response.status_code, {200, 201})
            created = response.data
            self.assertIsInstance(created, Template)
            self.assertTrue(created.id)

            fetched = self.client.templates.get(created.id)
            self.assert_wrapper(fetched)
            self.assertEqual(fetched.data.id, created.id)

            updated = self.client.templates.update(
                created.id, subject=f"Updated {self.suffix}"
            )
            self.assert_wrapper(updated)
            self.assertIn("Updated", updated.data.subject)

            preview = self.client.templates.preview(
                created.id, sample_variables={"name": "Ada"}
            )
            self.assert_wrapper(preview)
            self.assertIsInstance(preview.data, TemplatePreview)
            self.assertIn("Ada", preview.data.rendered_body)

            synced = self.client.templates.sync_meta(created.id)
            self.assert_wrapper(synced)
            self.assertEqual(synced.data.id, created.id)
        finally:
            if created is not None:
                deleted = self.client.templates.delete(created.id)
                self.assertTrue(deleted.success)

    # --------------------------------------------------------------- support

    def test_support_ticket_lifecycle(self) -> None:
        subject = f"SDK integration {self.suffix}"
        created = self.client.support.create(
            subject,
            "Automated SDK integration check. Safe to ignore.",
            category="other",
            priority="low",
        )
        self.assertTrue(created.success)
        self.assertIn(created.status_code, {200, 201})
        self.assertIsInstance(created.data, SupportTicketCreated)
        ticket_id = created.data.id or created.data.ticket_id
        self.assertTrue(ticket_id)

        fetched = self.client.support.get(ticket_id)
        self.assert_wrapper(fetched)
        self.assertIsInstance(fetched.data, SupportTicket)
        self.assertEqual(fetched.data.subject, subject)

        replied = self.client.support.reply(
            ticket_id, "SDK integration follow-up."
        )
        self.assert_wrapper(replied)

        marked = self.client.support.mark_read(ticket_id)
        self.assert_wrapper(marked)

        listed = self.client.support.list(limit=10)
        self.assert_wrapper(listed)
        self.assertIn(ticket_id, [ticket.id for ticket in listed.data.items])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
