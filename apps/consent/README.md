# Consent App

Centralized consent policies, decisions/events, hashing helpers, and CSP-safe banner/manage flows.

## Capabilities
- ConsentDecision / ConsentEvent models; policy management.
- Hashing helpers for IP/UA; cookie options centralized.
- Banner + manage pages; legal templates (privacy/terms/cookies).
- Integrates with ads/device identity/comments to respect consent categories.

## Key Files
- `models.py` — policies, decisions, events.
- `views.py` — banner, accept/reject, manage.
- `utils.py` — hashing, cookie helpers.
- `templates/consent/includes/banner.html` — uses `data-consent-action` (no HTMX).
- `static/js/consent-banner-loader.js` — local loader, CSP-safe.

## Notes
- No external scripts/CDNs; banner actions are local AJAX/fetch.
