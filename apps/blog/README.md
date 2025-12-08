# Blog App

Posts, drafts, scheduling, AI hooks, feeds, tags/SEO integration, and CSP-safe sharing (copy-link only).

## Capabilities
- Post lifecycle: draft/scheduled/published, revisions, summaries, AI editor hooks.
- Translations: Post/Category/Tag translation tables; translation command uses offline provider (Argos/dummy).
- Feeds: RSS/JSON feeds, sitemaps, trending/related widgets.
- Tags: Integrated with `apps.tags` (cloud, trending badges).
- Comments: Consent-aware comment block with moderation flags.
- SEO: Metadata rendering, canonical URLs, JSON-LD.
- Sharing: Local copy-link buttons; external share URLs removed.

## Key Files
- `models.py` — Post, Category, PostTranslation, etc.
- `views.py` — List/detail, manage, search; translation application at render.
- `signals.py` — Sitemap ping, automation hooks.
- `services/` — AI editor/workflow helpers.
- `templates/blog/*.html` — list/detail/manage widgets; `post_detail` has copy-link sharing.

## Commands
- `translate_content --langs ar,ur` — fills translations for posts/categories/tags (after content exists).

## Notes
- Recaptcha script is commented out in templates for CSP/offline; enable only via a proxied/local solution if needed.
