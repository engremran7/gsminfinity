
from __future__ import annotations

from django.conf import settings
from django.db import models
from solo.models import SingletonModel


class AISettings(SingletonModel):
    """
    Global toggles for the AI platform (decentralized, app-owned).
    """

    ai_enabled = models.BooleanField(default=True)
    default_model = models.CharField(max_length=100, default="gpt-4")
    enable_vector_search = models.BooleanField(default=True)
    enable_auto_translation = models.BooleanField(default=True)
    enable_safety_firewall = models.BooleanField(default=True)
    default_locale = models.CharField(max_length=16, default="en")

    class Meta:
        verbose_name = "AI Settings"

    def __str__(self) -> str:
        return "AI Settings"


class ModelEndpoint(models.Model):
    """
    Registered model endpoints (LLM, embedding, vision, etc.)
    """

    KIND_CHOICES = [
        ("llm", "LLM"),
        ("embedding", "Embedding"),
        ("vision", "Vision"),
        ("speech", "Speech"),
    ]

    name = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="llm")
    provider = models.CharField(max_length=100)
    endpoint = models.URLField()
    api_key = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.provider})"


class KnowledgeSource(models.Model):
    """
    Knowledge base source registration (files, URLs, indexes).
    """

    SOURCE_CHOICES = [
        ("file", "File"),
        ("url", "URL"),
        ("db", "Database"),
        ("log", "Log Stream"),
    ]

    name = models.CharField(max_length=150)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="file")
    location = models.TextField(help_text="URI/path/connection string")
    metadata = models.JSONField(default=dict, blank=True)
    last_indexed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class Workflow(models.Model):
    """
    Declarative AI pipeline definition.
    """

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, default="")
    definition = models.JSONField(default=dict, blank=True, help_text="Declarative steps, tools, routing rules.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PipelineRun(models.Model):
    """
    Execution log for workflows/agents.
    """

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
    ]

    workflow = models.ForeignKey(Workflow, null=True, blank=True, on_delete=models.SET_NULL, related_name="runs")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["status"], name="ai_pipeline_status_idx"),
            models.Index(fields=["started_at"], name="ai_pipeline_started_idx"),
        ]

    def __str__(self) -> str:
        return f"Run {self.pk} ({self.status})"


