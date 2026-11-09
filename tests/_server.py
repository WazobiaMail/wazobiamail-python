"""Small in-process HTTP server used by the SDK test-suite.

The tests deliberately exercise the real transport (``urllib``) instead of
mocking it, so headers, query strings, JSON encoding, multipart bodies and
binary downloads are verified exactly as they go over the wire.
"""

from __future__ import annotations

import json
import threading
import time
import unittest
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlsplit

from wazobiamail import WazobiaMail


@dataclass
class RecordedRequest:
    """A request captured by the mock server."""

    method: str
    path: str
    query: List[Tuple[str, str]]
    headers: Dict[str, str]
    body: bytes

    def query_dict(self) -> Dict[str, str]:
        return dict(self.query)

    def query_pairs(self, name: str) -> List[str]:
        return [value for key, value in self.query if key == name]

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")

    @property
    def json(self) -> Any:
        return json.loads(self.text)

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "")


@dataclass
class ResponseSpec:
    status: int = 200
    body: bytes = b""
    headers: Dict[str, str] = field(default_factory=dict)
    delay: float = 0.0


class MockServer:
    """Threaded local HTTP server that serves queued responses."""

    def __init__(self) -> None:
        self.requests: List[RecordedRequest] = []
        self._responses: List[ResponseSpec] = []
        self._lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def _handle(self) -> None:
                length = int(self.headers.get("content-length") or 0)
                body = self.rfile.read(length) if length else b""
                parsed = urlsplit(self.path)
                request = RecordedRequest(
                    method=self.command,
                    path=parsed.path,
                    query=parse_qsl(parsed.query, keep_blank_values=True),
                    headers={key.lower(): value for key, value in self.headers.items()},
                    body=body,
                )
                with owner._lock:
                    owner.requests.append(request)
                    response = (
                        owner._responses.pop(0)
                        if owner._responses
                        else ResponseSpec(
                            status=500,
                            body=json.dumps(
                                {
                                    "success": False,
                                    "message": "Mock server response queue is empty",
                                    "data": None,
                                }
                            ).encode("utf-8"),
                            headers={"Content-Type": "application/json"},
                        )
                    )

                if response.delay:
                    time.sleep(response.delay)
                try:
                    self.send_response(response.status)
                    headers = dict(response.headers)
                    headers.setdefault("Content-Length", str(len(response.body)))
                    headers.setdefault("Connection", "close")
                    for name, value in headers.items():
                        self.send_header(name, value)
                    self.end_headers()
                    if response.body:
                        self.wfile.write(response.body)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            do_GET = _handle
            do_POST = _handle
            do_PUT = _handle
            do_PATCH = _handle
            do_DELETE = _handle

            def log_message(self, *args: Any) -> None:
                return

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._httpd.daemon_threads = True
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, name="wazobiamail-mock", daemon=True
        )
        self._thread.start()

    @property
    def base_url(self) -> str:
        host, port = self._httpd.server_address[:2]
        return f"http://{host}:{port}/api/v1"

    def reset(self) -> None:
        with self._lock:
            self.requests.clear()
            self._responses.clear()

    def enqueue(
        self,
        status: int = 200,
        *,
        data: Any = None,
        message: str = "OK",
        success: bool = True,
        headers: Optional[Dict[str, str]] = None,
        raw_body: Optional[bytes] = None,
        delay: float = 0.0,
    ) -> None:
        """Queue a WazobiaMail envelope response."""

        if raw_body is None:
            raw_body = json.dumps(
                {"success": success, "message": message, "data": data}
            ).encode("utf-8")
        merged_headers = {"Content-Type": "application/json"}
        merged_headers.update(headers or {})
        with self._lock:
            self._responses.append(
                ResponseSpec(
                    status=status,
                    body=raw_body,
                    headers=merged_headers,
                    delay=delay,
                )
            )

    def enqueue_error(
        self,
        status: int,
        message: str,
        *,
        code: Optional[str] = None,
        errors: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "success": False,
            "message": message,
            "data": None,
        }
        if code is not None:
            payload["code"] = code
        if errors is not None:
            payload["errors"] = errors
        self.enqueue(
            status=status,
            raw_body=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )

    def enqueue_binary(
        self,
        content: bytes,
        *,
        status: int = 200,
        content_type: str = "application/pdf",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        merged = {"Content-Type": content_type}
        merged.update(headers or {})
        self.enqueue(status=status, raw_body=content, headers=merged)

    def enqueue_raw(self, body: str, *, status: int = 200) -> None:
        self.enqueue(
            status=status,
            raw_body=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

    @property
    def last(self) -> RecordedRequest:
        if not self.requests:
            raise AssertionError("Mock server recorded no requests")
        return self.requests[-1]

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)


class MockServerTestCase(unittest.TestCase):
    """Base class that owns one mock server for the whole test class."""

    server: MockServer

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.server = MockServer()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.stop()
        super().tearDownClass()

    def setUp(self) -> None:
        super().setUp()
        self.server.reset()

    def make_client(self, **kwargs: Any) -> WazobiaMail:
        kwargs.setdefault("api_key", "wzbm_test_key_1234567890")
        kwargs.setdefault("base_url", self.server.base_url)
        return WazobiaMail(**kwargs)


__all__ = [
    "MockServer",
    "MockServerTestCase",
    "RecordedRequest",
    "ResponseSpec",
]
