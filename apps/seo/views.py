from __future__ import annotations

import logging
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.db.models import Q, Count
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import user_passes_test
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.csrf import csrf_exempt
import hashlib
import urllib.request
from urllib.error import HTTPError, URLError

from apps.blog.models import Post
from apps.core.utils import feature_flags
from .models import SEOModel, Metadata, SitemapEntry, Redirect, LinkableEntity, LinkSuggestion
from apps.seo.services.ai.metadata import generate_metadata
from apps.seo.services.scoring.serp import serp_analyze
from apps.seo.services.readability import readability_score
from apps.seo.services.crawlers.heatmap import heatmap

logger = logging.getLogger(__name__)


def _seo_enabled() -> bool:
    return feature_flags.seo_enabled()


def _has_seo_consent(request: HttpRequest) -> bool:
    consent = getattr(request, "consent_categories", {}) or {}
    if consent and not consent.get("functional", True):
        return False
    # If analytics category exists, require it for SEO inspection endpoints
    if "analytics" in consent and not consent.get("analytics", False):
        return False
    return True


@require_GET
def metadata_view(request: HttpRequest) -> JsonResponse:
    if not _seo_enabled() or not _has_seo_consent(request):
        return JsonResponse({"items": []})
    ct_id = request.GET.get("content_type")
    obj_id = request.GET.get("object_id")
    if not ct_id or not obj_id:
        return JsonResponse({"items": []})
    try:
        ct = ContentType.objects.get_for_id(ct_id)
        seo_obj = SEOModel.objects.filter(content_type=ct, object_id=obj_id).first()
    except Exception:
        seo_obj = None
    if not seo_obj or not hasattr(seo_obj, "metadata"):
        return JsonResponse({"items": []})
    m = seo_obj.metadata
    return JsonResponse(
        {
            "title": m.title,
            "description": m.description,
            "keywords": m.keywords,
            "canonical_url": m.canonical_url,
            "og_image": m.og_image,
        }
    )


@csrf_exempt
@require_POST
def regenerate_metadata(request: HttpRequest) -> JsonResponse:
    """
    Explicit AI regeneration; respects locks and content delta.
    """
    if not _seo_enabled() or not _has_seo_consent(request):
        return JsonResponse({"ok": False, "error": "seo_disabled"}, status=403)
    ct_id = request.POST.get("content_type")
    obj_id = request.POST.get("object_id")
    text = request.POST.get("text") or ""
    force = request.POST.get("force") == "1"
    lock = request.POST.get("lock") == "1"
    focus_keywords_raw = request.POST.get("focus_keywords") or ""
    if not ct_id or not obj_id or not text:
        return JsonResponse({"ok": False, "error": "missing_params"}, status=400)
    try:
        ct = ContentType.objects.get_for_id(ct_id)
        seo_obj, _ = SEOModel.objects.get_or_create(content_type=ct, object_id=obj_id)
        if seo_obj.locked and not force:
            return JsonResponse({"ok": False, "error": "locked"}, status=403)
        meta, _ = Metadata.objects.get_or_create(seo=seo_obj)
        content_hash = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
        if meta.content_hash and meta.content_hash == content_hash and not force:
            return JsonResponse({"ok": True, "skipped": True})
        data = generate_metadata(text, request.user)
        meta.title = data.get("title", "")[:255]
        meta.description = data.get("description", "")[:320]
        meta.keywords = data.get("keywords", "")
        if focus_keywords_raw:
            meta.focus_keywords = [kw.strip() for kw in focus_keywords_raw.split(",") if kw.strip()]
        meta.content_hash = content_hash
        meta.save()
        seo_obj.ai_generated = True
        seo_obj.locked = lock or seo_obj.locked
        seo_obj.save(update_fields=["ai_generated", "locked", "updated_at"])
        logger.info("SEO metadata regenerated", extra={"object_id": obj_id, "content_type": ct_id, "locked": seo_obj.locked})
        return JsonResponse(
            {
                "ok": True,
                "title": meta.title,
                "description": meta.description,
                "focus_keywords": meta.focus_keywords,
                "locked": seo_obj.locked,
            }
        )
    except Exception as exc:
        logger.error("regenerate_metadata failed", exc_info=True)
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@csrf_exempt
@require_POST
def update_metadata_controls(request: HttpRequest) -> JsonResponse:
    """
    Lock/unlock metadata and persist focus keywords without regeneration.
    """
    if not _seo_enabled() or not _has_seo_consent(request):
        return JsonResponse({"ok": False, "error": "seo_disabled"}, status=403)
    ct_id = request.POST.get("content_type")
    obj_id = request.POST.get("object_id")
    action = request.POST.get("action") or ""
    focus_keywords_raw = request.POST.get("focus_keywords") or ""
    if not ct_id or not obj_id:
        return JsonResponse({"ok": False, "error": "missing_params"}, status=400)
    try:
        ct = ContentType.objects.get_for_id(ct_id)
        seo_obj, _ = SEOModel.objects.get_or_create(content_type=ct, object_id=obj_id)
        meta, _ = Metadata.objects.get_or_create(seo=seo_obj)
        if action == "lock":
            seo_obj.locked = True
        elif action == "unlock":
            seo_obj.locked = False
        if focus_keywords_raw:
            meta.focus_keywords = [kw.strip() for kw in focus_keywords_raw.split(",") if kw.strip()]
            meta.save(update_fields=["focus_keywords", "updated_at"])
        seo_obj.save(update_fields=["locked", "updated_at"])
        return JsonResponse({"ok": True, "locked": seo_obj.locked, "focus_keywords": meta.focus_keywords})
    except Exception as exc:
        logger.error("update_metadata_controls failed", exc_info=True)
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@csrf_exempt
@require_POST
def apply_link_suggestion(request: HttpRequest) -> JsonResponse:
    if not _seo_enabled() or not _has_seo_consent(request):
        return JsonResponse({"ok": False, "error": "seo_disabled"}, status=403)
    suggestion_id = request.POST.get("id")
    lock = request.POST.get("lock") == "1"
    apply_flag = request.POST.get("apply") != "0"
    try:
        sug = LinkSuggestion.objects.get(pk=suggestion_id)
        if sug.locked and not lock:
            return JsonResponse({"ok": False, "error": "locked"}, status=403)
        sug.is_applied = apply_flag
        sug.locked = lock or sug.locked
        sug.save()
        return JsonResponse({"ok": True})
    except LinkSuggestion.DoesNotExist:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)


@require_GET
def inspect_url_view(request: HttpRequest) -> JsonResponse:
    if not _seo_enabled() or not _has_seo_consent(request):
        return JsonResponse({"ok": False, "error": "seo_disabled"}, status=403)
    url = request.GET.get("url", "")
    if not url:
        return JsonResponse({"ok": False, "error": "missing_url"}, status=400)
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=5) as resp:
            headers = {k: v for k, v in resp.headers.items()}
            return JsonResponse({"ok": True, "status": resp.getcode(), "headers": headers})
    except (HTTPError, URLError, Exception) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@csrf_exempt
@require_POST
def manage_redirect(request: HttpRequest) -> HttpResponse:
    if not _seo_enabled() or not _has_seo_consent(request):
        return JsonResponse({"ok": False, "error": "seo_disabled"}, status=403)
    action = request.POST.get("action") or "create"
    rid = request.POST.get("id")
    source = request.POST.get("source") or ""
    target = request.POST.get("target") or ""
    permanent = request.POST.get("is_permanent") == "1"
    active = request.POST.get("is_active") != "0"
    try:
        if action == "create":
            if not source or not target:
                return redirect("seo:dashboard")
            Redirect.objects.update_or_create(
                source=source,
                defaults={"target": target, "is_permanent": permanent, "is_active": active},
            )
        elif action in ("toggle_active", "toggle_permanent") and rid:
            redirect_obj = Redirect.objects.filter(pk=rid).first()
            if redirect_obj:
                if action == "toggle_active":
                    redirect_obj.is_active = not redirect_obj.is_active
                    redirect_obj.save(update_fields=["is_active"])
                else:
                    redirect_obj.is_permanent = not redirect_obj.is_permanent
                    redirect_obj.save(update_fields=["is_permanent"])
    except Exception as exc:
        logger.error("manage_redirect failed", exc_info=True)
    return redirect("seo:dashboard")


@user_passes_test(lambda u: u.is_staff or u.is_superuser or getattr(u, "has_role", lambda *r: False)("admin", "editor"))
def dashboard(request: HttpRequest) -> HttpResponse:
    suggestions = LinkSuggestion.objects.filter(is_applied=False).select_related("source", "target")[:50]
    redirects = Redirect.objects.all()[:50]
    sitemap_qs = SitemapEntry.objects.filter(is_active=True)
    sitemap_entries = sitemap_qs.order_by("-last_checked_at", "-created_at")[:50]
    link_issues = sitemap_qs.filter(last_status__gte=400).count()
    link_unknown = sitemap_qs.filter(Q(last_status__isnull=True) | Q(last_status=0)).count()
    recent_posts = Post.objects.order_by("-updated_at")[:15]
    post_ct = ContentType.objects.get_for_model(Post)
    missing_meta = Metadata.objects.filter(Q(meta_title="") | Q(meta_description="")).count()
    duplicate_titles = (
        Metadata.objects.exclude(meta_title="")
        .values("meta_title")
        .annotate(c=Count("id"))
        .filter(c__gt=1)
        .count()
    )
    serp_stats = serp_analyze(" ".join(recent_posts.values_list("seo_title", flat=True)[:1]), " ".join(recent_posts.values_list("seo_description", flat=True)[:1]))
    heatmap_stats = heatmap()
    return render(
        request,
        "seo/dashboard.html",
        {
            "seo_enabled": _seo_enabled(),
            "sitemaps": SitemapEntry.objects.count(),
            "redirects": Redirect.objects.count(),
            "entities": LinkableEntity.objects.count(),
            "suggestions": suggestions,
            "redirects_list": redirects,
            "sitemap_entries": sitemap_entries,
            "link_issues": link_issues,
            "link_unknown": link_unknown,
            "recent_posts": recent_posts,
            "post_content_type_id": post_ct.id,
            "missing_meta": missing_meta,
            "duplicate_titles": duplicate_titles,
            "serp_stats": serp_stats,
            "heatmap": heatmap_stats,
        },
    )
