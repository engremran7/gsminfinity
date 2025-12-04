
from __future__ import annotations

import logging
import socket
import ipaddress
import hashlib
import urllib.request
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.db.models import Q, Count
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import user_passes_test
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from apps.blog.models import Post
from apps.core.app_service import AppService
from apps.core.utils import feature_flags
from apps.consent.utils import check as consent_check
from .models import SEOModel, Metadata, SitemapEntry, Redirect, LinkableEntity, LinkSuggestion
from apps.seo.services.ai.metadata import generate_metadata
from apps.seo.services.scoring.serp import serp_analyze
from apps.seo.services.readability import readability_score
from apps.seo.services.crawlers.heatmap import heatmap
from apps.core.utils.logging import log_event

logger = logging.getLogger(__name__)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _seo_settings() -> dict:
    try:
        seo_api = AppService.get("seo")
        if seo_api and hasattr(seo_api, "get_settings"):
            return seo_api.get_settings()
    except Exception:
        pass
    return {}


def _seo_enabled() -> bool:
    try:
        return bool(_seo_settings().get("seo_enabled", True))
    except Exception:
        return feature_flags.seo_enabled()


def _seo_auto_meta_enabled() -> bool:
    try:
        return bool(_seo_settings().get("auto_meta_enabled", False))
    except Exception:
        return False


def _has_seo_consent(request: HttpRequest) -> bool:
    return consent_check("analytics", request)


def _is_private_host(hostname: str) -> bool:
    if not hostname:
        return True
    try:
        infos = socket.getaddrinfo(hostname, None)
    except Exception:
        return True

    for fam, _, _, _, sockaddr in infos:
        ip = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
        ):
            return True
    return False


staff_or_editor = user_passes_test(
    lambda u: u.is_staff
    or u.is_superuser
    or getattr(u, "has_role", lambda *r: False)("admin", "editor")
)


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
            "title": m.meta_title,
            "description": m.meta_description,
            "keywords": m.focus_keywords,
            "canonical_url": m.canonical_url,
            "og_image": m.social_image,
        }
    )


@staff_or_editor
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
        log_event(
            logger,
            "info",
            "seo.metadata.regenerated",
            object_id=obj_id,
            content_type=ct_id,
            locked=seo_obj.locked,
            ai_generated=True,
        )
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


@staff_or_editor
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
        log_event(
            logger,
            "info",
            "seo.metadata.controls",
            action=action,
            locked=seo_obj.locked,
            object_id=obj_id,
        )
        return JsonResponse({"ok": True, "locked": seo_obj.locked, "focus_keywords": meta.focus_keywords})
    except Exception as exc:
        logger.error("update_metadata_controls failed", exc_info=True)
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@staff_or_editor
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
        log_event(
            logger,
            "info",
            "seo.link_suggestion.applied",
            suggestion_id=suggestion_id,
            locked=sug.locked,
            applied=sug.is_applied,
        )
        return JsonResponse({"ok": True})
    except LinkSuggestion.DoesNotExist:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)


@require_GET
def inspect_url_view(request: HttpRequest) -> JsonResponse:
    if not _seo_enabled() or not _has_seo_consent(request):
        return JsonResponse({"ok": False, "error": "seo_disabled"}, status=403)

    allowed_hosts = getattr(settings, "SEO_INSPECT_ALLOWLIST", ())
    raw_url = (request.GET.get("url") or "").strip()
    if not raw_url:
        return JsonResponse({"ok": False, "error": "missing_url"}, status=400)

    if not raw_url.startswith(("http://", "https://")):
        raw_url = "https://" + raw_url

    try:
        parsed = urlparse(raw_url)
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid_url"}, status=400)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return JsonResponse({"ok": False, "error": "invalid_url"}, status=400)

    hostname = parsed.hostname or ""
    if allowed_hosts and hostname not in allowed_hosts:
        return JsonResponse({"ok": False, "error": "forbidden_target"}, status=400)

    if _is_private_host(hostname):
        return JsonResponse({"ok": False, "error": "forbidden_target"}, status=400)

    try:
        req = urllib.request.Request(raw_url, method="HEAD")
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(req, timeout=5) as resp:
            headers = {k: v for k, v in resp.headers.items()}
            return JsonResponse({"ok": True, "status": resp.getcode(), "headers": headers})
    except Exception as exc:
        logger.exception("inspect_url_view failed", extra={"url": raw_url})
        return JsonResponse({"ok": False, "error": "fetch_failed"}, status=400)


@staff_or_editor
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
        log_event(logger, "info", "seo.redirect.updated", action=action, source=source, target=target)
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
    flags = {
        "seo_enabled": _seo_enabled(),
        "auto_meta_enabled": _seo_auto_meta_enabled(),
        "auto_schema_enabled": bool(_seo_settings().get("auto_schema_enabled", False)),
        "auto_linking_enabled": bool(_seo_settings().get("auto_linking_enabled", False)),
    }
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
            "flags": flags,
        },
    )





