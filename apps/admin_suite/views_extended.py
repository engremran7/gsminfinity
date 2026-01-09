"""
Admin Suite Extended Views - Additional App Management

Views for:
- i18n (Languages, Translations)
- Devices (Device Settings, Policies)
- AI (Endpoints, Knowledge Bases, Workflows)
- Core (Feature Toggles)
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_protect

from .views_shared import _ADMIN_DISABLED, _make_breadcrumb, _render_admin

logger = logging.getLogger(__name__)


# =============================================================================
# I18N / LOCALIZATION MANAGEMENT
# =============================================================================


@csrf_protect
@staff_member_required
def admin_suite_i18n(request: HttpRequest) -> HttpResponse:
    """Internationalization dashboard - Languages, Translations."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "total_languages": 0,
        "active_languages": 0,
        "total_keys": 0,
        "total_translations": 0,
        "missing_translations": 0,
        "translation_coverage": 0,
    }
    languages = []
    recent_missing = []
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.i18n.models import Language

            if action == "toggle_language":
                lang_id = request.POST.get("language_id")
                lang = Language.objects.filter(pk=lang_id).first()
                if lang:
                    lang.is_active = not lang.is_active
                    lang.save(update_fields=["is_active"])
                    message = f"Language {'enabled' if lang.is_active else 'disabled'}."
            elif action == "create_language":
                code = (request.POST.get("code") or "").strip()[:10]
                name = (request.POST.get("name") or "").strip()[:64]
                native_name = (request.POST.get("native_name") or "").strip()[:64]
                if code and name:
                    Language.objects.create(
                        code=code,
                        name=name,
                        native_name=native_name or name,
                        is_active=True,
                    )
                    message = f"Language '{name}' created."
        except Exception as exc:
            logger.warning("i18n admin action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.i18n.models import (
            Language,
            MissingTranslation,
            Translation,
            TranslationKey,
        )

        all_languages = Language.objects.all().order_by("-is_active", "name")
        stats["total_languages"] = all_languages.count()
        stats["active_languages"] = all_languages.filter(is_active=True).count()
        stats["total_keys"] = TranslationKey.objects.count()
        stats["total_translations"] = Translation.objects.count()
        stats["missing_translations"] = MissingTranslation.objects.filter(
            is_resolved=False
        ).count()

        if stats["total_keys"] > 0 and stats["active_languages"] > 0:
            expected = stats["total_keys"] * stats["active_languages"]
            stats["translation_coverage"] = (
                round((stats["total_translations"] / expected) * 100, 1)
                if expected > 0
                else 0
            )

        languages = list(
            all_languages[:50].values(
                "id", "code", "name", "native_name", "is_active", "is_rtl", "flag_emoji"
            )
        )

        recent_missing = list(
            MissingTranslation.objects.filter(is_resolved=False)
            .select_related("language")
            .order_by("-created_at")[:20]
            .values("id", "key", "language__code", "context", "created_at")
        )
    except Exception as exc:
        logger.debug("Failed to load i18n data: %s", exc)

    return _render_admin(
        request,
        "admin_suite/i18n.html",
        {
            "stats": stats,
            "languages": languages,
            "recent_missing": recent_missing,
            "message": message,
        },
        nav_active="i18n",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Localization", None),
        ),
        subtitle="Languages & Translations",
    )


@csrf_protect
@staff_member_required
def admin_suite_i18n_translations(request: HttpRequest) -> HttpResponse:
    """Translation management view."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    query = (request.GET.get("q") or "").strip()
    lang_filter = (request.GET.get("lang") or "").strip()
    page = max(1, int(request.GET.get("page", "1") or "1"))
    page_size = 50
    offset = (page - 1) * page_size

    translations = []
    languages = []
    keys = []
    total_count = 0
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.i18n.models import Language, Translation, TranslationKey

            if action == "save_translation":
                key_id = request.POST.get("key_id")
                lang_id = request.POST.get("language_id")
                value = request.POST.get("value", "")
                key = TranslationKey.objects.filter(pk=key_id).first()
                lang = Language.objects.filter(pk=lang_id).first()
                if key and lang:
                    Translation.objects.update_or_create(
                        key=key, language=lang, defaults={"value": value}
                    )
                    message = "Translation saved."
        except Exception as exc:
            logger.warning("Translation action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.i18n.models import Language, Translation, TranslationKey

        languages = list(
            Language.objects.filter(is_active=True)
            .order_by("name")
            .values("id", "code", "name")
        )

        qs = TranslationKey.objects.all()
        if query:
            qs = qs.filter(key__icontains=query)

        total_count = qs.count()
        keys = list(
            qs.order_by("key")[offset : offset + page_size].values(
                "id", "key", "context", "created_at"
            )
        )

        # Get translations for these keys
        key_ids = [k["id"] for k in keys]
        trans_qs = Translation.objects.filter(key_id__in=key_ids).select_related(
            "language"
        )
        translations = {}
        for t in trans_qs:
            if t.key_id not in translations:
                translations[t.key_id] = {}
            translations[t.key_id][t.language.code] = t.value
    except Exception as exc:
        logger.debug("Failed to load translations: %s", exc)

    return _render_admin(
        request,
        "admin_suite/i18n_translations.html",
        {
            "keys": keys,
            "translations": translations,
            "languages": languages,
            "total_count": total_count,
            "query": query,
            "lang_filter": lang_filter,
            "page": page,
            "page_size": page_size,
            "message": message,
        },
        nav_active="i18n",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Localization", "admin_suite:i18n"),
            ("Translations", None),
        ),
        subtitle="Translation Strings",
    )


# =============================================================================
# DEVICES MANAGEMENT (Extended)
# =============================================================================


@csrf_protect
@staff_member_required
def admin_suite_devices_settings(request: HttpRequest) -> HttpResponse:
    """Device settings and policies management."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    device_settings = None
    policies = []
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.devices.models import DevicePolicy, DeviceSettings

            if action == "save_settings":
                ds = DeviceSettings.get_solo()
                ds.max_devices_per_user = int(request.POST.get("max_devices", 5))
                ds.device_timeout_days = int(request.POST.get("timeout_days", 30))
                ds.require_device_verification = bool(
                    request.POST.get("require_verification")
                )
                ds.save()
                message = "Device settings saved."
            elif action == "create_policy":
                app_label = (request.POST.get("app_label") or "").strip()[:64]
                max_devices = int(request.POST.get("max_devices", 3))
                if app_label:
                    DevicePolicy.objects.create(
                        app_label=app_label,
                        max_devices=max_devices,
                        is_active=True,
                    )
                    message = f"Policy for '{app_label}' created."
            elif action == "toggle_policy":
                policy_id = request.POST.get("policy_id")
                policy = DevicePolicy.objects.filter(pk=policy_id).first()
                if policy:
                    policy.is_active = not policy.is_active
                    policy.save(update_fields=["is_active"])
                    message = f"Policy {'enabled' if policy.is_active else 'disabled'}."
        except Exception as exc:
            logger.warning("Device settings action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.devices.models import DevicePolicy, DeviceSettings

        device_settings = DeviceSettings.get_solo()
        policies = list(
            DevicePolicy.objects.all()
            .order_by("app_label")
            .values("id", "app_label", "max_devices", "is_active", "created_at")
        )
    except Exception as exc:
        logger.debug("Failed to load device settings: %s", exc)

    return _render_admin(
        request,
        "admin_suite/devices_settings.html",
        {
            "device_settings": device_settings,
            "policies": policies,
            "message": message,
        },
        nav_active="devices",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Devices", "admin_suite:devices"),
            ("Settings", None),
        ),
        subtitle="Device Policies & Settings",
    )


# =============================================================================
# AI MANAGEMENT (Extended)
# =============================================================================


@csrf_protect
@staff_member_required
def admin_suite_ai_endpoints(request: HttpRequest) -> HttpResponse:
    """AI Endpoints management."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    endpoints = []
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.ai.models import AIEndpoint

            if action == "toggle_endpoint":
                endpoint_id = request.POST.get("endpoint_id")
                ep = AIEndpoint.objects.filter(pk=endpoint_id).first()
                if ep:
                    ep.is_active = not ep.is_active
                    ep.save(update_fields=["is_active"])
                    message = f"Endpoint {'enabled' if ep.is_active else 'disabled'}."
            elif action == "create_endpoint":
                name = (request.POST.get("name") or "").strip()[:128]
                provider = (request.POST.get("provider") or "").strip()[:64]
                model_id = (request.POST.get("model_id") or "").strip()[:128]
                endpoint_url = (request.POST.get("endpoint_url") or "").strip()[:512]
                if name and provider:
                    AIEndpoint.objects.create(
                        name=name,
                        provider=provider,
                        model_id=model_id,
                        endpoint_url=endpoint_url,
                        is_active=True,
                    )
                    message = f"Endpoint '{name}' created."
            elif action == "delete_endpoint":
                endpoint_id = request.POST.get("endpoint_id")
                AIEndpoint.objects.filter(pk=endpoint_id).delete()
                message = "Endpoint deleted."
        except Exception as exc:
            logger.warning("AI endpoint action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.ai.models import AIEndpoint

        endpoints = list(
            AIEndpoint.objects.all()
            .order_by("-is_active", "name")
            .values(
                "id",
                "name",
                "provider",
                "model_id",
                "endpoint_url",
                "is_active",
                "total_requests",
                "total_tokens",
                "average_latency_ms",
                "created_at",
            )
        )
    except Exception as exc:
        logger.debug("Failed to load AI endpoints: %s", exc)

    return _render_admin(
        request,
        "admin_suite/ai_endpoints.html",
        {
            "endpoints": endpoints,
            "message": message,
        },
        nav_active="ai",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("AI Settings", "admin_suite:ai_settings"),
            ("Endpoints", None),
        ),
        subtitle="AI Model Endpoints",
    )


@csrf_protect
@staff_member_required
def admin_suite_ai_knowledge(request: HttpRequest) -> HttpResponse:
    """AI Knowledge Bases management."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    knowledge_bases = []
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.ai.models import AIKnowledgeBase

            if action == "toggle_kb":
                kb_id = request.POST.get("kb_id")
                kb = AIKnowledgeBase.objects.filter(pk=kb_id).first()
                if kb:
                    kb.is_active = not kb.is_active
                    kb.save(update_fields=["is_active"])
                    message = (
                        f"Knowledge base {'enabled' if kb.is_active else 'disabled'}."
                    )
            elif action == "create_kb":
                name = (request.POST.get("name") or "").strip()[:128]
                description = (request.POST.get("description") or "").strip()
                if name:
                    AIKnowledgeBase.objects.create(
                        name=name,
                        description=description,
                        is_active=True,
                    )
                    message = f"Knowledge base '{name}' created."
        except Exception as exc:
            logger.warning("AI knowledge base action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.ai.models import AIKnowledgeBase

        knowledge_bases = list(
            AIKnowledgeBase.objects.all()
            .order_by("-is_active", "name")
            .values(
                "id",
                "name",
                "description",
                "is_active",
                "document_count",
                "total_chunks",
                "last_indexed_at",
                "created_at",
            )
        )
    except Exception as exc:
        logger.debug("Failed to load AI knowledge bases: %s", exc)

    return _render_admin(
        request,
        "admin_suite/ai_knowledge.html",
        {
            "knowledge_bases": knowledge_bases,
            "message": message,
        },
        nav_active="ai",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("AI Settings", "admin_suite:ai_settings"),
            ("Knowledge Bases", None),
        ),
        subtitle="RAG Knowledge Bases",
    )


@csrf_protect
@staff_member_required
def admin_suite_ai_workflows(request: HttpRequest) -> HttpResponse:
    """AI Workflows management."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    workflows = []
    recent_runs = []
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.ai.models import AIWorkflow

            if action == "toggle_workflow":
                wf_id = request.POST.get("workflow_id")
                wf = AIWorkflow.objects.filter(pk=wf_id).first()
                if wf:
                    wf.is_active = not wf.is_active
                    wf.save(update_fields=["is_active"])
                    message = f"Workflow {'enabled' if wf.is_active else 'disabled'}."
        except Exception as exc:
            logger.warning("AI workflow action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.ai.models import AIWorkflow, AIWorkflowRun

        workflows = list(
            AIWorkflow.objects.all()
            .order_by("-is_active", "name")
            .values(
                "id", "name", "description", "is_active", "trigger_type", "created_at"
            )
        )

        recent_runs = list(
            AIWorkflowRun.objects.select_related("workflow")
            .order_by("-started_at")[:30]
            .values(
                "id",
                "workflow__name",
                "status",
                "started_at",
                "completed_at",
                "error_message",
            )
        )
    except Exception as exc:
        logger.debug("Failed to load AI workflows: %s", exc)

    return _render_admin(
        request,
        "admin_suite/ai_workflows.html",
        {
            "workflows": workflows,
            "recent_runs": recent_runs,
            "message": message,
        },
        nav_active="ai",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("AI Settings", "admin_suite:ai_settings"),
            ("Workflows", None),
        ),
        subtitle="AI Automation Pipelines",
    )


# =============================================================================
# CORE / FEATURE TOGGLES
# =============================================================================


@csrf_protect
@staff_member_required
def admin_suite_features(request: HttpRequest) -> HttpResponse:
    """Feature toggles management."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    feature_settings = None
    feature_fields = []
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.core.models import FeatureSettings

            if action == "save_features":
                fs = FeatureSettings.get_solo()
                # Update all boolean feature flags from POST
                for field in fs._meta.get_fields():
                    if (
                        hasattr(field, "get_internal_type")
                        and field.get_internal_type() == "BooleanField"
                    ):
                        field_name = field.name
                        if field_name in request.POST:
                            setattr(fs, field_name, True)
                        else:
                            setattr(fs, field_name, False)
                fs.save()
                message = "Feature settings saved."
        except Exception as exc:
            logger.warning("Feature settings action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.core.models import FeatureSettings

        feature_settings = FeatureSettings.get_solo()

        # Build list of feature fields for template (can't access _meta in templates)
        for field in feature_settings._meta.get_fields():
            if (
                hasattr(field, "get_internal_type")
                and field.get_internal_type() == "BooleanField"
            ):
                feature_fields.append(
                    {
                        "name": field.name,
                        "verbose_name": getattr(field, "verbose_name", field.name)
                        .replace("_", " ")
                        .title(),
                        "help_text": getattr(field, "help_text", ""),
                        "value": getattr(feature_settings, field.name, False),
                    }
                )
    except Exception as exc:
        logger.debug("Failed to load feature settings: %s", exc)

    return _render_admin(
        request,
        "admin_suite/features.html",
        {
            "feature_settings": feature_settings,
            "feature_fields": feature_fields,
            "message": message,
        },
        nav_active="features",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Feature Toggles", None),
        ),
        subtitle="Enable/Disable Features",
    )


# =============================================================================
# BLOG MANAGEMENT (Extended)
# =============================================================================


@csrf_protect
@staff_member_required
def admin_suite_blog_posts(request: HttpRequest) -> HttpResponse:
    """Blog posts management."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    posts = []
    categories = []
    query = (request.GET.get("q") or "").strip()
    status_filter = (request.GET.get("status") or "").strip()
    page = max(1, int(request.GET.get("page", "1") or "1"))
    page_size = 25
    offset = (page - 1) * page_size
    total_count = 0
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.blog.models import Post

            if action == "toggle_publish":
                post_id = request.POST.get("post_id")
                post = Post.objects.filter(pk=post_id).first()
                if post:
                    post.is_published = not post.is_published
                    post.save(update_fields=["is_published"])
                    message = (
                        f"Post {'published' if post.is_published else 'unpublished'}."
                    )
            elif action == "delete_post":
                post_id = request.POST.get("post_id")
                Post.objects.filter(pk=post_id).delete()
                message = "Post deleted."
        except Exception as exc:
            logger.warning("Blog post action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.blog.models import Category, Post

        categories = list(
            Category.objects.all().order_by("name").values("id", "name", "slug")
        )

        qs = Post.objects.select_related("author", "category").all()
        if query:
            qs = qs.filter(title__icontains=query)
        if status_filter == "published":
            qs = qs.filter(is_published=True)
        elif status_filter == "draft":
            qs = qs.filter(is_published=False)

        total_count = qs.count()
        posts = list(
            qs.order_by("-created_at")[offset : offset + page_size].values(
                "id",
                "title",
                "slug",
                "author__email",
                "category__name",
                "is_published",
                "is_featured",
                "view_count",
                "created_at",
                "published_at",
            )
        )
    except Exception as exc:
        logger.debug("Failed to load blog posts: %s", exc)

    return _render_admin(
        request,
        "admin_suite/blog_posts.html",
        {
            "posts": posts,
            "categories": categories,
            "total_count": total_count,
            "query": query,
            "status_filter": status_filter,
            "page": page,
            "page_size": page_size,
            "message": message,
        },
        nav_active="blog",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Blog", "admin_suite:blog"),
            ("Posts", None),
        ),
        subtitle="Blog Post Management",
    )


# =============================================================================
# CRAWLER GUARD MANAGEMENT
# =============================================================================


@csrf_protect
@staff_member_required
def admin_suite_crawler_rules(request: HttpRequest) -> HttpResponse:
    """Crawler guard rules management."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    rules = []
    recent_logs = []
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.crawler_guard.models import CrawlerRule

            if action == "toggle_rule":
                rule_id = request.POST.get("rule_id")
                rule = CrawlerRule.objects.filter(pk=rule_id).first()
                if rule:
                    rule.is_active = not rule.is_active
                    rule.save(update_fields=["is_active"])
                    message = f"Rule {'enabled' if rule.is_active else 'disabled'}."
            elif action == "create_rule":
                name = (request.POST.get("name") or "").strip()[:128]
                pattern = (request.POST.get("pattern") or "").strip()
                action_type = (request.POST.get("action_type") or "block").strip()
                if name and pattern:
                    CrawlerRule.objects.create(
                        name=name,
                        user_agent_pattern=pattern,
                        action=action_type,
                        is_active=True,
                    )
                    message = f"Rule '{name}' created."
        except Exception as exc:
            logger.warning("Crawler rule action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.crawler_guard.models import CrawlerLog, CrawlerRule

        rules = list(
            CrawlerRule.objects.all()
            .order_by("-is_active", "name")
            .values(
                "id",
                "name",
                "user_agent_pattern",
                "ip_pattern",
                "action",
                "is_active",
                "hit_count",
                "created_at",
            )
        )

        recent_logs = list(
            CrawlerLog.objects.order_by("-created_at")[:50].values(
                "id", "user_agent", "ip_address", "path", "action_taken", "created_at"
            )
        )
    except Exception as exc:
        logger.debug("Failed to load crawler rules: %s", exc)

    return _render_admin(
        request,
        "admin_suite/crawler_rules.html",
        {
            "rules": rules,
            "recent_logs": recent_logs,
            "message": message,
        },
        nav_active="crawlers",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Security", "admin_suite:security"),
            ("Crawler Rules", None),
        ),
        subtitle="Bot Detection Rules",
    )


__all__ = [
    # i18n
    "admin_suite_i18n",
    "admin_suite_i18n_translations",
    # Devices
    "admin_suite_devices_settings",
    # AI Extended
    "admin_suite_ai_endpoints",
    "admin_suite_ai_knowledge",
    "admin_suite_ai_workflows",
    # Core
    "admin_suite_features",
    # Blog Extended
    "admin_suite_blog_posts",
    # Crawler Guard
    "admin_suite_crawler_rules",
]
