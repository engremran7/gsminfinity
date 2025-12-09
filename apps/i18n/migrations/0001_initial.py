from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Locale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=16, unique=True)),
                ("name", models.CharField(max_length=64)),
                ("direction", models.CharField(choices=[("ltr", "LTR"), ("rtl", "RTL")], default="ltr", max_length=3)),
                ("enabled_global", models.BooleanField(default=True)),
                ("enabled_for_apps", models.JSONField(blank=True, default=list)),
            ],
            options={
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="LanguageProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("app_id", models.CharField(db_index=True, max_length=64)),
                ("site_id", models.CharField(blank=True, db_index=True, max_length=64, null=True)),
                ("default_locale", models.CharField(default="en", max_length=16)),
                ("supported_locales", models.JSONField(blank=True, default=list)),
                ("fallback_locale", models.CharField(default="en", max_length=16)),
            ],
            options={
                "unique_together": {("app_id", "site_id")},
                "indexes": [models.Index(fields=["app_id", "site_id"], name="i18n_lang_profile_idx")],
            },
        ),
        migrations.CreateModel(
            name="TranslationKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("app_id", models.CharField(db_index=True, max_length=64)),
                ("namespace", models.CharField(db_index=True, default="common", max_length=64)),
                ("key", models.CharField(db_index=True, max_length=256)),
                ("context", models.TextField(blank=True, default="")),
                ("workflow_state", models.CharField(choices=[("draft", "Draft"), ("in_review", "In Review"), ("approved", "Approved"), ("deprecated", "Deprecated")], default="draft", max_length=20)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="i18n_keys_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("app_id", "namespace", "key")},
                "indexes": [models.Index(fields=["app_id", "namespace", "key"], name="i18n_tkey_idx")],
            },
        ),
        migrations.CreateModel(
            name="FontRegistry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=64, unique=True)),
                ("family", models.CharField(max_length=128)),
                ("urls", models.JSONField(blank=True, default=list)),
                ("weight_map", models.JSONField(blank=True, default=dict)),
                ("font_display", models.CharField(default="swap", max_length=16)),
                ("is_default_for_locales", models.JSONField(blank=True, default=list)),
                ("metadata", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="MissingKeyLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("app_id", models.CharField(db_index=True, max_length=64)),
                ("site_id", models.CharField(blank=True, db_index=True, max_length=64, null=True)),
                ("locale", models.CharField(db_index=True, max_length=16)),
                ("key", models.CharField(db_index=True, max_length=256)),
                ("route", models.CharField(blank=True, default="", max_length=256)),
                ("user_id", models.CharField(blank=True, max_length=64, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["app_id", "locale"], name="i18n_missing_app_locale_idx"),
                    models.Index(fields=["created_at"], name="i18n_missing_created_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Theme",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("app_id", models.CharField(db_index=True, max_length=64)),
                ("site_id", models.CharField(blank=True, db_index=True, max_length=64, null=True)),
                ("name", models.CharField(max_length=100)),
                ("mode", models.CharField(choices=[("light", "Light"), ("dark", "Dark"), ("high_contrast", "High Contrast")], default="light", max_length=20)),
                ("tokens", models.JSONField(blank=True, default=dict)),
                ("locale_overrides", models.JSONField(blank=True, default=dict)),
                ("is_locked", models.BooleanField(default=False, help_text="Prevents overriding core brand tokens.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("inherits_from", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="children", to="i18n.theme")),
            ],
            options={
                "unique_together": {("app_id", "site_id", "name", "mode")},
                "indexes": [models.Index(fields=["app_id", "site_id", "mode"], name="i18n_theme_app_site_mode_idx")],
            },
        ),
        migrations.CreateModel(
            name="ThemeAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("app_id", models.CharField(db_index=True, max_length=64)),
                ("site_id", models.CharField(blank=True, db_index=True, max_length=64, null=True)),
                ("route", models.CharField(blank=True, max_length=256, null=True)),
                ("user_id", models.CharField(blank=True, max_length=64, null=True)),
                ("device_pref", models.CharField(blank=True, max_length=20, null=True)),
                ("system_pref", models.CharField(blank=True, max_length=20, null=True)),
                ("scope", models.CharField(choices=[("global", "Global"), ("site", "Site"), ("route", "Route"), ("user", "User"), ("device", "Device Preference"), ("system", "System Preference")], default="global", max_length=16)),
                ("theme", models.ForeignKey(on_delete=models.CASCADE, related_name="assignments", to="i18n.theme")),
            ],
            options={
                "indexes": [models.Index(fields=["app_id", "site_id", "scope"], name="i18n_theme_assignment_idx")],
            },
        ),
        migrations.CreateModel(
            name="TranslationValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("locale", models.CharField(db_index=True, max_length=16)),
                ("message", models.TextField()),
                ("status", models.CharField(choices=[("draft", "Draft"), ("in_review", "In Review"), ("approved", "Approved"), ("deprecated", "Deprecated")], default="draft", max_length=20)),
                ("version", models.PositiveIntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("translation_key", models.ForeignKey(on_delete=models.CASCADE, related_name="values", to="i18n.translationkey")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="i18n_values_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("translation_key", "locale")},
                "indexes": [models.Index(fields=["locale", "status"], name="i18n_tvalue_locale_status_idx")],
            },
        ),
        migrations.CreateModel(
            name="AppManifest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("app_id", models.CharField(max_length=64, unique=True)),
                ("site_id", models.CharField(blank=True, max_length=64, null=True)),
                ("namespaces", models.JSONField(blank=True, default=list)),
                ("token_usage", models.JSONField(blank=True, default=list)),
                ("supported_locales", models.JSONField(blank=True, default=list)),
                ("default_locale", models.CharField(default="en", max_length=16)),
                ("routes", models.JSONField(blank=True, default=list)),
                ("version", models.PositiveIntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "indexes": [models.Index(fields=["app_id"], name="i18n_manifest_app_idx")],
            },
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=64)),
                ("app_id", models.CharField(blank=True, max_length=64, null=True)),
                ("before", models.JSONField(blank=True, default=dict)),
                ("after", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="i18n_theme_audits", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
