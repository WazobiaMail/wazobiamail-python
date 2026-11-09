"""Reusable template CRUD, preview and Meta synchronization tests."""

from __future__ import annotations

import unittest

from wazobiamail.models import Template, TemplatePage, TemplatePreview

try:
    from ._server import MockServerTestCase
except ImportError:  # pragma: no cover
    from _server import MockServerTestCase


TEMPLATE = {
    "id": "tpl_123",
    "accountId": 7,
    "name": "Welcome email",
    "slug": "welcome-email",
    "channel": "email",
    "category": "marketing",
    "status": "active",
    "rejectionReason": None,
    "subject": "Welcome, {{name}}",
    "body": "<h1>Hello {{name}}</h1>",
    "textBody": "Hello {{name}}",
    "metaTemplateId": "meta_123",
    "metaTemplateName": "welcome_email",
    "language": "en_US",
    "components": [{"type": "BODY", "text": "Hello {{name}}"}],
    "variables": [{"name": "name"}],
    "design": {"background": "#ffffff"},
    "previewImageUrl": "https://cdn.example.com/templates/welcome.png",
    "isSystem": False,
    "revision": 3,
    "createdAt": "2026-11-09T00:00:00Z",
    "updatedAt": "2026-11-09T01:00:00Z",
}


class TestTemplates(MockServerTestCase):
    def test_list_templates_query_and_parsing(self) -> None:
        self.server.enqueue(
            data={"items": [TEMPLATE], "total": 1, "limit": 10, "offset": 0}
        )
        result = self.make_client().templates.list(
            channel="email",
            category="marketing",
            status="active",
            search="welcome",
            limit=10,
            offset=0,
        )
        self.assertEqual(self.server.last.path, "/api/v1/templates")
        self.assertEqual(
            self.server.last.query_dict(),
            {
                "channel": "email",
                "category": "marketing",
                "status": "active",
                "search": "welcome",
                "limit": "10",
                "offset": "0",
            },
        )
        self.assertIsInstance(result.data, TemplatePage)
        self.assertEqual(result.data.total, 1)
        self.assertEqual(result.data.limit, 10)
        self.assertEqual(result.data.offset, 0)
        template = result.data.items[0]
        self.assertIsInstance(template, Template)
        self.assertEqual(template.id, "tpl_123")
        self.assertEqual(template.account_id, 7)
        self.assertEqual(template.text_body, "Hello {{name}}")
        self.assertEqual(template.meta_template_id, "meta_123")
        self.assertEqual(template.preview_image_url, "https://cdn.example.com/templates/welcome.png")
        self.assertEqual(template.components, TEMPLATE["components"])
        self.assertEqual(template.variables, [{"name": "name"}])
        self.assertEqual(template.design, {"background": "#ffffff"})
        self.assertEqual(template.revision, 3)
        self.assertFalse(template.is_system)

    def test_create_template_wire_contract(self) -> None:
        self.server.enqueue(status=201, data=TEMPLATE)
        result = self.make_client().templates.create(
            "Welcome email",
            "<h1>Hello {{name}}</h1>",
            channel="email",
            category="marketing",
            subject="Welcome, {{name}}",
            text_body="Hello {{name}}",
            language="en_US",
            components=[{"type": "BODY"}],
            variables=[{"name": "name"}],
            design={"background": "#ffffff"},
            auto_submit_meta=True,
            is_system=False,
        )
        self.assertEqual(self.server.last.method, "POST")
        self.assertEqual(self.server.last.path, "/api/v1/templates")
        self.assertEqual(
            self.server.last.json,
            {
                "name": "Welcome email",
                "body": "<h1>Hello {{name}}</h1>",
                "channel": "email",
                "category": "marketing",
                "subject": "Welcome, {{name}}",
                "textBody": "Hello {{name}}",
                "language": "en_US",
                "components": [{"type": "BODY"}],
                "variables": [{"name": "name"}],
                "design": {"background": "#ffffff"},
                "autoSubmitMeta": True,
                "isSystem": False,
            },
        )
        self.assertEqual(result.data.id, "tpl_123")
        self.assertEqual(result.data.subject, "Welcome, {{name}}")

    def test_create_sends_only_required_fields_by_default(self) -> None:
        self.server.enqueue(data={**TEMPLATE, "channel": "email", "category": "marketing"})
        self.make_client().templates.create("Minimal", "<p>Body</p>")
        self.assertEqual(
            self.server.last.json,
            {"name": "Minimal", "body": "<p>Body</p>"},
        )

    def test_get_update_preview_sync_and_delete(self) -> None:
        client = self.make_client()

        self.server.enqueue(data=TEMPLATE)
        fetched = client.templates.get("tpl_123")
        self.assertEqual(self.server.last.method, "GET")
        self.assertEqual(self.server.last.path, "/api/v1/templates/tpl_123")
        self.assertEqual(fetched.data.slug, "welcome-email")

        self.server.enqueue(data={**TEMPLATE, "status": "paused", "body": "<p>New</p>"})
        updated = client.templates.update(
            "tpl_123",
            name="Welcome email v2",
            subject="Updated",
            body="<p>New</p>",
            text_body="New",
            status="paused",
            components=[{"type": "BODY", "text": "New"}],
        )
        self.assertEqual(self.server.last.method, "PUT")
        self.assertEqual(self.server.last.path, "/api/v1/templates/tpl_123")
        self.assertEqual(
            self.server.last.json,
            {
                "name": "Welcome email v2",
                "subject": "Updated",
                "body": "<p>New</p>",
                "textBody": "New",
                "status": "paused",
                "components": [{"type": "BODY", "text": "New"}],
            },
        )
        self.assertEqual(updated.data.status, "paused")

        self.server.enqueue(
            data={
                "channel": "email",
                "subject": "Welcome, Ada",
                "renderedBody": "<h1>Hello Ada</h1>",
                "renderedText": "Hello Ada",
                "status": "active",
                "canSend": True,
            }
        )
        previewed = client.templates.preview(
            "tpl_123", sample_variables={"name": "Ada"}
        )
        self.assertEqual(self.server.last.method, "POST")
        self.assertEqual(
            self.server.last.path, "/api/v1/templates/tpl_123/preview"
        )
        self.assertEqual(
            self.server.last.json, {"sampleVariables": {"name": "Ada"}}
        )
        self.assertIsInstance(previewed.data, TemplatePreview)
        self.assertEqual(previewed.data.rendered_body, "<h1>Hello Ada</h1>")
        self.assertEqual(previewed.data.rendered_text, "Hello Ada")
        self.assertTrue(previewed.data.can_send)

        self.server.enqueue(data={**TEMPLATE, "revision": 4})
        synced = client.templates.sync_meta("tpl_123")
        self.assertEqual(self.server.last.method, "POST")
        self.assertEqual(
            self.server.last.path, "/api/v1/templates/tpl_123/sync-meta"
        )
        self.assertEqual(self.server.last.json, {})
        self.assertEqual(synced.data.revision, 4)

        self.server.enqueue(data=None, message="Template deleted successfully")
        deleted = client.templates.delete("tpl_123")
        self.assertEqual(self.server.last.method, "DELETE")
        self.assertEqual(self.server.last.body, b"")
        self.assertIsNone(deleted.data)

    def test_preview_without_variables_sends_empty_object(self) -> None:
        self.server.enqueue(
            data={
                "channel": "email",
                "subject": "Hi",
                "renderedBody": "<p>Hi</p>",
                "renderedText": "Hi",
                "status": "draft",
                "canSend": False,
            }
        )
        self.make_client().templates.preview("tpl_123")
        self.assertEqual(self.server.last.json, {})

    def test_template_ids_are_url_encoded(self) -> None:
        self.server.enqueue(data=TEMPLATE)
        self.make_client().templates.get("id/with space")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/templates/id%2Fwith%20space",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
