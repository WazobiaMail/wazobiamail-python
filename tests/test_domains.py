"""Sending domains, DNS inspection, verification and Cloudflare tests."""

from __future__ import annotations

import unittest

from wazobiamail.models import DomainDns, DomainVerification

try:
    from ._server import MockServerTestCase
except ImportError:  # pragma: no cover
    from _server import MockServerTestCase


DOMAIN = {
    "id": "dom_123",
    "accountId": 7,
    "domain": "example.com",
    "requestedDomain": "example.com",
    "verificationStatus": "verified",
    "isDefault": True,
    "domainRole": "primary",
    "parentDomainId": None,
    "createDefaultInboxes": False,
    "mailMode": "hosted",
    "createdAt": "2026-11-01T00:00:00",
}


class TestDomains(MockServerTestCase):
    def test_list_domains(self) -> None:
        self.server.enqueue(data={"items": [DOMAIN]})
        result = self.make_client().domains.list()
        self.assertEqual(self.server.last.path, "/api/v1/sending/domains")
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].domain, "example.com")
        self.assertEqual(result.data[0].verification_status, "verified")
        self.assertTrue(result.data[0].is_default)
        self.assertEqual(result.data[0].domain_role, "primary")

    def test_create_domain_wire_payload_and_parser(self) -> None:
        self.server.enqueue(data={"domain": DOMAIN}, status=201)
        result = self.make_client().domains.create(
            "example.com",
            is_default=True,
            use_root_domain=False,
            host_inboxes_on_main_domain=False,
            sending_subdomain="mta",
            mail_mode="hosted",
            create_default_inboxes=True,
        )
        self.assertEqual(self.server.last.path, "/api/v1/sending/domains")
        self.assertEqual(
            self.server.last.json,
            {
                "domain": "example.com",
                "is_default": True,
                "use_root_domain": False,
                "host_inboxes_on_main_domain": False,
                "sending_subdomain": "mta",
                "mail_mode": "hosted",
                "create_default_inboxes": True,
            },
        )
        self.assertEqual(result.data.id, "dom_123")
        self.assertEqual(result.data.mail_mode, "hosted")

    def test_get_update_and_delete(self) -> None:
        self.server.enqueue(data={"domain": DOMAIN})
        result = self.make_client().domains.get("dom_123")
        self.assertEqual(self.server.last.path, "/api/v1/sending/domains/dom_123")
        self.assertTrue(result.data.is_default)

        self.server.enqueue(data={"domain": {**DOMAIN, "isDefault": False}})
        updated = self.make_client().domains.update(
            "dom_123",
            domain="new.example.com",
            is_default=False,
            use_root_domain=True,
            mail_mode="sending_only",
        )
        self.assertEqual(self.server.last.method, "PATCH")
        self.assertEqual(
            self.server.last.json,
            {
                "domain": "new.example.com",
                "is_default": False,
                "use_root_domain": True,
                "mail_mode": "sending_only",
            },
        )
        self.assertFalse(updated.data.is_default)

        self.server.enqueue(data={"domainId": "dom_123"})
        deleted = self.make_client().domains.delete("dom_123")
        self.assertEqual(self.server.last.method, "DELETE")
        self.assertEqual(deleted.data, {"domainId": "dom_123"})

    def test_dns_records(self) -> None:
        self.server.enqueue(
            data={
                "domain": {
                    "provisioning": True,
                    "domainId": "dom_123",
                    "domain": "example.com",
                    "verificationStatus": "pending",
                    "copyBlock": "copy me",
                    "records": [
                        {
                            "id": "rec_1",
                            "recordType": "TXT",
                            "host": "_dmarc.example.com",
                            "value": "v=DMARC1; p=none",
                            "ttl": 3600,
                            "status": "verified",
                            "lastCheckedAt": "2026-11-09T10:00:00",
                        }
                    ],
                }
            }
        )
        result = self.make_client().domains.get_dns_records("dom_123")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/sending/domains/dom_123/dns-records",
        )
        self.assertIsInstance(result.data, DomainDns)
        self.assertTrue(result.data.provisioning)
        self.assertEqual(result.data.copy_block, "copy me")
        self.assertEqual(result.data.records[0].record_type, "TXT")
        self.assertEqual(result.data.records[0].last_checked_at, "2026-11-09T10:00:00")

    def test_mail_dns_and_provider_detection(self) -> None:
        self.server.enqueue(data={"dmarc": {"recordType": "TXT", "host": "_dmarc"}})
        mail_dns = self.make_client().domains.get_mail_dns("dom_123")
        self.assertEqual(
            self.server.last.path, "/api/v1/sending/domains/dom_123/mail-dns"
        )
        self.assertEqual(mail_dns.data["dmarc"]["recordType"], "TXT")

        self.server.enqueue(
            data={"provider": "cloudflare", "isCloudflare": True, "nameservers": []}
        )
        provider = self.make_client().domains.detect_dns_provider("mail.example.com")
        self.assertEqual(
            self.server.last.query_dict(), {"domain": "mail.example.com"}
        )
        self.assertTrue(provider.data["isCloudflare"])

    def test_verify_and_refresh(self) -> None:
        verification = {
            "domainId": "dom_123",
            "domain": "example.com",
            "verificationStatus": "verified",
            "verifiedCount": 3,
            "pendingCount": 0,
            "checks": [
                {
                    "recordType": "TXT",
                    "host": "_dmarc.example.com",
                    "expectedValue": "v=DMARC1; p=none",
                    "matched": True,
                    "observedValues": ["v=DMARC1; p=none"],
                }
            ],
        }
        self.server.enqueue(data={"verification": verification})
        verified = self.make_client().domains.verify("dom_123", force=True)
        self.assertEqual(
            self.server.last.path, "/api/v1/sending/domains/dom_123/verify"
        )
        self.assertEqual(self.server.last.json, {"force": True})
        self.assertIsInstance(verified.data, DomainVerification)
        self.assertEqual(verified.data.verified_count, 3)
        self.assertTrue(verified.data.checks[0].matched)

        self.server.enqueue(data={"verification": verification})
        refreshed = self.make_client().domains.refresh_dns("dom_123")
        self.assertEqual(
            self.server.last.path, "/api/v1/sending/domains/dom_123/dns-refresh"
        )
        self.assertEqual(self.server.last.json, {})
        self.assertEqual(refreshed.data.pending_count, 0)

    def test_ids_are_url_encoded(self) -> None:
        self.server.enqueue(data={"domain": DOMAIN})
        self.make_client().domains.get("id/with space")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/sending/domains/id%2Fwith%20space",
        )

    def test_cloudflare_status_and_connect_params(self) -> None:
        self.server.enqueue(data={"connected": True})
        status = self.make_client().domains.cloudflare.status(domain_id="dom_123")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/sending/domains/cloudflare/status",
        )
        self.assertEqual(self.server.last.query_dict(), {"domainId": "dom_123"})
        self.assertTrue(status.data["connected"])

        self.server.enqueue(data={"authorizeUrl": "https://dash.cloudflare.com/..."})
        connect = self.make_client().domains.cloudflare.connect(
            domain_id="dom_123", return_to="/dashboard"
        )
        self.assertEqual(
            self.server.last.query_dict(),
            {"domainId": "dom_123", "returnTo": "/dashboard"},
        )
        self.assertIn("authorizeUrl", connect.data)

    def test_cloudflare_sync_and_disconnect(self) -> None:
        self.server.enqueue(data={"synced": True})
        synced = self.make_client().domains.cloudflare.sync("dom_123")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/sending/domains/cloudflare/sync",
        )
        self.assertEqual(self.server.last.json, {"domainId": "dom_123"})
        self.assertTrue(synced.data["synced"])

        self.server.enqueue(data={})
        self.make_client().domains.cloudflare.disconnect(domain_id="dom_123")
        self.assertEqual(self.server.last.method, "DELETE")
        self.assertEqual(
            self.server.last.query_dict(), {"domain_id": "dom_123"}
        )
        self.assertEqual(self.server.last.body, b"")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
