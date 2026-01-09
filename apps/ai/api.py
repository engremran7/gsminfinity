"""
Public API surface for the AI micro-module, to be loaded via AppService.
"""

from __future__ import annotations

from typing import Any

from apps.ai.services import (
    get_settings,
    list_models,
    register_knowledge_source,
    run_workflow,
)


def settings_snapshot() -> dict[str, Any]:
    return get_settings()


def models(kind: str | None = None) -> dict[str, Any]:
    return list_models(kind)


def knowledge_source(
    name: str, source_type: str, location: str, metadata: dict[str, Any] | None = None
):
    return register_knowledge_source(name, source_type, location, metadata)


def execute(workflow_name: str, payload: dict[str, Any], user=None):
    return run_workflow(workflow_name, payload, user)


__all__ = ["settings_snapshot", "models", "knowledge_source", "execute"]
