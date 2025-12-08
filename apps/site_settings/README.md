# Site Settings App

Singleton site configuration for branding, legal text, feature toggles, and integration with templates/context processors.

## Capabilities
- Stores site name, logos, colors, legal text, feature toggles (ads, seo, affiliate, etc.).
- Context processor exposes settings to all templates.
- Admin interface for editing branding and toggles.
- Feeds footer/header components with dynamic values.

## Key Files
- `models.py` — SiteSettings singleton.
- `views.py`/`urls.py` — Manage/legal pages.
- `admin.py` — Admin form for settings.
- `migrations/` — Includes sitemap/legal fields.
