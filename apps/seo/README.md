# SEO App

Metadata, sitemaps, internal linking, URL inspector, and AI-assisted meta/schema helpers.

## Capabilities
- SEO models for meta tags, schema, redirects.
- Sitemaps (XML) and URL inspector tools.
- Internal linking and auto-meta helpers.
- AI hooks to generate metadata/schema (leverages `apps.ai` services).

## Key Files
- `models_settings.py` — SEO settings singleton.
- `auto.py` — Automation helpers.
- `views.py` — Inspector and dashboard endpoints.
- `sitemaps.py` — Sitemap generation.
- `management/commands/*` — check_links, inspect_url.

## Templates
- `templates/seo/*` — Admin suite views and inspector components.

## Integration
- Used by blog/tags/pages to render canonical/meta blocks.
