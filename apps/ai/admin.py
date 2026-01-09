from django.contrib import admin
from solo.admin import SingletonModelAdmin

from apps.ai.models import (
    AISettings,
    KnowledgeSource,
    ModelEndpoint,
    PipelineRun,
    Workflow,
)


@admin.register(AISettings)
class AISettingsAdmin(SingletonModelAdmin):
    list_display = (
        "ai_enabled",
        "default_model",
        "enable_vector_search",
        "enable_safety_firewall",
    )

    def has_add_permission(self, request):
        return False


@admin.register(ModelEndpoint)
class ModelEndpointAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "provider", "is_active", "updated_at")
    list_filter = ("kind", "is_active")
    search_fields = ("name", "provider")


@admin.register(KnowledgeSource)
class KnowledgeSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "is_active", "last_indexed_at")
    list_filter = ("source_type", "is_active")
    search_fields = ("name", "location")


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "updated_at")
    search_fields = ("name", "description")
    list_filter = ("is_active",)


@admin.register(PipelineRun)
class PipelineRunAdmin(admin.ModelAdmin):
    list_display = ("id", "workflow", "status", "started_at", "finished_at")
    list_filter = ("status", "started_at")
    search_fields = ("workflow__name",)
    readonly_fields = ("started_at",)
