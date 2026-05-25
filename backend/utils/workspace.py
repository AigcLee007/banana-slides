"""Workspace-scoped helpers for anonymous multi-tenant isolation."""

from __future__ import annotations

import re
from typing import Optional

from flask import g, has_app_context, has_request_context, request

WORKSPACE_HEADER = "X-Workspace-Id"
DEFAULT_WORKSPACE_ID = "default"
_WORKSPACE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_SETTINGS_KEY_MAP = {
    'AI_PROVIDER_FORMAT': 'ai_provider_format',
    'GOOGLE_API_KEY': 'api_key',
    'OPENAI_API_KEY': 'api_key',
    'GOOGLE_API_BASE': 'api_base_url',
    'OPENAI_API_BASE': 'api_base_url',
    'TEXT_MODEL': 'text_model',
    'IMAGE_MODEL': 'image_model',
    'IMAGE_CAPTION_MODEL': 'image_caption_model',
    'OUTPUT_LANGUAGE': 'output_language',
    'MINERU_API_BASE': 'mineru_api_base',
    'MINERU_TOKEN': 'mineru_token',
    'BAIDU_API_KEY': 'baidu_api_key',
    'TEXT_MODEL_SOURCE': 'text_model_source',
    'IMAGE_MODEL_SOURCE': 'image_model_source',
    'IMAGE_CAPTION_MODEL_SOURCE': 'image_caption_model_source',
    'TEXT_API_KEY': 'text_api_key',
    'TEXT_API_BASE': 'text_api_base_url',
    'IMAGE_API_KEY': 'image_api_key',
    'IMAGE_API_BASE': 'image_api_base_url',
    'IMAGE_CAPTION_API_KEY': 'image_caption_api_key',
    'IMAGE_CAPTION_API_BASE': 'image_caption_api_base_url',
    'OPENAI_IMAGE_API_PROTOCOL': 'openai_image_api_protocol',
}


def normalize_workspace_id(raw: Optional[str]) -> Optional[str]:
    """Validate and normalize workspace ids coming from the client."""
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    if not _WORKSPACE_PATTERN.fullmatch(value):
        return None
    return value


def set_workspace_id(workspace_id: Optional[str]) -> str:
    """Bind the workspace id to the current Flask app context."""
    resolved = normalize_workspace_id(workspace_id) or DEFAULT_WORKSPACE_ID
    if has_app_context():
        g.workspace_id = resolved
    return resolved


def get_workspace_id() -> str:
    """Return the current workspace id, defaulting to a shared legacy scope."""
    if has_app_context() and getattr(g, "workspace_id", None):
        return g.workspace_id
    if has_request_context():
        return set_workspace_id(request.headers.get(WORKSPACE_HEADER))
    return DEFAULT_WORKSPACE_ID


def add_workspace_filter(query, model):
    """Apply owner_id filtering when the model supports anonymous workspaces."""
    if hasattr(model, "owner_id"):
        return query.filter(model.owner_id == get_workspace_id())
    return query


def get_workspace_project(project_id: str):
    """Fetch a project only if it belongs to the current workspace."""
    from models import Project

    return Project.query.filter(
        Project.id == project_id,
        Project.owner_id == get_workspace_id(),
    ).first()


def get_workspace_config_value(key: str, fallback=None):
    """Resolve runtime settings from the current workspace before global config/env."""
    from flask import current_app
    from models import Settings

    attr_name = _SETTINGS_KEY_MAP.get(key)
    if attr_name:
        settings = Settings.get_settings()
        value = getattr(settings, attr_name, None)
        if value is not None:
            return value

    if has_app_context() and current_app and hasattr(current_app, 'config'):
        config_value = current_app.config.get(key)
        if config_value is not None:
            return config_value

    return fallback
