# GSMInfinity

Full-stack Django platform for content, ads, SEO, consent, users, devices, and an optional pluggable security suite. This README is a human-friendly map so you can onboard fast and know where the sharp edges are.

## What’s inside
- **Users / MFA / Email verification** – Custom user model, TOTP, verification codes with TTL + resend + cooldown, countdown UI, allauth integration.
- **Content** – Blog with drafts/scheduling, tags, feeds, comments (moderation + spam controls).
- **Ads** – Placements, campaigns, creatives, events, affiliate links; respects consent.
- **SEO** – Metadata, internal linking, sitemaps, URL inspector, AI helpers.
- **Consent & privacy** – Central consent policies, hashed IP/UA helpers, banner/manage pages, cookies/legal templates.
- **Device identity** – Optional machine UUID + fingerprint, now gated by consent and only attached on submit.
- **Security suite (optional)** – `security_suite` facade + devices/bots/risk shims; pluggable.
- **Theming/i18n** – i18n themes app, theme switcher middleware stub.

## Layout (top-level)
- `apps/` – Django apps (ads, blog, comments, consent, core, seo, site_settings, tags, users, devices, crawler_guard, ai, ai_behavior, i18n_themes, app_registry, distribution, common).
- `security_suite/` – Optional installable facade + security_devices/bots/risk shims.
- `static/` – JS, CSS (Tailwind build + sources), assets, consent/device identity scripts, summernote overrides.
- `templates/` – Auth (allauth), ads/seo/blog/comments/users, consent/legal, shared components.
- `_recovery/` – Audit dumps (ignored).

## Quickstart
```bash
python -m venv .vnv
. .vnv/Scripts/activate   # PowerShell: .\.vnv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install               # if rebuilding frontend assets
python manage.py migrate  # DB init
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

## Migrations — important note
The recovered DB already had these tables. If you see “table already exists”, fake the matching migration, then run migrate:
```
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
- `.env` supported; see `settings.py`/`settings_dev.py`.
- `USERS_CONFIG`: `VERIFICATION_CODE_TTL_SECONDS`, `VERIFICATION_CODE_RESEND_COOLDOWN`, `EMAIL_VERIFICATION_CODE_LENGTH/TYPE`.
- `CONSENT_*`: cookie name/options, hash salt.
- `SECURITY_CONFIG`: enable optional security_suite facets.
- `DEFAULT_FROM_EMAIL`: for verification emails.

## Email verification flow
- Codes stamped (`verification_code_sent_at`), TTL + resend cooldown enforced.
- Resend button + countdown in `templates/users/verify_email.html`.
- Best-effort email via `send_mail`; on success clears code/timestamp.
- Signal syncs allauth confirmed emails to `email_verified_at`.

## Consent & device identity
- `static/js/device_identity.js` **requires consent** (security/fraud/analytics) before persisting UUID; attaches IDs/fingerprints on submit only.
- Consent helpers hash IP/UA and centralize cookie options.
- Consent/manage/legal pages live under `templates/consent` and `templates/site_settings`.

## Security suite (optional)
- `security_suite/security/services.py` facade calls `security_devices`, `security_bots`, `security_risk` if present. Shims map to in-project apps; can be split into its own package.

## Frontend bits
- Tailwind build: `static/css/main.css` (built) and `static/src_css/main.css` (source).
- JS: ads, consent, device identity, i18n themes, summernote assets.

## Tests
```bash
python manage.py test
```
(Add pytest if you prefer.)

## Git hygiene
- `.gitignore` excludes virtualenvs (`.vnv/`, `.venv/`), `_recovery/`, logs, node_modules, collected static, OS/editor junk.
- `git gc --prune=now` already run; latest pushed to `origin/main`.

## Troubleshooting cheatsheet
- Migration conflicts: fake the specific migration, then `migrate` (see above).
- Verification email issues: set `DEFAULT_FROM_EMAIL`, configure mail backend, use resend in UI.
- Device ID missing: consent is required; check `Consent.getState()` in the browser.
