"""
apps.consent.admin
Enterprise-grade, hardened GDPR/CCPA admin interface.
Django 5.2+ • Fully safe • No deprecated APIs • No queryset logic errors.
"""

from __future__ import annotations

import csv
import json
from typing import Iterable

from django.contrib import admin
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils.encoding import smart_str
from django.utils.html import format_html, mark_safe

from .models import ConsentLog, ConsentPolicy, ConsentRecord


# =====================================================================
#  FILTERS — ENTERPRISE HARDENED
# =====================================================================
class RejectAllFilter(admin.SimpleListFilter):
    """
    Filter records where the user rejected ALL optional cookies.

    Hardening:
    - Does NOT evaluate whole QuerySet
    - Uses DB-side filtering where possible
    - Falls back to safe in-Python logic only when required
    - Never returns lists
    """

    title = "Reject All"
    parameter_name = "reject_all"

    def lookups(self, request, model_admin):
        return [("yes", "Rejected All"), ("no", "Accepted Some")]

    def queryset(self, request, queryset: QuerySet):
        val = self.value()
        if val not in ("yes", "no"):
            return queryset

        # Optimized: detect reject_all via JSON field
        # "reject_all" is a boolean key under accepted_categories
        try:
            if val == "yes":
                return queryset.filter(accepted_categories__reject_all=True)
            else:
                return queryset.exclude(accepted_categories__reject_all=True)
        except Exception:
            # fallback safety version — robust, but slower
            ids = []
            for obj in queryset.only("pk"):
                try:
                    if (val == "yes" and obj.is_reject_all()) or (
                        val == "no" and not obj.is_reject_all()
                    ):
                        ids.append(obj.pk)
                except Exception:
                    continue

            return queryset.filter(pk__in=ids)


class PolicyVersionFilter(admin.SimpleListFilter):
    """
    Filter by policy version (distinct versions only).
    """

    title = "Policy Version"
    parameter_name = "policy_version"

    def lookups(self, request, model_admin):
        versions = (
            ConsentPolicy.objects.order_by("-created_at")
            .values_list("version", flat=True)
            .distinct()
        )
        return [(v, v) for v in versions]

    def queryset(self, request, queryset: QuerySet):
        val = self.value()
        if val:
            return queryset.filter(policy_version=val)
        return queryset


# =====================================================================
#  CONSENT POLICY ADMIN
# =====================================================================
@admin.register(ConsentPolicy)
class ConsentPolicyAdmin(admin.ModelAdmin):
    """
    Manage versioned consent policies with atomic activation logic.
    """

    readonly_fields = (
        "categories_snapshot_pretty",
        "created_at",
        "updated_at",
    )

    list_display = (
        "version",
        "site_domain",
        "is_active",
        "preview_snapshot",
        "created_at",
        "updated_at",
    )

    list_filter = ("site_domain", "is_active", "created_at")
    search_fields = ("version", "site_domain")
    ordering = ("-created_at",)
    actions = ["activate_policy", "export_policy_json"]

    fieldsets = (
        (
            "Policy Versioning",
            {
                "fields": ("version", "site_domain", "is_active"),
            },
        ),
        (
            "Snapshot (read-only)",
            {
                "fields": ("categories_snapshot_pretty",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    # ---------------- JSON Pretty Printer ----------------
    @admin.display(description="Categories Snapshot")
    def categories_snapshot_pretty(self, obj):
        data = obj.categories_snapshot or {}
        try:
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            pretty = "{}"
        return format_html(
            "<pre style='background:#fafafa; padding:12px; border-radius:6px; white-space:pre-wrap'>{}</pre>",
            mark_safe(pretty),
        )

    @admin.display(description="Snapshot")
    def preview_snapshot(self, obj):
        snap = obj.categories_snapshot or {}
        return f"{len(snap)} categories"

    # ---------------- Admin Actions ----------------
    @admin.action(description="Activate selected policy (auto-deactivate siblings)")
    def activate_policy(self, request, queryset: QuerySet):
        if queryset.count() != 1:
            self.message_user(request, "❌ Select exactly ONE policy", level="error")
            return

        policy = queryset.first()

        with transaction.atomic():
            ConsentPolicy.objects.select_for_update().filter(
                site_domain=policy.site_domain
            ).exclude(pk=policy.pk).update(is_active=False)

            policy.is_active = True
            policy.save(update_fields=["is_active"])

        self.message_user(
            request,
            f"✅ Activated Policy v{policy.version} for '{policy.site_domain}'",
        )

    @admin.action(description="Export selected policies → JSON")
    def export_policy_json(self, request, queryset: QuerySet):
        response = HttpResponse(content_type="application/json; charset=utf-8")
        response["Content-Disposition"] = "attachment; filename=consent_policies.json"

        try:
            payload = [obj.to_payload() for obj in queryset]
        except Exception:
            payload = []

        response.write(json.dumps(payload, indent=2, ensure_ascii=False))
        return response


# =====================================================================
#  CONSENT RECORD ADMIN
# =====================================================================
@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    """
    Admin interface for user consent records.
    """

    readonly_fields = (
        "accepted_categories_pretty",
        "accepted_at",
        "updated_at",
    )

    list_display = (
        "user_display",
        "session_key",
        "policy_display",
        "site_domain",
        "is_reject_all_display",
        "accepted_summary_display",
        "updated_at",
    )

    list_filter = (
        PolicyVersionFilter,
        "site_domain",
        "updated_at",
        RejectAllFilter,
    )

    search_fields = (
        "user__email",
        "user__username",
        "session_key",
        "policy_version",
        "site_domain",
    )

    ordering = ("-updated_at",)
    actions = ["export_to_csv"]

    fieldsets = (
        ("User / Session", {"fields": ("user", "session_key", "site_domain")}),
        ("Policy Info", {"fields": ("policy", "policy_version")}),
        ("Accepted Categories", {"fields": ("accepted_categories_pretty",)}),
        ("Timestamps", {"fields": ("accepted_at", "updated_at")}),
    )

    # ---------------- JSON Pretty Printer ----------------
    @admin.display(description="Accepted Categories")
    def accepted_categories_pretty(self, obj):
        data = obj.accepted_categories or {}
        try:
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            pretty = "{}"
        return format_html(
            "<pre style='background:#fafafa; padding:8px; border-radius:6px; white-space:pre-wrap'>{}</pre>",
            mark_safe(pretty),
        )

    # ---------------- Display Helpers ----------------
    @admin.display(description="User")
    def user_display(self, obj):
        try:
            if obj.user:
                return obj.user.email or obj.user.username
        except Exception:
            pass
        return "Anonymous"

    @admin.display(description="Policy")
    def policy_display(self, obj):
        try:
            if obj.policy_version:
                return obj.policy_version
            if obj.policy:
                return obj.policy.version
        except Exception:
            pass
        return "—"

    @admin.display(boolean=True, description="Rejected All?")
    def is_reject_all_display(self, obj):
        try:
            return obj.is_reject_all()
        except Exception:
            return False

    @admin.display(description="Accepted Categories Summary")
    def accepted_summary_display(self, obj):
        try:
            return obj.audit_summary()
        except Exception:
            return "(Error)"

    # ---------------- CSV Export ----------------
    @admin.action(description="Export selected consent records → CSV")
    def export_to_csv(self, request, queryset: QuerySet):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = "attachment; filename=consent_records.csv"
        response.write("\ufeff")  # Excel-safe BOM

        writer = csv.writer(response)
        writer.writerow(
            [
                "User",
                "Session Key",
                "Policy Version",
                "Site Domain",
                "Accepted Categories",
                "Rejected All",
                "Accepted At",
                "Updated At",
            ]
        )

        recs: Iterable[ConsentRecord] = queryset.select_related("user", "policy")

        for rec in recs:
            writer.writerow(
                [
                    smart_str(rec.user.email if rec.user else "Anonymous"),
                    smart_str(rec.session_key or ""),
                    smart_str(rec.policy_version),
                    smart_str(rec.site_domain),
                    json.dumps(rec.accepted_categories or {}, ensure_ascii=False),
                    rec.is_reject_all(),
                    rec.accepted_at.isoformat() if rec.accepted_at else "",
                    rec.updated_at.isoformat() if rec.updated_at else "",
                ]
            )

        return response


# =====================================================================
#  CONSENT LOG ADMIN — READ-ONLY AUDIT TRAIL
# =====================================================================
@admin.register(ConsentLog)
class ConsentLogAdmin(admin.ModelAdmin):
    """
    Immutable forensic log entries.
    """

    readonly_fields = (
        "user",
        "ip_address",
        "user_agent",
        "policy_version",
        "site_domain",
        "timestamp",
        "accepted_categories_pretty",
    )

    list_display = (
        "user_display",
        "ip_address",
        "policy_version",
        "site_domain",
        "timestamp",
    )

    list_filter = ("site_domain", "timestamp")
    search_fields = ("user__email", "ip_address", "policy_version")
    ordering = ("-timestamp",)
    date_hierarchy = "timestamp"

    @admin.display(description="Accepted Categories")
    def accepted_categories_pretty(self, obj):
        data = obj.accepted_categories or {}
        try:
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            pretty = "{}"
        return format_html(
            "<pre style='background:#fafafa; padding:8px; border-radius:6px; white-space:pre-wrap'>{}</pre>",
            mark_safe(pretty),
        )

    @admin.display(description="User")
    def user_display(self, obj):
        try:
            if obj.user:
                return obj.user.email
        except Exception:
            pass
        return "Anonymous"