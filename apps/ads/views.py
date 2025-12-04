
from __future__ import annotations

import logging
from collections import defaultdict

from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import user_passes_test
from django.core.cache import cache

from apps.core.app_service import AppService
from apps.core.utils import feature_flags
from .models import AdPlacement, AdEvent, Campaign, AdCreative, PlacementAssignment
from apps.ads.services.rotation.engine import choose_creative
from apps.ads.services.analytics.tracker import record_event as tracker_record_event
from apps.core.utils.logging import log_event
from apps.consent.utils import check as consent_check, hash_ip, hash_ua
from apps.ads.services import ai_optimizer
from apps.ads.services.schemas import AdRequest, AdResponse, CreativeSelection
from apps.core.utils.ip import get_client_ip
from apps.ads.services.targeting.engine import campaign_allowed
from apps.site_settings.models import SiteSettings

logger = logging.getLogger(__name__)


def _ads_settings() -> dict:
    try:
        ads_api = AppService.get("ads")
        if ads_api and hasattr(ads_api, "get_settings"):
            return ads_api.get_settings()
    except Exception:
        logger.exception("ads settings fetch failed")
    return {
        "ads_enabled": False,
        "affiliate_enabled": False,
        "ad_networks_enabled": False,
        "ad_aggressiveness_level": "balanced",
    }


def _ads_enabled() -> bool:
    try:
        settings_obj = _ads_settings()
        return bool(settings_obj.get("ads_enabled", False))
    except Exception:
        return feature_flags.ads_enabled()


def _has_ads_consent(request: HttpRequest) -> bool:
    """Honor consent categories; track events only when ads consent granted."""
    try:
        return consent_check("ads", request)
    except Exception:
        return False


def _log(request: HttpRequest, message: str, **extra):
    cid = getattr(request, "correlation_id", None)
    payload = {"correlation_id": cid, **extra}
    logger.info(message, extra=payload)
    try:
        log_event(logger, "info", message, **payload)
    except Exception:
        return


@require_GET
def list_placements(request: HttpRequest) -> JsonResponse:
    if not _ads_enabled():
        return JsonResponse({"items": []})
    placements = AdPlacement.objects.filter(is_enabled=True, is_active=True, is_deleted=False)
    data = [
        {
            "name": p.name,
            "slug": p.slug,
            "code": p.code,
            "allowed_types": p.allowed_types,
            "allowed_sizes": p.allowed_sizes,
            "page_context": p.context or p.page_context,
            "template_reference": p.template_reference,
        }
        for p in placements
    ]
    _log(request, "ads.list_placements", count=len(data))
    return JsonResponse({"items": data})


@csrf_protect
@require_POST
def record_event(request: HttpRequest) -> JsonResponse:
    if not _ads_enabled():
        return JsonResponse({"ok": False, "error": "ads_disabled"}, status=403)
    if not _has_ads_consent(request):
        return JsonResponse({"ok": True, "skipped": "no_consent"})
    event_type = (request.POST.get("event_type") or "").strip()
    placement_slug = (request.POST.get("placement") or "").strip()
    campaign_id = request.POST.get("campaign")
    creative_id = request.POST.get("creative")
    page_url = request.POST.get("page_url", "")
    referrer = request.POST.get("referrer", "")
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    consent_granted = request.POST.get("consent_granted") in ("1", "true", "True")
    if not placement_slug or event_type not in {"impression", "click"}:
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)
    if page_url and not page_url.startswith(("http://", "https://")):
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)
    # Basic abuse throttle per IP
    rl_key = f"ads:event:{get_client_ip(request) or 'anon'}"
    try:
        count = cache.get(rl_key, 0)
        if count and int(count) >= 50:
            return JsonResponse({"ok": False, "error": "rate_limited"}, status=429)
        cache.set(rl_key, int(count) + 1, timeout=60)
    except Exception:
        pass
    hashed_ip = hash_ip(get_client_ip(request))
    hashed_ua = hash_ua(user_agent)
    try:
        placement = AdPlacement.objects.filter(slug=placement_slug, is_enabled=True, is_active=True, is_deleted=False).first()
        if placement is None:
            return JsonResponse({"ok": False, "error": "invalid_placement"}, status=400)
        campaign = Campaign.objects.filter(pk=campaign_id).first() if campaign_id else None
        creative = AdCreative.objects.filter(pk=creative_id, is_enabled=True, is_active=True).first() if creative_id else None
        if creative:
            assigned = placement.assignments.filter(creative=creative, is_enabled=True, is_active=True).exists()
            if not assigned:
                return JsonResponse({"ok": False, "error": "invalid_mapping"}, status=400)
        if campaign and not campaign_allowed(campaign, {"consent_ads": consent_granted}):
            return JsonResponse({"ok": False, "error": "campaign_not_allowed"}, status=400)
        tracker_record_event(
            event_type or "impression",
            placement=placement,
            creative=creative,
            campaign=campaign,
            user=request.user if request.user.is_authenticated else None,
            request_meta={
                "ip": hashed_ip,
                "referrer": referrer,
                "user_agent": hashed_ua,
                "page_url": page_url,
                "consent_granted": consent_granted,
                "correlation_id": getattr(request, "correlation_id", None),
            },
        )
        _log(
            request,
            "ads_event_recorded",
            event_type=event_type,
            placement=placement_slug,
            campaign=str(campaign_id or ""),
            page_url=page_url,
        )
    except Exception:
        logger.exception("record_event failed", extra={"placement": placement_slug, "creative": creative_id})
        return JsonResponse({"ok": False}, status=400)
    return JsonResponse({"ok": True})


@require_GET
def fill_ad(request: HttpRequest) -> JsonResponse:
    """
    Returns a creative for a placement slug using rotation engine.
    """
    if not _ads_enabled():
        return JsonResponse({"ok": False, "error": "ads_disabled"}, status=403)
    if not _has_ads_consent(request):
        return JsonResponse({"ok": True, "skipped": "no_consent"})
    slug = request.GET.get("placement") or ""
    page_url = request.GET.get("page_url", "")
    if page_url and not page_url.startswith(("http://", "https://")):
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)
    if not slug:
        return JsonResponse({"ok": False, "error": "missing_placement"}, status=400)
    placement = AdPlacement.objects.filter(slug=slug, is_enabled=True, is_active=True, is_deleted=False).first()
    if not placement:
        return JsonResponse({"ok": False, "error": "placement_not_found"}, status=404)
    ad_request = AdRequest(
        placement_code=placement.code,
        page_url=page_url,
        referrer=request.META.get("HTTP_REFERER", ""),
        user_id=request.user.id if request.user.is_authenticated else None,
        session_id=request.session.session_key,
        consent_ads=_has_ads_consent(request),
        device=hash_ua(request.META.get("HTTP_USER_AGENT", "")),
        context={"ip": hash_ip(get_client_ip(request) or "")},
    )
    tags = set((request.GET.get("tags") or "").split(",")) if request.GET.get("tags") else set()
    context = {
        "consent_ads": _has_ads_consent(request),
        "page_context": placement.context or placement.page_context or request.GET.get("page_context"),
        "tags": tags,
    }
    creative: AdCreative | None = choose_creative(placement, context)
    if not creative:
        return JsonResponse({"ok": False, "error": "no_creative"}, status=404)
    ad_response = AdResponse(
        placement_code=placement.code,
        creatives=[CreativeSelection(creative_id=creative.id, campaign_id=getattr(creative, "campaign_id", None), weight=1)],
        tracking={"consent": ad_request.consent_ads, "correlation_id": getattr(request, "correlation_id", "")},
    )
    _log(
        request,
        "ads_fill",
        placement=slug,
        creative=str(getattr(creative, "id", "")),
        campaign=str(getattr(creative, "campaign_id", "")),
        page_url=page_url,
    )
    payload = {
        "type": creative.creative_type,
        "html": creative.html,
        "image_url": creative.image_url,
        "click_url": creative.click_url,
        "campaign": creative.campaign_id,
        "placement": placement.slug,
        "creative": creative.id,
        "page_url": page_url,
        "tracking": ad_response.tracking,
    }
    if _has_ads_consent(request):
        tracker_record_event(
            "impression",
            placement=placement,
            creative=creative,
            campaign=creative.campaign,
            user=request.user if request.user.is_authenticated else None,
            request_meta={
                "ip": hash_ip(get_client_ip(request) or ""),
                "referrer": request.META.get("HTTP_REFERER", ""),
                "user_agent": hash_ua(request.META.get("HTTP_USER_AGENT", "")),
                "page_url": request.GET.get("page_url", ""),
                "consent_granted": True,
                "correlation_id": getattr(request, "correlation_id", None),
            },
        )
    else:
        logger.info("Ads impression skipped due to missing consent", extra={"placement": placement.slug})
    return JsonResponse({"ok": True, "creative": payload})


@csrf_protect
@require_POST
def record_click(request: HttpRequest) -> JsonResponse:
    if not _ads_enabled():
        return JsonResponse({"ok": False, "error": "ads_disabled"}, status=403)
    if not _has_ads_consent(request):
        return JsonResponse({"ok": True, "skipped": "no_consent"})
    creative_id = (request.POST.get("creative") or "").strip()
    placement_slug = (request.POST.get("placement") or "").strip()
    if not creative_id or not placement_slug:
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)
    page_url = request.POST.get("page_url", "")
    referrer = request.POST.get("referrer", "")
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    if page_url and not page_url.startswith(("http://", "https://")):
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)
    # Basic abuse throttle per IP
    rl_key = f"ads:click:{get_client_ip(request) or 'anon'}"
    try:
        count = cache.get(rl_key, 0)
        if count and int(count) >= 30:
            return JsonResponse({"ok": False, "error": "rate_limited"}, status=429)
        cache.set(rl_key, int(count) + 1, timeout=60)
    except Exception:
        pass
    placement = AdPlacement.objects.filter(slug=placement_slug, is_enabled=True, is_active=True, is_deleted=False).first()
    if placement is None:
        return JsonResponse({"ok": False, "error": "invalid_placement"}, status=400)
    creative = AdCreative.objects.filter(pk=creative_id, is_enabled=True, is_active=True).first()
    if creative is None:
        return JsonResponse({"ok": False, "error": "invalid_creative"}, status=400)
    assigned = placement.assignments.filter(creative=creative, is_enabled=True, is_active=True).exists()
    if not assigned:
        return JsonResponse({"ok": False, "error": "invalid_mapping"}, status=400)
    if creative.campaign and not creative.campaign.is_live():
        return JsonResponse({"ok": False, "error": "campaign_not_live"}, status=400)
    try:
        tracker_record_event(
            "click",
            placement=placement,
            creative=creative,
            campaign=creative.campaign if creative else None,
            user=request.user if request.user.is_authenticated else None,
            request_meta={
                "ip": hash_ip(get_client_ip(request) or ""),
                "referrer": referrer,
                "user_agent": hash_ua(user_agent),
                "page_url": page_url,
                "consent_granted": True,
                "correlation_id": getattr(request, "correlation_id", None),
            },
        )
    except Exception:
        logger.exception("record_click failed", extra={"placement": placement_slug, "creative": creative_id})
        return JsonResponse({"ok": False}, status=400)
    return JsonResponse({"ok": True})


@user_passes_test(lambda u: u.is_staff or u.is_superuser or getattr(u, "has_role", lambda *r: False)("admin", "editor"))
def dashboard(request: HttpRequest) -> HttpResponse:
    # Basic CTR stats
    impressions = AdEvent.objects.filter(event_type="impression").count()
    clicks = AdEvent.objects.filter(event_type="click").count()
    ctr = (clicks / impressions * 100) if impressions else 0
    ss = _ads_settings()
    placements = AdPlacement.objects.all()[:50]
    campaigns = Campaign.objects.all()[:50]
    creatives = AdCreative.objects.select_related("campaign")[:50]
    affiliate_sources = Campaign.objects.none()
    try:
        from apps.ads.models import AffiliateSource
        affiliate_sources = AffiliateSource.objects.all()[:10]
    except Exception:
        affiliate_sources = []
    # Fill stats per placement / creative
    placement_stats = {}
    creative_stats = {}
    for p in placements:
        imp = AdEvent.objects.filter(placement=p, event_type="impression").count()
        clk = AdEvent.objects.filter(placement=p, event_type="click").count()
        ctr_local = (clk / imp * 100) if imp else 0
        placement_stats[p.id] = {"impressions": imp, "clicks": clk, "ctr": round(ctr_local, 2)}
    for c in AdCreative.objects.all()[:50]:
        imp = AdEvent.objects.filter(creative=c, event_type="impression").count()
        clk = AdEvent.objects.filter(creative=c, event_type="click").count()
        ctr_local = (clk / imp * 100) if imp else 0
        creative_stats[c.id] = {"impressions": imp, "clicks": clk, "ctr": round(ctr_local, 2)}
    assignments = (
        PlacementAssignment.objects.filter(placement__in=placements, is_enabled=True)
        .select_related("placement", "creative", "creative__campaign")
    )
    placement_campaigns = defaultdict(list)
    for a in assignments:
        placement_campaigns[a.placement_id].append(
            {
                "creative": a.creative.name,
                "campaign": getattr(a.creative.campaign, "name", ""),
                "locked": a.locked,
                "weight": a.weight,
                "active": a.creative.is_enabled and a.creative.campaign.is_live() if a.creative.campaign else a.creative.is_enabled,
            }
        )
    return render(
        request,
        "ads/dashboard.html",
        {
            "placements": placements,
            "campaigns": campaigns,
            "ads_enabled": _ads_enabled(),
            "ad_networks_enabled": getattr(ss, "ad_networks_enabled", False),
            "affiliate_enabled": getattr(ss, "affiliate_enabled", False),
            "impressions": impressions,
            "clicks": clicks,
            "ctr": round(ctr, 2),
            "ad_aggressiveness_level": getattr(ss, "ad_aggressiveness_level", "balanced"),
            "placement_stats": placement_stats,
            "placement_campaigns": placement_campaigns,
            "affiliate_sources": affiliate_sources,
            "creative_stats": creative_stats,
            "creatives": creatives,
        },
    )


@csrf_protect
@user_passes_test(lambda u: u.is_staff or u.is_superuser or getattr(u, "has_role", lambda *r: False)("admin", "editor"))
@require_POST
def toggle_settings(request: HttpRequest) -> HttpResponse:
    ss = SiteSettings.get_solo()
    action = request.POST.get("action", "")
    placement_id = request.POST.get("placement")
    campaign_id = request.POST.get("campaign")

    if action in ("disable_placement", "enable_placement") and placement_id:
        placement = AdPlacement.objects.filter(pk=placement_id).first()
        if placement:
            placement.is_enabled = action == "enable_placement"
            placement.save(update_fields=["is_enabled"])
    elif action == "toggle_lock" and placement_id:
        placement = AdPlacement.objects.filter(pk=placement_id).first()
        if placement:
            placement.locked = not placement.locked
            placement.save(update_fields=["locked"])
    elif action in ("disable_campaign", "enable_campaign") and campaign_id:
        campaign = Campaign.objects.filter(pk=campaign_id).first()
        if campaign:
            campaign.is_active = action == "enable_campaign"
            campaign.save(update_fields=["is_active"])
    elif action == "toggle_campaign_lock" and campaign_id:
        campaign = Campaign.objects.filter(pk=campaign_id).first()
        if campaign:
            campaign.locked = not campaign.locked
            campaign.save(update_fields=["locked"])
    else:
        ss.ads_enabled = request.POST.get("ads_enabled") == "1"
        ss.ad_networks_enabled = request.POST.get("ad_networks_enabled") == "1"
        ss.affiliate_enabled = request.POST.get("affiliate_enabled") == "1"
        level = request.POST.get("ad_aggressiveness_level") or ss.ad_aggressiveness_level
        if level in ("minimal", "balanced", "aggressive"):
            ss.ad_aggressiveness_level = level
        ss.save()
    _log(
        request,
        "ads.dashboard.toggle",
        action=action,
        placement=str(placement_id or ""),
        campaign=str(campaign_id or ""),
    )
    return redirect("ads:dashboard")


