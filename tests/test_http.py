"""Transport-level tests: envelopes, serialization, multipart and binary data."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import urllib.error

from wazobiamail import FileUpload, WazobiaMail, prepare_file
from wazobiamail.errors import WazobiaApiError, WazobiaConnectionError, WazobiaTimeoutError
from wazobiamail.http import encode_multipart

try:
    from ._server import MockServerTestCase
except ImportError:  # pragma: no cover
    from _server import MockServerTestCase


class TestEnvelopesAndSerialization(MockServerTestCase):
    def test_success_envelope_and_request_id(self) -> None:
        self.server.enqueue(
            data={"id": "dom_1", "domain": "example.com"},
            message="Fetched successfully",
            headers={"X-Request-Id": "req_1"},
        )
        result = self.make_client().domains.get("dom_1")
        self.assertTrue(result.success)
        self.assertTrue(result)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.message, "Fetched successfully")
        self.assertEqual(result.request_id, "req_1")
        self.assertEqual(result.raw["success"], True)
        self.assertEqual(result.data.id, "dom_1")

    def test_empty_response_body_returns_none(self) -> None:
        self.server.enqueue(204, raw_body=b"")
        result = self.make_client().domains.delete("dom_1")
        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 204)
        self.assertIsNone(result.data)

    def test_get_and_delete_do_not_send_json_bodies(self) -> None:
        self.server.enqueue(data=[])
        self.make_client().domains.list()
        self.assertEqual(self.server.last.body, b"")

        self.server.enqueue(data={"domainId": "d1"})
        self.make_client().domains.delete("d1")
        self.assertEqual(self.server.last.method, "DELETE")
        self.assertEqual(self.server.last.body, b"")

    def test_post_sends_compact_utf8_json(self) -> None:
        self.server.enqueue(data={})
        self.make_client().auth.login("person@example.com", "pässword")
        request = self.server.last
        self.assertEqual(request.headers["content-type"], "application/json")
        self.assertEqual(
            request.json, {"email": "person@example.com", "password": "pässword"}
        )
        self.assertIn("pässword".encode("utf-8"), request.body)
        self.assertNotIn(b", ", request.body)
        self.assertNotIn(b": ", request.body)

    def test_query_serialization_skips_none_and_uses_wire_names(self) -> None:
        self.server.enqueue(
            data={
                "items": [],
                "pagination": {
                    "page": 2,
                    "pageSize": 5,
                    "totalItems": 0,
                    "totalPages": 0,
                },
            }
        )
        self.make_client().units.ledger(
            page=2,
            per_page=5,
            status="purchase",
            search="two words",
            sort="created_at",
            descending=True,
        )
        request = self.server.last
        self.assertEqual(request.path, "/api/v1/units/ledger")
        self.assertEqual(
            request.query_dict(),
            {
                "page": "2",
                "perPage": "5",
                "status": "purchase",
                "search": "two words",
                "sort": "created_at",
                "descending": "true",
            },
        )

    def test_boolean_false_is_serialized_as_lowercase(self) -> None:
        self.server.enqueue(data=[])
        self.make_client().mailboxes.messages.list(
            "mbx_1", page=1, limit=10, unread_only=False, search="invoice"
        )
        self.assertEqual(
            self.server.last.query_dict(),
            {
                "page": "1",
                "limit": "10",
                "unreadOnly": "false",
                "search": "invoice",
            },
        )

    def test_path_segments_are_percent_encoded(self) -> None:
        self.server.enqueue(data={"message": {"trackingId": "a/b"}})
        self.make_client().messages.get_tracking("id with/slash")
        self.assertEqual(
            self.server.last.path,
            "/api/v1/sending/tracking/messages/id%20with%2Fslash",
        )

    def test_idempotency_key_header(self) -> None:
        self.server.enqueue(data={"result": {"status": "queued"}})
        self.make_client().messages.send(
            to="to@example.com",
            subject="Hi",
            html="<p>Hi</p>",
            idempotency_key="invoice-123",
        )
        self.assertEqual(self.server.last.headers["idempotency-key"], "invoice-123")

    def test_malformed_json_response_raises_api_error(self) -> None:
        self.server.enqueue(200, raw_body=b"<html>not json</html>")
        with self.assertRaises(WazobiaApiError) as caught:
            self.make_client().plans.list()
        self.assertIn("parse", caught.exception.message.lower())

    def test_binary_download_preserves_bytes_and_filename(self) -> None:
        self.server.enqueue_binary(
            b"%PDF-1.7\nbinary\x00data",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": 'attachment; filename="invoice-1042.pdf"',
            },
        )
        result = self.make_client().billing.download_invoice("inv_1042")
        self.assertEqual(result.content, b"%PDF-1.7\nbinary\x00data")
        self.assertEqual(result.content_type, "application/pdf")
        self.assertEqual(result.filename, "invoice-1042.pdf")
        self.assertEqual(bytes(result), result.content)
        self.assertEqual(result.status_code, 200)

    def test_timeout_is_mapped_to_timeout_error(self) -> None:
        self.server.enqueue(data=[], delay=0.25)
        client = self.make_client(timeout=0.05)
        with self.assertRaises(WazobiaTimeoutError) as caught:
            client.domains.list()
        self.assertEqual(caught.exception.timeout, 0.05)

    def test_connection_failure_is_mapped(self) -> None:
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError(ConnectionRefusedError("refused")),
        ):
            with self.assertRaises(WazobiaConnectionError):
                self.make_client().domains.list()


class TestFilePreparation(unittest.TestCase):
    def test_prepare_file_from_path_bytes_and_stream(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.txt"
            path.write_text("hello", encoding="utf-8")
            from_path = prepare_file(path)
            self.assertEqual(from_path.file_name, "report.txt")
            self.assertEqual(from_path.content, b"hello")
            self.assertEqual(from_path.content_type, "text/plain")

        from_bytes = prepare_file(b"\x00\x01", file_name="data.bin", content_type="application/octet-stream")
        self.assertEqual(from_bytes.content, b"\x00\x01")
        self.assertEqual(from_bytes.content_type, "application/octet-stream")

        stream = io.BytesIO(b"streamed")
        stream.name = "stream.csv"
        from_stream = prepare_file(stream)
        self.assertEqual(from_stream.file_name, "stream.csv")
        self.assertEqual(from_stream.content, b"streamed")
        self.assertEqual(from_stream.content_type, "text/csv")

    def test_prepare_file_rejects_missing_or_directory(self) -> None:
        with self.assertRaises(FileNotFoundError):
            prepare_file("/definitely/not/a/real/file.txt")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                prepare_file(directory)

    def test_prepare_file_rejects_text_file_handles(self) -> None:
        with tempfile.NamedTemporaryFile("w+", suffix=".txt") as handle:
            handle.write("hello")
            handle.flush()
            handle.seek(0)
            with self.assertRaises(ValueError):
                prepare_file(handle)


class TestMultipartEncoding(unittest.TestCase):
    def test_encode_multipart_fields_and_files(self) -> None:
        body, content_type = encode_multipart(
            [("message", '{"to":["a@example.com"]}')],
            [("files", FileUpload("hello.txt", b"hello", "text/plain"), "files")],
        )
        self.assertTrue(content_type.startswith("multipart/form-data; boundary="))
        boundary = content_type.split("boundary=", 1)[1]
        self.assertIn(f"--{boundary}".encode(), body)
        self.assertIn(b'name="message"', body)
        self.assertIn(b'name="files"; filename="hello.txt"', body)
        self.assertIn(b"Content-Type: text/plain", body)
        self.assertIn(b"hello", body)
        self.assertTrue(body.endswith(f"--{boundary}--\r\n".encode()))

    def test_multipart_headers_cannot_be_injected(self) -> None:
        body, _ = encode_multipart(
            [("message", "safe")],
            [
                (
                    "files",
                    FileUpload('bad"\r\nX-Injected: yes.txt', b"x", "text/plain\r\nX: y"),
                    "files",
                )
            ],
        )
        self.assertNotIn(b"\r\nX-Injected:", body)
        self.assertNotIn(b"\r\nX: y", body)
        self.assertIn(b"X-Injected: yes", body)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
