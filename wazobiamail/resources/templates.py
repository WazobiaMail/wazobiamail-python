"""Reusable message templates and Meta synchronization."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import quote

from ..models import ApiResponse, Template, TemplatePage, TemplatePreview
from .base import Resource


def _template_id(value: str) -> str:
    return quote(str(value), safe="")


class TemplatesResource(Resource):
    """Manage email/WhatsApp templates.

    Template endpoints require Enterprise access (or an admin account);
    other plans receive HTTP 403 (``WazobiaForbiddenError``).
    """

    def list(
        self,
        *,
        channel: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[TemplatePage]:
        """List account and system templates."""

        return self._request(
            "GET",
            "/templates",
            params={
                "channel": channel,
                "category": category,
                "status": status,
                "search": search,
                "limit": limit,
                "offset": offset,
            },
            timeout=timeout,
            parser=lambda data: TemplatePage.from_dict(data),
        )

    def get(
        self, template_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Template]:
        """Fetch one template."""

        return self._request(
            "GET",
            f"/templates/{_template_id(template_id)}",
            timeout=timeout,
            parser=lambda data: Template.from_dict(data),
        )

    def create(
        self,
        name: str,
        body: str,
        *,
        channel: Optional[str] = None,
        category: Optional[str] = None,
        subject: Optional[str] = None,
        text_body: Optional[str] = None,
        language: Optional[str] = None,
        components: Any = None,
        variables: Any = None,
        design: Any = None,
        auto_submit_meta: Optional[bool] = None,
        is_system: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Template]:
        """Create a template."""

        payload: Dict[str, Any] = {"name": name, "body": body}
        if channel is not None:
            payload["channel"] = channel
        if category is not None:
            payload["category"] = category
        if subject is not None:
            payload["subject"] = subject
        if text_body is not None:
            payload["textBody"] = text_body
        if language is not None:
            payload["language"] = language
        if components is not None:
            payload["components"] = components
        if variables is not None:
            payload["variables"] = variables
        if design is not None:
            payload["design"] = design
        if auto_submit_meta is not None:
            payload["autoSubmitMeta"] = auto_submit_meta
        if is_system is not None:
            payload["isSystem"] = is_system

        return self._request(
            "POST",
            "/templates",
            json_body=payload,
            timeout=timeout,
            parser=lambda data: Template.from_dict(data),
        )

    def update(
        self,
        template_id: str,
        *,
        name: Optional[str] = None,
        category: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        text_body: Optional[str] = None,
        language: Optional[str] = None,
        components: Any = None,
        variables: Any = None,
        design: Any = None,
        status: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[Template]:
        """Update a template's content or status."""

        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if category is not None:
            payload["category"] = category
        if subject is not None:
            payload["subject"] = subject
        if body is not None:
            payload["body"] = body
        if text_body is not None:
            payload["textBody"] = text_body
        if language is not None:
            payload["language"] = language
        if components is not None:
            payload["components"] = components
        if variables is not None:
            payload["variables"] = variables
        if design is not None:
            payload["design"] = design
        if status is not None:
            payload["status"] = status

        return self._request(
            "PUT",
            f"/templates/{_template_id(template_id)}",
            json_body=payload,
            timeout=timeout,
            parser=lambda data: Template.from_dict(data),
        )

    def delete(
        self, template_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[None]:
        """Delete a template."""

        return self._request(
            "DELETE",
            f"/templates/{_template_id(template_id)}",
            send_json=False,
            timeout=timeout,
        )

    def sync_meta(
        self, template_id: str, *, timeout: Optional[float] = None
    ) -> ApiResponse[Template]:
        """Synchronize a template with Meta and return the updated record."""

        return self._request(
            "POST",
            f"/templates/{_template_id(template_id)}/sync-meta",
            timeout=timeout,
            parser=lambda data: Template.from_dict(data),
        )

    def preview(
        self,
        template_id: str,
        *,
        sample_variables: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> ApiResponse[TemplatePreview]:
        """Render a template preview with optional sample variables."""

        payload: Dict[str, Any] = {}
        if sample_variables is not None:
            payload["sampleVariables"] = sample_variables
        return self._request(
            "POST",
            f"/templates/{_template_id(template_id)}/preview",
            json_body=payload,
            timeout=timeout,
            parser=lambda data: TemplatePreview.from_dict(data),
        )


__all__ = ["TemplatesResource"]
