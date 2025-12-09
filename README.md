# GSMInfinity

Full-stack Django platform for content, ads, SEO, consent, users, devices, distribution, and an optional pluggable security suite. This README is a human-friendly map so you can onboard fast and know where the sharp edges are.

## What’s inside
- Users / MFA / Email verification – Custom user model, TOTP, verification codes with TTL + resend + cooldown, countdown UI, allauth integration.
- Content – Blog with drafts/scheduling, tags, feeds, comments (moderation + spam controls), copy-link sharing only (CSP/offline safe).
- Ads – Placements, campaigns, creatives, events, affiliate links; respects consent.
- SEO – Metadata, internal linking, sitemaps, URL inspector, AI helpers.
- Consent & privacy – Central consent policies, hashed IP/UA helpers, banner/manage pages, cookies/legal templates.
- Device identity – Machine UUID + fingerprint; consent-gated; approval tokens and quotas.
- Security suite (optional) – `security_suite` facade + devices/bots/risk shims; pluggable.
- Theming/i18n – Locales + translation provider; seed locales en/ar/ur; translation command.
- Distribution – Social accounts, plans/jobs/logs; connectors scaffold (log-only until real APIs).
- App registry – Simple registry hooks for pluggability.

## Layout (top-level)
- `apps/` – Django apps (ads, blog, comments, consent, core, seo, site_settings, tags, users, devices, crawler_guard, ai, ai_behavior, i18n, app_registry, distribution, common).
- `security_suite/` – Optional facade + security_devices/bots/risk shims.
- `static/` – Local JS/CSS (Tailwind build), assets, consent/device identity scripts.
- `templates/` – Auth (allauth), ads/seo/blog/comments/users, consent/legal, shared components.

## Quickstart
```bash
python -m venv .vnv
.\.vnv\Scripts\activate   # PowerShell: .\.vnv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install               # only if rebuilding frontend assets
python manage.py migrate  # DB init
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

## Migrations — important note
If you see “table already exists” on a recovered DB, fake the matching migration, then run migrate:
```bash
python manage.py migrate ads 0005 --fake
python manage.py migrate blog 0005 --fake
python manage.py migrate consent 0003 --fake
python manage.py migrate seo 0006 --fake
python manage.py migrate site_settings 0006 --fake
python manage.py migrate tags 0005 --fake
python manage.py migrate comments 0005 --fake
python manage.py migrate users 0004 --fake
python manage.py migrate
```

## Config you’ll likely touch
- `.env` supported; see `settings.py` / `settings_dev.py`.
- `USERS_CONFIG`: VERIFICATION_CODE_TTL_SECONDS, VERIFICATION_CODE_RESEND_COOLDOWN, EMAIL_VERIFICATION_CODE_LENGTH/TYPE.
- `CONSENT_*`: cookie name/options, hash salt.
- `SECURITY_CONFIG`: enable optional `security_suite` facets.
- `DEFAULT_FROM_EMAIL`: for verification emails.

## Email verification flow
- Codes stamped (`verification_code_sent_at`), TTL + resend cooldown enforced.
- Resend button + countdown in `templates/users/verify_email.html`.
- Best-effort email via `send_mail`; on success clears code/timestamp.
- Signal syncs allauth confirmed emails to `email_verified_at`.

## Consent & device identity
- `static/js/device_identity.js` requires consent (security/fraud/analytics) before persisting UUID; attaches IDs/fingerprints on submit only.
- Consent helpers hash IP/UA and centralize cookie options.
- Consent/manage/legal pages live under `templates/consent` and `templates/site_settings`.

## Security suite (optional)
- `security_suite/security/services.py` facade calls `security_devices`, `security_bots`, `security_risk` if present. Shims map to in-project apps; can be split into its own package.

## Frontend bits
- Tailwind build: `static/css/main.css` (built).
- JS: ads, consent, device identity, blog (copy-link sharing), admin suite; no CDNs or HTMX.
- Recaptcha script is commented out for CSP/offline; enable only via a proxied/local solution if needed.

## Tests
```bash
python manage.py test
```
(Pytest is installed if you prefer.)

## Git hygiene
`.gitignore` excludes virtualenvs (.vnv/, .venv/), _recovery/, logs, node_modules, collected static, OS/editor junk.

## Troubleshooting cheatsheet
- Migration conflicts: fake the specific migration, then migrate (see above).
- Verification email issues: set DEFAULT_FROM_EMAIL, configure mail backend, use resend in UI.
- Device ID missing: consent is required; check consent state in the browser.

## App-by-app snapshot
- apps/users: Custom user model, MFA (TOTP), email verification (TTL/resend), notifications, profile completion, allauth adapters, rate limiting hooks, device approval banner.
- apps/ads: Placements, campaigns, creatives, events, affiliate sources/links, rotation/targeting engines, analytics tracker, consent-aware serving, dashboards.
- apps/blog: Posts, drafts, revisions, scheduling, AI editor hooks, feeds, tags integration, SEO helpers, trending/related widgets; copy-link sharing only.
- apps/comments: Generic comments (content type), threading/meta, moderation/spam flags, settings, API, admin moderation tools.
- apps/seo: SEO models, metadata, internal linking engine, sitemaps, URL inspector, AI metadata/schema helpers, management commands, dashboard components.
- apps/consent: Consent policies, decisions/events, middleware/context, hashing helpers (IP/UA), banners/manage views, legal copy templates.
- apps/site_settings: Singleton site config (branding, toggles, legal text), context processors, admin.
- apps/tags: Tag model with hierarchy, suggestions/providers, settings, management commands for keywords/duplicates.
- apps/devices: Device identity models/services (consent-gated), quotas, risk/MFA threshold, approval tokens; decorators and admin actions.
- apps/crawler_guard: Middleware + utilities to classify/block crawlers (stub-compatible with security suite).
- apps/ai / apps/ai_behavior: AI configs/services and behavior/risk tracking (shims).
- apps/i18n: Locales and translation provider; seeded en/ar/ur; translation command for blog content.
- apps/app_registry: Registry scaffolding for pluggable features.
- apps/distribution: Social accounts/plans/jobs/logs; admin suite page; connectors scaffold (log-only by default).
- apps/common/core: Framework utilities (feature flags, cache, middleware, logging, sanitize, base views), template tags, AI client/job helper, signals.
- security_suite/: Optional facade plus security_devices, security_bots, security_risk shims delegating to in-project apps; can be split out as a package.
