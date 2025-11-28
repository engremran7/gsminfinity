# Generated manually to align Ads models with enterprise spec.
from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
from django.utils.text import slugify


def populate_codes_and_links(apps, schema_editor):
    AdPlacement = apps.get_model("ads", "AdPlacement")
    AffiliateLink = apps.get_model("ads", "AffiliateLink")

    for placement in AdPlacement.objects.all():
        code = getattr(placement, "code", None)
        if not code:
            base = getattr(placement, "slug", "") or slugify(getattr(placement, "name", "placement"))
            placement.code = (base or f"placement-{placement.pk}")[:120]
        if not getattr(placement, "context", "") and getattr(placement, "page_context", ""):
            placement.context = placement.page_context
        placement.is_active = placement.is_enabled
        placement.save(update_fields=["code", "context", "is_active"])

    for link in AffiliateLink.objects.all():
        if not getattr(link, "target_url", ""):
            link.target_url = getattr(link, "url", "") or ""
        if not getattr(link, "affiliate_url", ""):
            link.affiliate_url = getattr(link, "url", "") or ""
        if not getattr(link, "slug", ""):
            base = slugify(getattr(link, "name", "link")) or "link"
            link.slug = f"{base}-{link.pk or ''}".strip("-")[:180]
        link.save(update_fields=["target_url", "affiliate_url", "slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("tags", "0002_tag_normalized_description_usage"),
        ("ads", "0002_adplacement_template_reference"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # AdPlacement fields
        migrations.AddField(
            model_name="adplacement",
            name="code",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="adplacement",
            name="context",
            field=models.CharField(blank=True, default="", help_text="Page context e.g. blog_detail, blog_list, homepage", max_length=100),
        ),
        migrations.AddField(
            model_name="adplacement",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="adplacement_created", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="adplacement",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="adplacement",
            name="deleted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="adplacement_deleted", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="adplacement",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="adplacement",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="adplacement",
            name="updated_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="adplacement_updated", to=settings.AUTH_USER_MODEL),
        ),
        # Campaign fields
        migrations.AddField(
            model_name="campaign",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="campaign_created", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="campaign",
            name="daily_cap",
            field=models.PositiveIntegerField(default=0, help_text="0 = unlimited"),
        ),
        migrations.AddField(
            model_name="campaign",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="campaign",
            name="deleted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="campaign_deleted", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="campaign",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="campaign",
            name="priority",
            field=models.IntegerField(default=0, help_text="Higher wins ties"),
        ),
        migrations.AddField(
            model_name="campaign",
            name="targeting_rules",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="campaign",
            name="total_cap",
            field=models.PositiveIntegerField(default=0, help_text="0 = unlimited"),
        ),
        migrations.AddField(
            model_name="campaign",
            name="type",
            field=models.CharField(choices=[("direct", "Direct"), ("affiliate", "Affiliate"), ("network", "Network"), ("house", "House")], default="direct", max_length=20),
        ),
        migrations.AddField(
            model_name="campaign",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="campaign",
            name="updated_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="campaign_updated", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="campaign",
            name="weight",
            field=models.PositiveIntegerField(default=1),
        ),
        # AdCreative fields
        migrations.AddField(
            model_name="adcreative",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="adcreative_created", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="adcreative",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="adcreative",
            name="deleted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="adcreative_deleted", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="adcreative",
            name="html_code",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="adcreative",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="adcreative",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="adcreative",
            name="script_code",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="adcreative",
            name="tracking_params",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="adcreative",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="adcreative",
            name="updated_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="adcreative_updated", to=settings.AUTH_USER_MODEL),
        ),
        # PlacementAssignment fields
        migrations.AddField(
            model_name="placementassignment",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="placementassignment_created", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="placementassignment",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="placementassignment",
            name="deleted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="placementassignment_deleted", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="placementassignment",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="placementassignment",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="placementassignment",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="placementassignment",
            name="updated_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="placementassignment_updated", to=settings.AUTH_USER_MODEL),
        ),
        # AffiliateSource fields
        migrations.AddField(
            model_name="affiliatesource",
            name="base_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="affiliatesource",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="affiliatesource",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="affiliatesource_created", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="affiliatesource",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="affiliatesource",
            name="deleted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="affiliatesource_deleted", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="affiliatesource",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="affiliatesource",
            name="tracking_parameters",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="affiliatesource",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="affiliatesource",
            name="updated_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="affiliatesource_updated", to=settings.AUTH_USER_MODEL),
        ),
        # AffiliateLink fields
        migrations.AddField(
            model_name="affiliatelink",
            name="affiliate_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="affiliatelink_created", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="deleted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="affiliatelink_deleted", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="last_used_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="slug",
            field=models.SlugField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="target_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="updated_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="affiliatelink_updated", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="usage_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="affiliatelink",
            name="tags",
            field=models.ManyToManyField(blank=True, related_name="affiliate_links", to="tags.tag"),
        ),
        # AdEvent fields
        migrations.AddField(
            model_name="adevent",
            name="page_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="adevent",
            name="referrer_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="adevent",
            name="session_id",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="adevent",
            name="site_domain",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="adevent",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="adevent",
            name="user_agent",
            field=models.TextField(blank=True, default=""),
        ),
        # Data migration for codes/links
        migrations.RunPython(populate_codes_and_links, reverse_code=migrations.RunPython.noop),
        # Finalize AdPlacement.code constraints
        migrations.AlterField(
            model_name="adplacement",
            name="code",
            field=models.CharField(help_text="Stable placement code used in templates and auto-discovery.", max_length=120, unique=True),
        ),
    ]
