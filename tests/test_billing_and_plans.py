"""Billing, plans, status and email-unit tests."""

from __future__ import annotations

import unittest

from wazobiamail.models import (
    AccountStatus,
    Currency,
    EffectiveLimits,
    Invoice,
    Page,
    Plan,
    PurchaseUnitsResult,
    Subscription,
    UnitsSummary,
)

try:
    from ._server import MockServerTestCase
except ImportError:  # pragma: no cover
    from _server import MockServerTestCase


INVOICE = {
    "id": "inv_101",
    "accountId": 7,
    "amount": 5000.0,
    "currency": "NGN",
    "status": "paid",
    "purpose": "Starter plan",
    "metadata": {"planId": "starter"},
    "dueDate": "2026-11-15",
    "paidAt": "2026-11-10T10:00:00",
    "createdAt": "2026-11-01T00:00:00",
}

PLAN = {
    "id": "starter",
    "name": "Starter",
    "usdPrice": 9.0,
    "nairaPrice": 7000.0,
    "yearlyUsdPrice": 90.0,
    "yearlyNairaPrice": 70000.0,
    "hourlyQuota": 100,
    "dailyQuota": 1000,
    "monthlyQuota": 30000,
    "sendRateLimitPerMinute": 60,
    "dataRetentionDays": 30,
    "features": ["custom_domains"],
    "limits": {"domainLimit": 3},
    "overageUsdPer1000": 0.5,
    "dedicatedIpAddonUsd": 20.0,
    "status": "active",
}


class TestBilling(MockServerTestCase):
    def test_list_invoices(self) -> None:
        self.server.enqueue(
            data={
                "items": [INVOICE],
                "pagination": {
                    "page": 1,
                    "pageSize": 10,
                    "totalItems": 1,
                    "totalPages": 1,
                    "hasNext": False,
                    "hasPrev": False,
                },
            }
        )
        result = self.make_client().billing.list_invoices()
        self.assertEqual(self.server.last.path, "/api/v1/billing/invoices")
        self.assertIsInstance(result.data, Page)
        self.assertEqual(result.data.items[0].id, "inv_101")
        self.assertIsInstance(result.data.items[0], Invoice)
        self.assertEqual(result.data.pagination.total_items, 1)

    def test_get_invoice_wrapper_and_missing_null(self) -> None:
        self.server.enqueue(data={"invoice": INVOICE})
        result = self.make_client().billing.get_invoice("inv_101")
        self.assertEqual(
            self.server.last.path, "/api/v1/billing/invoices/inv_101"
        )
        self.assertEqual(result.data.purpose, "Starter plan")
        self.assertEqual(result.data.metadata, {"planId": "starter"})

        self.server.enqueue(data={"invoice": None})
        missing = self.make_client().billing.get_invoice("missing")
        self.assertIsNone(missing.data)

    def test_download_invoice(self) -> None:
        self.server.enqueue_binary(
            b"%PDF-1.4",
            headers={"Content-Disposition": 'attachment; filename="INV-1.pdf"'},
        )
        result = self.make_client().billing.download_invoice("inv_101")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/billing/invoices/inv_101/download",
        )
        self.assertEqual(result.content, b"%PDF-1.4")
        self.assertEqual(result.filename, "INV-1.pdf")

    def test_create_invoice_contract(self) -> None:
        self.server.enqueue(data={"invoiceId": "inv_new"})
        result = self.make_client().billing.create_invoice(
            1500.0, currency="NGN"
        )
        self.assertEqual(
            self.server.last.json,
            {"amount": 1500.0, "currency": "NGN", "status": "open"},
        )
        self.assertEqual(result.data["invoiceId"], "inv_new")

    def test_current_subscription_and_currency(self) -> None:
        self.server.enqueue(
            data={
                "subscription": {
                    "id": "sub_1",
                    "accountId": 7,
                    "planId": "starter",
                    "status": "active",
                    "startDate": "2026-11-01T00:00:00",
                    "endDate": None,
                    "autoRenew": True,
                    "billingInterval": "monthly",
                    "plan": {
                        "id": "starter",
                        "name": "Starter",
                        "usdPrice": 9.0,
                        "nairaPrice": 7000.0,
                        "monthlyQuota": 30000,
                    },
                }
            }
        )
        result = self.make_client().billing.get_current_subscription(
            product="wazobiamail"
        )
        self.assertEqual(
            self.server.last.query_dict(), {"product": "wazobiamail"}
        )
        self.assertIsInstance(result.data, Subscription)
        self.assertTrue(result.data.auto_renew)
        self.assertEqual(result.data.plan.monthly_quota, 30000)

        self.server.enqueue(data={"subscription": None})
        none_result = self.make_client().billing.get_current_subscription()
        self.assertIsNone(none_result.data)
        self.assertEqual(self.server.last.query, [])

        self.server.enqueue(data={"country": "NG", "currency": "NGN"})
        currency = self.make_client().billing.detect_currency()
        self.assertEqual(
            self.server.last.path, "/api/v1/payments/currency"
        )
        self.assertIsInstance(currency.data, Currency)
        self.assertEqual(currency.data.currency, "NGN")


class TestPlansAndStatus(MockServerTestCase):
    def test_list_plans(self) -> None:
        self.server.enqueue(
            data={
                "items": [PLAN],
                "pagination": {
                    "page": 1,
                    "pageSize": 7,
                    "totalItems": 7,
                    "totalPages": 1,
                },
            }
        )
        result = self.make_client().plans.list(product="wazobiamail")
        self.assertEqual(self.server.last.query_dict(), {"product": "wazobiamail"})
        self.assertIsInstance(result.data.items[0], Plan)
        self.assertEqual(result.data.items[0].usd_price, 9.0)
        self.assertEqual(result.data.items[0].send_rate_limit_per_minute, 60)

    def test_effective_limits(self) -> None:
        self.server.enqueue(
            data={
                "limits": {
                    "accountId": 7,
                    "planId": "enterprise",
                    "sendRateLimitPerMinute": 60,
                    "mailboxOpsPerMinute": 600,
                    "mailboxLimit": -1,
                    "baseMailboxLimit": -1,
                    "additionalMailboxLimit": 0,
                    "customDomainSendingEnabled": True,
                    "domainLimit": -1,
                    "receivingEnabled": True,
                    "mailboxStorageGb": -1,
                }
            }
        )
        result = self.make_client().plans.get_effective_limits()
        self.assertEqual(self.server.last.path, "/api/v1/plans/effective")
        self.assertIsInstance(result.data, EffectiveLimits)
        self.assertTrue(result.data.custom_domain_sending_enabled)
        self.assertEqual(result.data.mailbox_limit, -1)

    def test_status(self) -> None:
        self.server.enqueue(
            data={
                "plan": {
                    "id": "free",
                    "name": "Free",
                    "status": "active",
                    "billingInterval": "monthly",
                    "startDate": None,
                    "endDate": None,
                    "autoRenew": True,
                },
                "units": {
                    "monthlyAllocation": 0,
                    "subscriptionUsed": 0,
                    "subscriptionRemaining": 0,
                    "purchasedBalance": 0,
                    "totalRemaining": 0,
                    "unlimited": False,
                },
            }
        )
        result = self.make_client().status.get()
        self.assertEqual(self.server.last.path, "/api/v1/status")
        self.assertIsInstance(result.data, AccountStatus)
        self.assertEqual(result.data.plan.name, "Free")
        self.assertFalse(result.data.units.unlimited)


class TestUnits(MockServerTestCase):
    def test_summary_and_packs(self) -> None:
        self.server.enqueue(
            data={
                "includedAllowance": 30000,
                "includedUsed": 1200,
                "includedRemaining": 28800,
                "purchasedBalance": 5000,
                "unlimited": False,
                "canBuyCredits": True,
            }
        )
        summary = self.make_client().units.summary()
        self.assertEqual(self.server.last.path, "/api/v1/units/summary")
        self.assertIsInstance(summary.data, UnitsSummary)
        self.assertEqual(summary.data.included_remaining, 28800)
        self.assertTrue(summary.data.can_buy_credits)

        self.server.enqueue(
            data={
                "items": [
                    {
                        "id": "pack_1",
                        "name": "5,000 credits",
                        "description": "Top up",
                        "units": 5000,
                        "priceNgnMinor": 500000,
                        "priceUsdMinor": 500,
                        "isActive": True,
                        "sortOrder": 1,
                    }
                ]
            }
        )
        packs = self.make_client().units.packs()
        self.assertEqual(packs.data[0].price_ngn_minor, 500000)
        self.assertTrue(packs.data[0].is_active)

    def test_ledger_query_and_parsing(self) -> None:
        self.server.enqueue(
            data={
                "items": [
                    {
                        "id": "ledger_1",
                        "accountId": 7,
                        "email": "user@example.com",
                        "quantity": 5000,
                        "balanceAfter": 5000,
                        "source": "purchase",
                        "reference": "inv_1",
                        "actorId": 7,
                        "reason": "Credit purchase",
                        "createdAt": "2026-11-09T00:00:00",
                    }
                ],
                "pagination": {
                    "page": 1,
                    "pageSize": 10,
                    "totalItems": 1,
                    "totalPages": 1,
                },
            }
        )
        result = self.make_client().units.ledger(
            page=1, per_page=10, status="purchase"
        )
        self.assertEqual(self.server.last.query_dict()["perPage"], "10")
        self.assertEqual(result.data.items[0].balance_after, 5000)
        self.assertEqual(result.data.pagination.total_items, 1)

    def test_purchase_wire_contract_and_result(self) -> None:
        self.server.enqueue(
            data={
                "invoiceId": "inv_units_1",
                "units": 5000,
                "amountMinor": 550000,
                "creditAmountMinor": 500000,
                "serviceAmountMinor": 50000,
                "currency": "NGN",
                "status": "pending_payment",
            }
        )
        result = self.make_client().units.purchase(
            currency="NGN",
            pack_id="pack_1",
            units=5000,
            plan_id="starter",
            billing_interval="monthly",
        )
        self.assertEqual(
            self.server.last.json,
            {
                "currency": "NGN",
                "packId": "pack_1",
                "units": 5000,
                "planId": "starter",
                "billingInterval": "monthly",
            },
        )
        self.assertIsInstance(result.data, PurchaseUnitsResult)
        self.assertEqual(result.data.invoice_id, "inv_units_1")
        self.assertEqual(result.data.service_amount_minor, 50000)
        self.assertEqual(result.data.status, "pending_payment")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
