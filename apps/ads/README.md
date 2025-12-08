# Ads App

Ad placements, campaigns, creatives, affiliate sources/links, rotation/targeting engines, and consent-aware serving.

## Capabilities
- Placements and creatives with status/is_active flags.
- Campaign and event tracking; affiliate link/source tracking.
- Rotation/targeting engines (`services/rotation`, `services/targeting`).
- Consent-aware rendering via template tags and JS helpers.
- Admin and admin-suite views for placements/creatives/redirects.

## Key Files
- `models.py` — Placement, Creative, Campaign, Event, Affiliate.
- `services/` — rotation, targeting, tasks.
- `templatetags/ads_tags.py` — `render_ad_slot` for templates.
- `views.py` — Redirects/tracking.
- `signals.py` — Hooks for analytics.

## Templates/Static
- Ad slot partials in site templates; JS helpers in `static/js/ads.js` (local).
