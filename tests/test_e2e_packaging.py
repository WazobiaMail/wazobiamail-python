"""Packaging, metadata, PEP 561 and public-surface integrity tests."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import wazobiamail
from wazobiamail.config import SDK_VERSION

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.9/3.10
    tomllib = None  # type: ignore[assignment]


PACKAGE_DIR = Path(wazobiamail.__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent


class TestPackaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pyproject_path = PROJECT_DIR / "pyproject.toml"
        cls.source_tree = cls.pyproject_path.is_file()
        cls.pyproject_text = (
            cls.pyproject_path.read_text(encoding="utf-8") if cls.source_tree else ""
        )
        if cls.source_tree and tomllib is not None:
            cls.pyproject = tomllib.loads(cls.pyproject_text)
        else:  # pragma: no cover - installed wheel or Python 3.9/3.10
            cls.pyproject = {}

    def require_source_tree(self) -> None:
        if not self.source_tree:
            self.skipTest("source-tree metadata is unavailable for an installed wheel")

    def test_package_exports_client(self) -> None:
        self.assertTrue(hasattr(wazobiamail, "WazobiaMail"))
        self.assertTrue(hasattr(wazobiamail, "Wazobia"))
        self.assertIs(wazobiamail.Wazobia, wazobiamail.WazobiaMail)

    def test_package_version_defined_and_consistent(self) -> None:
        self.assertEqual(wazobiamail.__version__, "0.1.0")
        self.assertEqual(wazobiamail.__version__, SDK_VERSION)
        if self.source_tree:
            if self.pyproject:
                self.assertEqual(self.pyproject["project"]["version"], SDK_VERSION)
            else:  # pragma: no cover
                match = re.search(
                    r'^version\s*=\s*"([^"]+)"', self.pyproject_text, re.M
                )
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1), SDK_VERSION)

    def test_pep561_py_typed_exists(self) -> None:
        py_typed = PACKAGE_DIR / "py.typed"
        self.assertTrue(
            py_typed.exists(), f"Expected {py_typed} to exist for PEP 561 compliance"
        )
        self.assertTrue(py_typed.is_file())

    def test_pyproject_packages_py_typed(self) -> None:
        self.require_source_tree()
        self.assertIn('wazobiamail = ["py.typed"]', self.pyproject_text)
        self.assertIn('include = ["wazobiamail*"]', self.pyproject_text)

    def test_zero_runtime_dependencies(self) -> None:
        self.require_source_tree()
        if self.pyproject:
            self.assertEqual(self.pyproject["project"].get("dependencies"), [])
        else:  # pragma: no cover
            self.assertIn("dependencies = []", self.pyproject_text)

    def test_python_floor_and_readme(self) -> None:
        self.require_source_tree()
        if self.pyproject:
            self.assertEqual(self.pyproject["project"]["requires-python"], ">=3.9")
            readme = self.pyproject["project"]["readme"]
        else:  # pragma: no cover
            readme = "README.md"
        self.assertTrue((PROJECT_DIR / readme).exists())

    def test_license_and_description_metadata(self) -> None:
        self.require_source_tree()
        if not self.pyproject:
            self.skipTest("tomllib unavailable")
        project = self.pyproject["project"]
        self.assertEqual(project["name"], "wazobiamail")
        self.assertEqual(project["license"]["text"], "MIT")
        self.assertIn("WazobiaMail", project["description"])
        self.assertTrue((PROJECT_DIR / "LICENSE").exists())

    def test_legacy_setup_py_is_a_thin_shim(self) -> None:
        setup_path = PROJECT_DIR / "setup.py"
        if not setup_path.is_file():
            self.skipTest("setup.py is not shipped in the installed wheel")
        setup_text = setup_path.read_text(encoding="utf-8")
        self.assertIn("from setuptools import setup", setup_text)
        self.assertIn("setup()", setup_text)
        self.assertNotIn("name=", setup_text)
        self.assertNotIn("version=", setup_text)

    def test_client_module_compatibility_path(self) -> None:
        from wazobiamail.client import Wazobia as LegacyAlias
        from wazobiamail.client import WazobiaMail as LegacyClient

        self.assertIs(LegacyClient, wazobiamail.WazobiaMail)
        self.assertIs(LegacyAlias, wazobiamail.WazobiaMail)

    def test_every_declared_export_exists(self) -> None:
        missing = [name for name in wazobiamail.__all__ if not hasattr(wazobiamail, name)]
        self.assertEqual(missing, [])

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
            "WazobiaWebhookError",
        ]
        for name in expected:
            with self.subTest(name=name):
                self.assertTrue(hasattr(wazobiamail, name))
                self.assertTrue(
                    issubclass(getattr(wazobiamail, name), Exception),
                    f"{name} must be an Exception subclass",
                )

    def test_all_resource_attributes_present_on_client(self) -> None:
        client = wazobiamail.WazobiaMail("wzbm_mock")
        expected_resources = [
            "auth",
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
            "templates",
            "tracking",
            "webhooks",
        ]
        for attr in expected_resources:
            with self.subTest(attr=attr):
                self.assertTrue(
                    hasattr(client, attr),
                    f"WazobiaMail client missing expected resource attribute '{attr}'",
                )

    def test_resource_alias_identity(self) -> None:
        client = wazobiamail.WazobiaMail("wzbm_mock")
        self.assertIs(client.emails, client.messages)
        self.assertIs(client.units.get_summary.__func__, client.units.summary.__func__)
        self.assertIs(client.support.create_ticket.__func__, client.support.create.__func__)

    def test_resources_package_exports(self) -> None:
        import wazobiamail.resources as resources

        for name in resources.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(resources, name))

    def test_resource_classes_exported_from_package(self) -> None:
        expected = [
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
        ]
        for name in expected:
            with self.subTest(name=name):
                self.assertTrue(hasattr(wazobiamail, name))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
