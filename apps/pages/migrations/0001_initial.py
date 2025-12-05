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
            name="Page",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=200, unique=True)),
                ("title", models.CharField(max_length=200)),
                ("content", models.TextField()),
                (
                    "content_format",
                    models.CharField(
                        choices=[("md", "Markdown"), ("html", "HTML")],
                        default="md",
                        max_length=8,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")],
                        default="draft",
                        max_length=12,
                    ),
                ),
                ("publish_at", models.DateTimeField(blank=True, null=True)),
                ("unpublish_at", models.DateTimeField(blank=True, null=True)),
                ("seo_title", models.CharField(blank=True, max_length=200)),
                ("seo_description", models.CharField(blank=True, max_length=300)),
                ("og_image", models.ImageField(blank=True, null=True, upload_to="pages/og/")),
                (
                    "access_level",
                    models.CharField(
                        choices=[("public", "Public"), ("auth", "Authenticated"), ("staff", "Staff")],
                        default="public",
                        max_length=12,
                    ),
                ),
                ("include_in_sitemap", models.BooleanField(default=True)),
                (
                    "changefreq",
                    models.CharField(
                        choices=[
                            ("always", "always"),
                            ("hourly", "hourly"),
                            ("daily", "daily"),
                            ("weekly", "weekly"),
                            ("monthly", "monthly"),
                            ("yearly", "yearly"),
                            ("never", "never"),
                        ],
                        default="weekly",
                        max_length=12,
                    ),
                ),
                ("priority", models.DecimalField(decimal_places=1, default=0.5, max_digits=2)),
                ("canonical_url", models.URLField(blank=True, default="")),
                ("last_modified", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pages_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pages_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["slug"],
            },
        ),
    ]
