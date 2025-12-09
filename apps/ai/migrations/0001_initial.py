from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AISettings",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ai_enabled", models.BooleanField(default=True)),
                ("default_model", models.CharField(default="deepseek-chat", max_length=100)),
                ("enable_vector_search", models.BooleanField(default=True)),
                ("enable_auto_translation", models.BooleanField(default=True)),
                ("enable_safety_firewall", models.BooleanField(default=True)),
                ("default_locale", models.CharField(default="en", max_length=16)),
                ("provider", models.CharField(default="deepseek", max_length=50)),
                ("base_url", models.URLField(blank=True, default="")),
                ("api_key", models.TextField(blank=True, default="")),
                ("model_name", models.CharField(default="deepseek-chat", max_length=100)),
                ("timeout_seconds", models.PositiveIntegerField(default=30)),
                ("max_tokens", models.PositiveIntegerField(default=1024)),
                ("temperature", models.DecimalField(decimal_places=2, default=0.30, max_digits=3)),
                ("log_prompts", models.BooleanField(default=False)),
                ("log_completions", models.BooleanField(default=False)),
                ("pii_redaction_enabled", models.BooleanField(default=True)),
                ("moderation_enabled", models.BooleanField(default=True)),
                ("allow_tools", models.BooleanField(default=False)),
                ("retry_limit", models.PositiveSmallIntegerField(default=3)),
                ("backoff_min_seconds", models.FloatField(default=0.5)),
                ("backoff_max_seconds", models.FloatField(default=4.0)),
            ],
            options={
                "verbose_name": "AI Settings",
            },
        ),
        migrations.CreateModel(
            name="KnowledgeSource",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("source_type", models.CharField(choices=[("file", "File"), ("url", "URL"), ("db", "Database"), ("log", "Log Stream")], default="file", max_length=20)),
                ("location", models.TextField(help_text="URI/path/connection string")),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("last_indexed_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ModelEndpoint",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("kind", models.CharField(choices=[("llm", "LLM"), ("embedding", "Embedding"), ("vision", "Vision"), ("speech", "Speech")], default="llm", max_length=20)),
                ("provider", models.CharField(max_length=100)),
                ("endpoint", models.URLField()),
                ("api_key", models.CharField(blank=True, default="", max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Workflow",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("definition", models.JSONField(blank=True, default=dict, help_text="Declarative steps, tools, routing rules.")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="PipelineRun",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("input_payload", models.JSONField(blank=True, default=dict)),
                ("output_payload", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed")], default="queued", max_length=20)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("workflow", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="runs", to="ai.workflow")),
            ],
            options={
                "ordering": ["-started_at"],
                "indexes": [
                    models.Index(fields=["status"], name="ai_pipeline_status_idx"),
                    models.Index(fields=["started_at"], name="ai_pipeline_started_idx"),
                ],
            },
        ),
    ]
