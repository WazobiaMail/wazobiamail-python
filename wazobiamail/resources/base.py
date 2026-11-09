"""Shared resource helpers."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Type, TypeVar

from ..http import BinaryResult, HttpClient, HttpResult
from ..models import ApiResponse, Page, Pagination, normalize

M = TypeVar("M")


class Resource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def _request(
        self,
        method: str,
        path: str,
        *,
        parser: Optional[Callable[[Any], Any]] = None,
        json_body: Any = None,
        send_json: Optional[bool] = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        idempotency_key: Optional[str] = None,
        multipart: Optional[Any] = None,
    ) -> ApiResponse[Any]:
        kwargs: Dict[str, Any] = {
            "params": params,
            "headers": headers,
            "timeout": timeout,
            "idempotency_key": idempotency_key,
        }
        if multipart is not None:
            kwargs["multipart"] = multipart
        else:
            should_send = (
                method.upper() in {"POST", "PUT", "PATCH"}
                if send_json is None
                else send_json
            )
            if should_send:
                kwargs["json_body"] = {} if json_body is None else json_body

        result: HttpResult = self._http.request(method, path, **kwargs)
        data = result.data
        if parser is not None and data is not None:
            data = parser(data)
        return ApiResponse(
            success=True,
            message=result.message,
            data=data,
            status_code=result.status_code,
            headers=result.headers,
            raw=result.envelope,
        )

    def _binary(
        self,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> BinaryResult:
        result = self._http.request(
            "GET",
            path,
            params=params,
            headers=headers,
            timeout=timeout,
            binary=True,
        )
        return result.data


def _items(data: Any) -> List[Any]:
    d = normalize(data)
    value = d.get("items")
    return value if isinstance(value, list) else []


def parse_items(model: Type[M], key: str = "items") -> Callable[[Any], List[M]]:
    def parser(data: Any) -> List[M]:
        if isinstance(data, list):
            return [model.from_dict(item) for item in data]
        d = normalize(data)
        value = d.get(key)
        return [model.from_dict(item) for item in value] if isinstance(value, list) else []

    return parser


def parse_bare_list(model: Type[M]) -> Callable[[Any], List[M]]:
    def parser(data: Any) -> List[M]:
        return [model.from_dict(item) for item in data] if isinstance(data, list) else []

    return parser


def parse_one(model: Type[M], key: str) -> Callable[[Any], Optional[M]]:
    def parser(data: Any) -> Optional[M]:
        if not isinstance(data, Mapping):
            return None
        d = normalize(data)
        value = d.get(key)
        if isinstance(value, Mapping):
            return model.from_dict(value)
        return model.from_dict(data)

    return parser



def parse_direct(model: Type[M]) -> Callable[[Any], M]:
    def parser(data: Any) -> M:
        return model.from_dict(data)

    return parser


def parse_page(model: Type[M], key: str = "items") -> Callable[[Any], Page[M]]:
    def parser(data: Any) -> Page[M]:
        d = normalize(data)
        raw_items = d.get(key)
        items = (
            [model.from_dict(item) for item in raw_items]
            if isinstance(raw_items, list)
            else []
        )
        pagination = (
            Pagination.from_dict(d.get("pagination"))
            if isinstance(d.get("pagination"), Mapping)
            else None
        )
        return Page(items=items, pagination=pagination)

    return parser


__all__ = [
    "Resource",
    "parse_items",
    "parse_bare_list",
    "parse_one",
    "parse_direct",
    "parse_page",
]
