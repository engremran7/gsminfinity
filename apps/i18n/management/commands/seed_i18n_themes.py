
from __future__ import annotations

from typing import List, Optional

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.i18n.models import (
    AppManifest,
    FontRegistry,
    LanguageProfile,
    Locale,
    Theme,
    ThemeAssignment,
)


class Command(BaseCommand):
    help = "Seed i18n with default locales, fonts, language profiles, and manifests for common apps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--locales",
            type=str,
            help="Comma-separated locale codes to seed. Defaults to settings.LANGUAGES or en,ur,ar.",
        )
        parser.add_argument(
            "--apps",
            type=str,
            help="Comma-separated app_ids to register manifests for. Defaults to core,users,blog,comments,tags.",
        )
        parser.add_argument(
            "--site-id",
            type=str,
            default=None,
            help="Optional site_id to associate with manifests/profiles.",
        )

    def handle(self, *args, **options):
        locale_codes = self._get_locales(options.get("locales"))
        app_ids = self._get_apps(options.get("apps"))
        site_id = options.get("site_id")

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding locales..."))
        for code in locale_codes:
            defaults = {
                "name": settings.LANGUAGES_DICT.get(code, code) if hasattr(settings, "LANGUAGES_DICT") else code,
                "direction": "rtl" if code.startswith(("ar", "ur", "fa", "ps")) else "ltr",
            }
            obj, created = Locale.objects.get_or_create(code=code, defaults=defaults)
            self._log(obj, created)

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding default Nastaleeq font registry..."))
        font_defaults = {
            "family": "Jameel Noori Nastaleeq",
            "urls": ["/static/fonts/jameel-noori-nastaleeq.woff2"],
            "weight_map": {"400": "normal", "700": "bold"},
            "font_display": "swap",
            "is_default_for_locales": [c for c in locale_codes if c.startswith(("ar", "ur", "fa"))],
        }
        font, created = FontRegistry.objects.get_or_create(code="jameel-noori-nastaleeq", defaults=font_defaults)
        self._log(font, created)

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding language profiles..."))
        for app_id in app_ids:
            profile_defaults = {
                "default_locale": locale_codes[0] if locale_codes else "en",
                "supported_locales": locale_codes,
                "fallback_locale": "en",
            }
            profile, created = LanguageProfile.objects.get_or_create(
                app_id=app_id,
                site_id=site_id,
                defaults=profile_defaults,
            )
            self._log(profile, created)

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding app manifests..."))
        for app_id in app_ids:
            manifest_defaults = {
                "site_id": site_id,
                "namespaces": ["common"],
                "supported_locales": locale_codes,
                "default_locale": locale_codes[0] if locale_codes else "en",
                "routes": ["/"],
                "token_usage": [],
            }
            manifest, created = AppManifest.objects.update_or_create(
                app_id=app_id,
                defaults=manifest_defaults,
            )
            self._log(manifest, created)

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding curated themes..."))
        self._seed_themes(app_ids, site_id)

        self.stdout.write(self.style.SUCCESS("i18n seeding complete."))

    def _get_locales(self, arg: Optional[str]) -> List[str]:
        if arg:
            return [c.strip() for c in arg.split(",") if c.strip()]
        if hasattr(settings, "LANGUAGES") and settings.LANGUAGES:
            return [code for code, _ in settings.LANGUAGES]
        return ["en", "ur", "ar"]

    def _get_apps(self, arg: Optional[str]) -> List[str]:
        if arg:
            return [a.strip() for a in arg.split(",") if a.strip()]
        return ["core", "users", "blog", "comments", "tags"]

    def _log(self, obj, created: bool):
        msg = f"{'Created' if created else 'Exists'}: {obj}"
        self.stdout.write(f"  - {msg}")

    def _seed_themes(self, app_ids: List[str], site_id: Optional[str]):
        """
        Create a curated set of enterprise-friendly themes and assign global defaults.
        """
        curated = [
            {
                "name": "Aurora",
                "mode": "light",
                "tokens": {
                    "color": {
                        "surface": "#f8fafc",
                        "text": "#0f172a",
                        "muted": "#475569",
                        "border": "#e2e8f0",
                        "primary": "#2563eb",
                        "accent": "#22c55e",
                    },
                    "radii": {"md": "14px"},
                    "shadows": {"elevation": "0 18px 40px rgba(37,99,235,0.15)"},
                    "typography": {"fonts": {"base": "Inter, 'Segoe UI', system-ui, sans-serif"}},
                },
            },
            {
                "name": "Noir",
                "mode": "dark",
                "tokens": {
                    "color": {
                        "surface": "#0b1220",
                        "text": "#e2e8f0",
                        "muted": "#94a3b8",
                        "border": "#1f2937",
                        "primary": "#38bdf8",
                        "accent": "#f472b6",
                    },
                    "radii": {"md": "12px"},
                    "shadows": {"elevation": "0 22px 46px rgba(0,0,0,0.65)"},
                    "typography": {"fonts": {"base": "Inter, 'Segoe UI', system-ui, sans-serif"}},
                },
            },
            {
                "name": "Emerald",
                "mode": "light",
                "tokens": {
                    "color": {
                        "surface": "#f0fdf4",
                        "text": "#064e3b",
                        "muted": "#065f46",
                        "border": "#bbf7d0",
                        "primary": "#10b981",
                        "accent": "#0ea5e9",
                    },
                    "radii": {"md": "16px"},
                    "shadows": {"elevation": "0 16px 36px rgba(16,185,129,0.18)"},
                    "typography": {"fonts": {"base": "Manrope, Inter, system-ui, sans-serif"}},
                },
            },
            {
                "name": "Midnight Neon",
                "mode": "dark",
                "tokens": {
                    "color": {
                        "surface": "#0b0f1a",
                        "text": "#e5e7eb",
                        "muted": "#a5b4fc",
                        "border": "#1f2937",
                        "primary": "#8b5cf6",
                        "accent": "#22d3ee",
                    },
                    "radii": {"md": "14px"},
                    "shadows": {"elevation": "0 20px 44px rgba(139,92,246,0.35)"},
                    "typography": {"fonts": {"base": "Space Grotesk, Inter, system-ui, sans-serif"}},
                },
            },
            {
                "name": "Sunset",
                "mode": "light",
                "tokens": {
                    "color": {
                        "surface": "#fff7ed",
                        "text": "#7c2d12",
                        "muted": "#9a3412",
                        "border": "#fed7aa",
                        "primary": "#f97316",
                        "accent": "#0ea5e9",
                    },
                    "radii": {"md": "18px"},
                    "shadows": {"elevation": "0 14px 32px rgba(249,115,22,0.25)"},
                    "typography": {"fonts": {"base": "Sora, Inter, system-ui, sans-serif"}},
                },
            },
            {
                "name": "Sapphire",
                "mode": "dark",
                "tokens": {
                    "color": {
                        "surface": "#0b1224",
                        "text": "#e0f2fe",
                        "muted": "#bfdbfe",
                        "border": "#1e3a8a",
                        "primary": "#3b82f6",
                        "accent": "#22c55e",
                    },
                    "radii": {"md": "12px"},
                    "shadows": {"elevation": "0 20px 40px rgba(59,130,246,0.3)"},
                    "typography": {"fonts": {"base": "Inter, 'Segoe UI', system-ui, sans-serif"}},
                },
            },
            {
                "name": "Sandstone",
                "mode": "light",
                "tokens": {
                    "color": {
                        "surface": "#fffbeb",
                        "text": "#3f2f1a",
                        "muted": "#6b4d2f",
                        "border": "#f5e7c6",
                        "primary": "#d97706",
                        "accent": "#2563eb",
                    },
                    "radii": {"md": "14px"},
                    "shadows": {"elevation": "0 12px 28px rgba(217,119,6,0.22)"},
                    "typography": {"fonts": {"base": "IBM Plex Sans, Inter, system-ui, sans-serif"}},
                },
            },
            {
                "name": "Forest",
                "mode": "dark",
                "tokens": {
                    "color": {
                        "surface": "#0b1611",
                        "text": "#e2f4ea",
                        "muted": "#9ae6b4",
                        "border": "#0f241a",
                        "primary": "#22c55e",
                        "accent": "#0ea5e9",
                    },
                    "radii": {"md": "12px"},
                    "shadows": {"elevation": "0 20px 44px rgba(34,197,94,0.28)"},
                    "typography": {"fonts": {"base": "Inter, 'Segoe UI', system-ui, sans-serif"}},
                },
            },
            {
                "name": "High Contrast Pro",
                "mode": "high_contrast",
                "tokens": {
                    "color": {
                        "surface": "#000000",
                        "text": "#ffffff",
                        "muted": "#d1d5db",
                        "border": "#ffffff",
                        "primary": "#ffbf00",
                        "accent": "#00ffcc",
                    },
                    "radii": {"md": "0px"},
                    "shadows": {"elevation": "none"},
                    "typography": {"fonts": {"base": "Inter, 'Segoe UI', system-ui, sans-serif"}},
                },
            },
        ]

        for app_id in app_ids:
            for theme_def in curated:
                theme, created = Theme.objects.update_or_create(
                    app_id=app_id,
                    site_id=site_id,
                    name=theme_def["name"],
                    mode=theme_def["mode"],
                    defaults={
                        "tokens": theme_def["tokens"],
                        "is_locked": True,
                    },
                )
                self._log(theme, created)
                # Ensure global assignment exists so the theme is available
                ThemeAssignment.objects.get_or_create(
                    theme=theme,
                    app_id=app_id,
                    site_id=site_id,
                    scope="global",
                    defaults={},
                )


