
from __future__ import annotations

import json

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from apps.consent.models import ConsentPolicy, ConsentDecision, ConsentEvent
from apps.consent.utils import hash_ip, hash_ua, set_consent_cookie
from apps.core.utils.ip import get_client_ip


def privacy_center(request):
    active_policy = ConsentPolicy.objects.filter(is_active=True).order_by("-effective_from").first()
    decisions = ConsentDecision.objects.none()
    if active_policy:
        if request.user.is_authenticated:
            decisions = ConsentDecision.objects.filter(user=request.user, policy=active_policy)
        else:
            sid = request.session.session_key
            if sid:
                decisions = ConsentDecision.objects.filter(session_id=sid, policy=active_policy)
    return render(
        request,
        "consent/privacy_center.html",
        {"policy": active_policy, "decisions": decisions[:20]},
    )


@login_required
def privacy_center_authed(request):
    return privacy_center(request)


@require_POST
def accept_all(request: HttpRequest) -> HttpResponse:
    policy = ConsentPolicy.objects.filter(is_active=True).order_by("-effective_from").first()
    if not policy:
        return JsonResponse({"ok": False, "message": "No active policy"}, status=400)
    if not request.session.session_key:
        request.session.create()
    snapshot = policy.categories_snapshot or {}
    if not snapshot:
        snapshot = {"functional": True}
    categories = {k: True for k in snapshot.keys()}
    decision = ConsentDecision.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_id=request.session.session_key or "",
        policy=policy,
        categories=categories,
    )
    decision.set_hashes(get_client_ip(request) or "", request.META.get("HTTP_USER_AGENT", ""))
    decision.save(update_fields=["ip_hash", "user_agent_hash"])
    ConsentEvent.objects.create(
        decision=decision,
        policy=policy,
        categories=categories,
        event_type="accepted_all",
        ip_hash=decision.ip_hash,
        user_agent_hash=decision.user_agent_hash,
    )
    resp = JsonResponse({"ok": True, "message": "Preferences saved"})
    set_consent_cookie(resp, categories)
    return resp


@require_POST
def reject_all(request: HttpRequest) -> HttpResponse:
    policy = ConsentPolicy.objects.filter(is_active=True).order_by("-effective_from").first()
    if not policy:
        return JsonResponse({"ok": False, "message": "No active policy"}, status=400)
    if not request.session.session_key:
        request.session.create()
    snapshot = policy.categories_snapshot or {}
    if not snapshot:
        snapshot = {"functional": True}
    # Only required categories remain true; optional are false/omitted
    categories = {}
    for slug, meta in snapshot.items():
        required = False
        if isinstance(meta, dict):
            required = bool(meta.get("required", False))
        categories[slug] = True if required else False
    decision = ConsentDecision.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_id=request.session.session_key or "",
        policy=policy,
        categories=categories,
    )
    decision.set_hashes(get_client_ip(request) or "", request.META.get("HTTP_USER_AGENT", ""))
    decision.save(update_fields=["ip_hash", "user_agent_hash"])
    ConsentEvent.objects.create(
        decision=decision,
        policy=policy,
        categories=categories,
        event_type="rejected_all",
        ip_hash=decision.ip_hash,
        user_agent_hash=decision.user_agent_hash,
    )
    resp = JsonResponse({"ok": True, "message": "Preferences saved"})
    set_consent_cookie(resp, categories)
    return resp


@require_POST
def accept(request: HttpRequest) -> HttpResponse:
    policy = ConsentPolicy.objects.filter(is_active=True).order_by("-effective_from").first()
    if not policy:
        return JsonResponse({"ok": False, "message": "No active policy"}, status=400)
    if not request.session.session_key:
        request.session.create()
    try:
        payload = json.loads(request.body.decode() or "{}")
        if not isinstance(payload, dict):
            raise ValueError
    except Exception:
        payload = {}
    snapshot = policy.categories_snapshot or {}
    if not snapshot:
        snapshot = {"functional": True}
    categories = {}
    for slug, val in snapshot.items():
        required = False
        if isinstance(val, dict):
            required = bool(val.get("required", False))
        incoming = payload.get(slug)
        categories[slug] = True if required else bool(incoming)
    decision = ConsentDecision.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_id=request.session.session_key or "",
        policy=policy,
        categories=categories,
    )
    decision.set_hashes(get_client_ip(request) or "", request.META.get("HTTP_USER_AGENT", ""))
    decision.save(update_fields=["ip_hash", "user_agent_hash"])
    ConsentEvent.objects.create(
        decision=decision,
        policy=policy,
        categories=categories,
        event_type="granular_accept",
        ip_hash=decision.ip_hash,
        user_agent_hash=decision.user_agent_hash,
    )
    resp = JsonResponse({"ok": True, "message": "Preferences saved"})
    set_consent_cookie(resp, categories)
    return resp


def banner(request: HttpRequest) -> HttpResponse:
    """
    Render the consent banner fragment for the frontend loader.
    Returns empty content if no active policy exists.
    """
    policy = ConsentPolicy.objects.filter(is_active=True).order_by("-effective_from").first()
    if not policy:
        # Ensure we always have a minimal active policy so the banner can render
        policy, _ = ConsentPolicy.objects.get_or_create(
            version="default",
            defaults={
                "is_active": True,
                "banner_text": "We use cookies to improve your browsing experience.",
                "manage_text": "Manage your cookie preferences.",
                "categories_snapshot": {
                    "functional": {"required": True, "label": "Functional"},
                    "analytics": {"required": False, "label": "Analytics"},
                    "ads": {"required": False, "label": "Advertising"},
                },
            },
        )
        if not policy.is_active:
            policy.is_active = True
            policy.save(update_fields=["is_active"])
    ctx = {
        "policy": policy,
        "categories": policy.categories_snapshot or {},
        "consent_text": policy.banner_text or "We use cookies to improve your browsing experience.",
    }
    return render(request, "consent/includes/banner.html", ctx)


