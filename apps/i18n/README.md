# i18n App

Locales, translation provider, and translation command for posts/categories/tags.

## Capabilities
- Locale model with code/name/direction.
- Translation provider abstraction (Argos offline/dummy).
- Services to resolve locales and apply translations at render time.
- Management command `translate_content` to batch-translate blog content.

## Key Files
- `models.py` — Locale and translation manifests.
- `services.py` — Locale resolution, translation helpers.
- `translation_provider.py` — Provider selection (offline-first).
- `management/commands/translate_content.py` — Batch translation runner.
- `migrations/0003_seed_locales.py` — Seeds en/ar/ur.

## Usage
- Run `python manage.py translate_content --langs ar,ur` after posts/categories/tags exist.
