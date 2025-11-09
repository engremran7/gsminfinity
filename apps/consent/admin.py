"""
apps.consent.admin
------------------
Enterprise-grade admin interface for GDPR/CCPA consent management.
"""

import csv
import json
from django.contrib import admin
from django.http import HttpResponse
from django.db import transaction
from django.utils.encoding import smart_str
from .models import ConsentPolicy, ConsentRecord, ConsentLog


# ============================================================
#  FILTERS
# ============================================================
class RejectAllFilter(admin.SimpleListFilter):
    """Quickly locate users who rejected all optional cookies."""
    title = "Reject All"
    parameter_name = "reject_all"

    def lookups(self, request, model_admin):
        return [("yes", "Rejected All"), ("no", "Not Rejected All")]

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.filter(accepted_categories__reject_all=True)
        elif val == "no":
            return queryset.exclude(accepted_categories__reject_all=True)
        return queryset


class PolicyVersionFilter(admin.SimpleListFilter):
    """Filter by policy version safely, even if field is CharField or FK."""
    title = "Policy Version"
    parameter_name = "policy_version"

    def lookups(self, request, model_admin):
        versions = (
            ConsentPolicy.objects.order_by("-created_at")
            .values_list("version", flat=True)
            .distinct()
        )
        return [(v, v) for v in versions]

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            return queryset.filter(policy_version=val)
        return queryset


# ============================================================
#  CONSENT POLICY ADMIN
# ============================================================
@admin.register(ConsentPolicy)
class ConsentPolicyAdmin(admin.ModelAdmin):
    """Manage Consent Policies across sites."""
    list_display = ("version", "site_domain", "is_active", "created_at", "updated_at")
    list_filter = ("site_domain", "is_active", "created_at")
    search_fields = ("version", "site_domain")
    ordering = ("-created_at",)
    actions = ["activate_policy"]

    @admin.action(description="Activate selected policy (deactivate others for same site)")
    def activate_policy(self, request, queryset):
        """Atomically activate selected policies per site_domain."""
        with transaction.atomic():
            for policy in queryset:
                ConsentPolicy.objects.select_for_update().filter(
                    site_domain=policy.site_domain
                ).exclude(pk=policy.pk).update(is_active=False)
                policy.is_active = True
                policy.save(update_fields=["is_active"])
        self.message_user(
            request,
            "✅ Selected policies activated; others for the same site were deactivated."
        )


# ============================================================
#  CONSENT RECORD ADMIN
# ============================================================
@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    """Manage individual consent records and export compliance data."""
    list_display = (
        "user_display",
        "session_key",
        "policy_display",
        "site_domain",
        "is_reject_all",
        "audit_summary_display",
        "accepted_at",
        "updated_at",
    )
    list_filter = (
        PolicyVersionFilter,  # ✅ replaced invalid direct field filter
        "site_domain",
        RejectAllFilter,
        "updated_at",
    )
    search_fields = (
        "user__email",
        "user__username",
        "session_key",
        "policy_version",
        "site_domain",
    )
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)
    actions = ["export_to_csv"]

    @admin.display(description="User")
    def user_display(self, obj):
        """Friendly user display for admin lists."""
        if obj.user:
            return getattr(obj.user, "email", None) or getattr(obj.user, "username", None) or f"User#{obj.user_id}"
        return "Anonymous"

    @admin.display(description="Policy Version")
    def policy_display(self, obj):
        """Display linked policy version or fallback string."""
        if obj.policy:
            return obj.policy.version
        return obj.policy_version or "—"

    @admin.display(boolean=True, description="Rejected All?")
    def is_reject_all(self, obj):
        try:
            return bool(obj.accepted_categories.get("reject_all"))
        except Exception:
            return False

    @admin.display(description="Accepted Categories Summary")
    def audit_summary_display(self, obj):
        try:
            return obj.audit_summary()
        except Exception:
            return "—"

    @admin.action(description="Export selected consent records to CSV (UTF-8 + Excel-safe)")
    def export_to_csv(self, request, queryset):
        """Export selected consent records as UTF-8 CSV with JSON-safe category data."""
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = "attachment; filename=consent_records.csv"
        response.write("\ufeff")  # UTF-8 BOM for Excel

        writer = csv.writer(response)
        writer.writerow([
            "User",
            "Session Key",
            "Policy Version",
            "Site Domain",
            "Accepted Categories (JSON)",
            "Rejected All",
            "Accepted At",
            "Updated At",
        ])

        for record in queryset.select_related("user", "policy"):
            user_display = getattr(record.user, "email", "") or getattr(record.user, "username", "") or "Anonymous"
            writer.writerow([
                smart_str(user_display),
                smart_str(record.session_key or ""),
                smart_str(record.policy_version or getattr(record.policy, "version", "")),
                smart_str(record.site_domain),
                json.dumps(record.accepted_categories or {}, ensure_ascii=False),
                record.is_reject_all(),
                record.accepted_at.isoformat() if record.accepted_at else "",
                record.updated_at.isoformat() if record.updated_at else "",
            ])
        return response


# ============================================================
#  CONSENT LOG ADMIN
# ============================================================
@admin.register(ConsentLog)
class ConsentLogAdmin(admin.ModelAdmin):
    """Audit trail for consent change events."""
    list_display = ("user_display", "ip_address", "policy_version_display", "site_domain", "timestamp")
    list_filter = ("site_domain", "timestamp")
    search_fields = ("user__email", "ip_address", "policy_version")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)

    @admin.display(description="User")
    def user_display(self, obj):
        return getattr(obj.user, "email", None) or getattr(obj.user, "username", None) or "Anonymous"

    @admin.display(description="Policy Version")
    def policy_version_display(self, obj):
        """Display for admin list when policy_version isn't a true model field reference."""
        return getattr(obj, "policy_version", "—") or "—"
