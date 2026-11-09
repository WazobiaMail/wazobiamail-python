"""Tests for packaging, metadata, PEP 561 compliance, and exports."""

from pathlib import Path
import unittest

import wazobiamail


class TestE2EPackaging(unittest.TestCase):
    def test_package_exports_client(self) -> None:
        self.assertTrue(hasattr(wazobiamail, "WazobiaMail"))
        self.assertTrue(hasattr(wazobiamail, "Wazobia"))
        self.assertIs(wazobiamail.Wazobia, wazobiamail.WazobiaMail)

    def test_package_version_defined(self) -> None:
        self.assertEqual(wazobiamail.__version__, "0.1.0")

    def test_pep561_py_typed_exists(self) -> None:
        package_dir = Path(wazobiamail.__file__).parent
        py_typed = package_dir / "py.typed"
        self.assertTrue(
            py_typed.exists(),
            f"Expected {py_typed} to exist for PEP 561 compliance",
        )

    def test_all_exception_classes_exported(self) -> None:
        expected = [
            "WazobiaError",
            "WazobiaApiError",
            "WazobiaAuthenticationError",
            "WazobiaForbiddenError",
            "WazobiaNotFoundError",
            "WazobiaValidationError",
            "WazobiaRateLimitError",
            "WazobiaTimeoutError",
            "WazobiaConflictError",
            "WazobiaConnectionError",
            "WazobiaServerError",
        ]
        for name in expected:
            self.assertTrue(
                hasattr(wazobiamail, name), f"Missing exported exception {name}"
            )

    def test_all_resource_attributes_present_on_client(self) -> None:
        client = wazobiamail.WazobiaMail("wzbm_mock")
        expected_resources = [
            "messages",
            "emails",
            "domains",
            "mailboxes",
            "api_keys",
            "smtp_relays",
            "smtp_access",
            "billing",
            "units",
            "plans",
            "status",
            "support",
            "auth",
        ]
        for attr in expected_resources:
            self.assertTrue(
                hasattr(client, attr),
                f"WazobiaMail client missing expected resource attribute '{attr}'",
            )


if __name__ == "__main__":
    unittest.main()
