# Tags App

Tagging with hierarchy, suggestions/providers, and SEO-friendly exposure.

## Capabilities
- Tag model with optional parent for hierarchy.
- Suggestions/providers for keyword extraction.
- Management commands for keyword ingestion and duplicate cleanup.
- Tag cloud and trending badges rendered in blog templates.

## Key Files
- `models.py` — Tag, relationships.
- `services.py` — Suggestions, keyword utilities.
- `views.py`/`urls.py` — Tag list/detail APIs.
- `sitemaps.py` — Tag sitemaps.

## Templates
- `templates/components/tag_badges.html`, `tag_cloud.html` — shared UI.
