"""HTTP transport for the WazobiaMail API.

Uses only the Python standard library so the SDK has no runtime dependencies.
"""

from __future__ import annotations

import http.client as _http_client
import json
import mimetypes
import os
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Dict, Iterable, List, Mapping, Optional, Tuple, Union

from .config import ClientConfig
from .errors import (
    WazobiaApiError,
    WazobiaAuthenticationError,
    WazobiaConflictError,
    WazobiaConnectionError,
    WazobiaForbiddenError,
    WazobiaNotFoundError,
    WazobiaRateLimitError,
    WazobiaServerError,
    WazobiaTimeoutError,
    WazobiaValidationError,
)

_UNSET = object()

FileSource = Union[str, os.PathLike, bytes, bytearray, memoryview, BinaryIO]


@dataclass(frozen=True)
class FileUpload:
    """A file ready for multipart upload."""

    file_name: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass
class HttpResult:
    """Decoded result of a successful HTTP request."""

    status_code: int
    headers: Dict[str, str]
    data: Any
    message: str = ""
    envelope: Dict[str, Any] = field(default_factory=dict)
    raw_body: bytes = b""

    @property
    def request_id(self) -> Optional[str]:
        return self.headers.get("x-request-id")


@dataclass
class BinaryResult:
    """Raw response bytes, used for invoice PDF downloads."""

    content: bytes
    content_type: str = "application/octet-stream"
    filename: Optional[str] = None
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)

    def __bytes__(self) -> bytes:
        return self.content


def prepare_file(
    source: FileSource,
    file_name: Optional[str] = None,
    content_type: Optional[str] = None,
) -> FileUpload:
    """Normalise a path, bytes object or binary file handle into a FileUpload."""

    if isinstance(source, (str, os.PathLike)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Attachment does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"Attachment is not a regular file: {path}")
        resolved_name = file_name or path.name
        guessed = content_type or mimetypes.guess_type(resolved_name)[0]
        return FileUpload(
            file_name=resolved_name,
            content=path.read_bytes(),
            content_type=guessed or "application/octet-stream",
        )

    if isinstance(source, (bytes, bytearray, memoryview)):
        resolved_name = file_name or "attachment.bin"
        guessed = content_type or mimetypes.guess_type(resolved_name)[0]
        return FileUpload(
            file_name=resolved_name,
            content=bytes(source),
            content_type=guessed or "application/octet-stream",
        )

    read = getattr(source, "read", None)
    if callable(read):
        content = read()
        if not isinstance(content, (bytes, bytearray)):
            raise ValueError("Attachment file handles must be opened in binary mode")
        resolved_name = (
            file_name
            or getattr(source, "name", None)
            or "attachment.bin"
        )
        if not isinstance(resolved_name, str) or not resolved_name.strip():
            resolved_name = "attachment.bin"
        guessed = content_type or mimetypes.guess_type(resolved_name)[0]
        return FileUpload(
            file_name=Path(resolved_name).name,
            content=bytes(content),
            content_type=guessed or "application/octet-stream",
        )

    raise ValueError(
        "Attachment must be a filesystem path, bytes, or a binary file-like object"
    )


def _header_token(value: str) -> str:
    """Strip CR/LF and quotes so user values cannot break multipart headers."""

    return value.replace("\r", "").replace("\n", "").replace('"', "'")


def encode_multipart(
    fields: Iterable[Tuple[str, Any]],
    files: Iterable[Tuple[str, FileUpload, Optional[str]]] = (),
) -> Tuple[bytes, str]:
    """Encode simple fields and files as multipart/form-data."""

    boundary = f"----WazobiaMailPython{uuid.uuid4().hex}"
    chunks: List[bytes] = []

    for name, value in fields:
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            f'Content-Disposition: form-data; name="{_header_token(str(name))}"\r\n\r\n'.encode(
                "utf-8"
            )
        )
        if isinstance(value, (bytes, bytearray)):
            chunks.append(bytes(value))
        else:
            chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")

    for name, upload, part_name in files:
        field_name = _header_token(part_name or name)
        filename = _header_token(upload.file_name)
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            (
                f'Content-Disposition: form-data; name="{field_name}"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8")
        )
        chunks.append(
            f"Content-Type: {_header_token(upload.content_type)}\r\n\r\n".encode("utf-8")
        )
        chunks.append(upload.content)
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class HttpClient:
    """Synchronous JSON/multipart transport with typed error mapping."""

    def __init__(self, config: ClientConfig) -> None:
        self._config = config

    @property
    def config(self) -> ClientConfig:
        return self._config

    def get(self, path: str, **kwargs: Any) -> HttpResult:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> HttpResult:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> HttpResult:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> HttpResult:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> HttpResult:
        return self.request("DELETE", path, **kwargs)

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = _UNSET,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        idempotency_key: Optional[str] = None,
        multipart: Optional[
            Tuple[Iterable[Tuple[str, Any]], Iterable[Tuple[str, FileUpload, Optional[str]]]]
        ] = None,
        binary: bool = False,
    ) -> HttpResult:
        url = self._build_url(path, params)
        request_headers = self._build_headers(headers, idempotency_key)

        body: Optional[bytes] = None
        if multipart is not None:
            fields, files = multipart
            body, content_type = encode_multipart(fields, files)
            request_headers["Content-Type"] = content_type
        elif json_body is not _UNSET:
            body = json.dumps(
                json_body, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")

        timeout_seconds = float(timeout if timeout is not None else self._config.timeout)
        request = urllib.request.Request(
            url, data=body, headers=request_headers, method=method.upper()
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                status_code = int(response.status)
                response_headers = self._response_headers(response.headers)
                raw_body = response.read()
        except urllib.error.HTTPError as exc:
            raw_body = exc.read()
            response_headers = self._response_headers(exc.headers)
            exc.close()
            self._raise_api_error(
                int(exc.code), response_headers, raw_body, str(exc.reason or "")
            )
            raise AssertionError("unreachable")  # pragma: no cover
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, (TimeoutError, socket.timeout)):
                raise WazobiaTimeoutError(
                    f"Request timed out after {timeout_seconds:g}s",
                    timeout_seconds,
                    cause=exc,
                ) from exc
            raise WazobiaConnectionError(
                f"Could not reach the WazobiaMail API: {reason}", cause=exc
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise WazobiaTimeoutError(
                f"Request timed out after {timeout_seconds:g}s",
                timeout_seconds,
                cause=exc,
            ) from exc
        except ssl.SSLError as exc:
            raise WazobiaConnectionError(
                f"TLS error while contacting the WazobiaMail API: {exc}", cause=exc
            ) from exc
        except (_http_client.HTTPException, ConnectionError, OSError) as exc:
            raise WazobiaConnectionError(
                f"Connection error while contacting the WazobiaMail API: {exc}", cause=exc
            ) from exc

        response_headers = self._response_headers(response_headers)

        if binary:
            content_type = response_headers.get("content-type", "application/octet-stream")
            filename = self._content_disposition_filename(
                response_headers.get("content-disposition", "")
            )
            return HttpResult(
                status_code=status_code,
                headers=response_headers,
                data=BinaryResult(
                    content=raw_body,
                    content_type=content_type,
                    filename=filename,
                    status_code=status_code,
                    headers=response_headers,
                ),
                envelope={},
                raw_body=raw_body,
            )

        if not raw_body:
            return HttpResult(
                status_code=status_code,
                headers=response_headers,
                data=None,
                envelope={},
            )

        payload = self._decode_json(raw_body, status_code)
        if isinstance(payload, Mapping) and "success" in payload:
            envelope = dict(payload)
            success = bool(envelope.get("success"))
            message = str(envelope.get("message") or "")
            data = envelope.get("data")
            if not success:
                self._raise_api_error(
                    status_code, response_headers, raw_body, message, envelope
                )
            return HttpResult(
                status_code=status_code,
                headers=response_headers,
                data=data,
                message=message,
                envelope=envelope,
                raw_body=raw_body,
            )

        return HttpResult(
            status_code=status_code,
            headers=response_headers,
            data=payload,
            envelope={},
            raw_body=raw_body,
        )

    def _build_url(self, path: str, params: Optional[Mapping[str, Any]]) -> str:
        clean_path = path if path.startswith("/") else f"/{path}"
        url = f"{self._config.base_url}{clean_path}"
        if not params:
            return url

        pairs: List[Tuple[str, str]] = []
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, bool):
                pairs.append((key, "true" if value else "false"))
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if item is not None:
                        pairs.append((key, str(item)))
            else:
                pairs.append((key, str(value)))

        if not pairs:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{urllib.parse.urlencode(pairs)}"

    def _build_headers(
        self,
        extra: Optional[Mapping[str, str]],
        idempotency_key: Optional[str],
    ) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "User-Agent": self._config.user_agent,
            "Accept": "application/json",
        }
        headers.update(self._config.headers)

        if self._config.auth_scheme in {"header", "both"} and self._config.api_key:
            headers["X-API-Key"] = self._config.api_key
        if self._config.auth_scheme in {"bearer", "both"} and self._config.access_token:
            headers["Authorization"] = f"Bearer {self._config.access_token}"

        if extra:
            headers.update({str(key): str(value) for key, value in extra.items()})
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    @staticmethod
    def _response_headers(headers: Any) -> Dict[str, str]:
        if headers is None:
            return {}
        result: Dict[str, str] = {}
        for key, value in headers.items():
            result[str(key).lower()] = str(value)
        return result

    @staticmethod
    def _decode_json(raw_body: bytes, status_code: int) -> Any:
        try:
            text = raw_body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WazobiaApiError(
                f"Server response was not valid UTF-8 (HTTP {status_code})",
                status_code,
                raw_body=raw_body,
            ) from exc
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise WazobiaApiError(
                f"Failed to parse server response as JSON (HTTP {status_code})",
                status_code,
                raw_body=raw_body,
            ) from exc

    @staticmethod
    def _content_disposition_filename(value: str) -> Optional[str]:
        for part in value.split(";"):
            part = part.strip()
            if part.lower().startswith("filename="):
                return part.split("=", 1)[1].strip().strip('"')
        return None

    def _raise_api_error(
        self,
        status_code: int,
        headers: Mapping[str, str],
        raw_body: bytes,
        fallback_message: str,
        envelope: Optional[Mapping[str, Any]] = None,
    ) -> None:
        payload: Any = envelope
        message = fallback_message
        code: Optional[str] = None
        errors: Dict[str, str] = {}

        if payload is None:
            try:
                payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {}

        if isinstance(payload, Mapping):
            if payload.get("message"):
                message = str(payload["message"])
            elif payload.get("error"):
                message = str(payload["error"])
            if isinstance(payload.get("code"), str):
                code = payload["code"]
            raw_errors = payload.get("errors")
            if isinstance(raw_errors, Mapping):
                errors = {str(key): str(value) for key, value in raw_errors.items()}

        if not message:
            message = f"Request failed with status {status_code}"

        request_id = headers.get("x-request-id")
        common = {
            "code": code,
            "errors": errors or None,
            "raw_body": payload,
            "request_id": request_id,
            "response_headers": dict(headers),
        }

        if status_code == 401:
            raise WazobiaAuthenticationError(message, **common)
        if status_code == 403:
            raise WazobiaForbiddenError(message, **common)
        if status_code == 404:
            raise WazobiaNotFoundError(message, **common)
        if status_code == 409:
            raise WazobiaConflictError(message, **common)
        if status_code == 422 or (status_code == 400 and errors):
            raise WazobiaValidationError(message, status_code, **common)
        if status_code == 429:
            retry_after = headers.get("retry-after")
            parsed_retry: Optional[int] = None
            if retry_after:
                try:
                    parsed_retry = int(retry_after)
                except ValueError:
                    parsed_retry = None
            raise WazobiaRateLimitError(message, retry_after=parsed_retry, **common)
        if status_code >= 500:
            raise WazobiaServerError(message, status_code=status_code, **common)
        raise WazobiaApiError(message, status_code, **common)


__all__ = [
    "HttpClient",
    "HttpResult",
    "BinaryResult",
    "FileUpload",
    "prepare_file",
    "encode_multipart",
]
