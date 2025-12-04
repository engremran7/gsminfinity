# GSMInfinity

Enterprise-grade Django + frontend stack for content, ads, SEO, consent, users, devices, and optional security suite.

## Key Features
- **Users/MFA/Email verification**: Custom user model, TOTP, verification codes with TTL/resend/cooldown and UI countdown.
- **Content**: Blog with drafts, scheduling, tags, feeds, comments with moderation/spam controls.
- **Ads**: Placements, campaigns, creatives, events, affiliate links; consent-aware ad serving.
- **SEO**: Metadata, internal links, sitemaps, URL inspector, AI helpers.
- **Consent & privacy**: Central consent policies, hashed IP/UA helpers, consent banners, cookies policy templates.
- **Device identity**: Optional machine UUID + fingerprint gated by consent; only attached on submit.
- **Security suite (optional)**: `security_suite` facade + devices/bots/risk shims for pluggable security.
- **Theming/i18n**: i18n themes app, theme switcher middleware stub.

## Project Layout
- `apps/` – Django apps (ads, blog, comments, consent, core, seo, site_settings, tags, users, devices, crawler_guard, ai, ai_behavior, i18n_themes, app_registry, distribution, common).
- `security_suite/` – Optional pip-installable facade + security_devices/bots/risk shims.
- `static/` – JS, CSS (Tailwind build), assets; consent/device identity scripts, summernote overrides.
- `templates/` – Auth flows (allauth), ads/seo/blog/comments/users, consent/legal, components.
- `_recovery/` – Audit dumps (ignored).

## Prerequisites
- Python 3.11+
- Node 18+ (for frontend build if needed)
- Virtualenv recommended (`.vnv/` or `.venv/`)

## Setup
```bash
python -m venv .vnv
. .vnv/Scripts/activate   # Windows PowerShell: .\.vnv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install  # if you need to rebuild static assets
python manage.py migrate  # DB init
python manage.py createsuperuser  # if needed
```

## Running
```bash
python manage.py runserver 0.0.0.0:8000
```

## Migrations Notes
Recent migrations were aligned with an existing DB. If you hit “table already exists”:
- Fake the specific migration, then run `python manage.py migrate`.
Examples:
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

## Configuration (env/settings)
- `.env` support (see `settings.py`/`settings_dev.py` for defaults)
- Notable settings:
  - `USERS_CONFIG`: `VERIFICATION_CODE_TTL_SECONDS`, `VERIFICATION_CODE_RESEND_COOLDOWN`, etc.
  - `CONSENT_*`: cookie name/options, hash salt.
  - `SECURITY_CONFIG` (optional security_suite).
  - `DEFAULT_FROM_EMAIL` for verification emails.

## Email Verification Flow
- Codes generated/stamped with `verification_code_sent_at`.
- TTL and resend cooldown enforced; resend button + countdown in UI (`templates/users/verify_email.html`).
- Codes sent via `send_mail` best-effort; on success, clears code/timestamp.
- Signal syncs allauth confirmed emails to `email_verified_at`.

## Consent & Device Identity
- `static/js/device_identity.js` now **requires consent** (security/fraud/analytics) before persisting UUID; attaches IDs/fingerprints only on submit.
- Consent helpers hash IP/UA and centralize cookie options.
- Consent templates and legal pages under `templates/consent` and `templates/site_settings`.

## Security Suite (optional)
- `security_suite/security/services.py` facade delegates to `security_devices`, `security_bots`, `security_risk` if installed.
- Currently shims to in-project apps; can be packaged separately.

## Frontend
- Tailwind-based styles in `static/css/main.css` (built) and `static/src_css/main.css` (source).
- JS: ads, consent, device identity, i18n themes, summernote assets.

## Running Tests
```bash
python manage.py test
```
(Adjust if you add pytest configuration.)

## Lint/Format
- Not enforced here; add your preferred tools (black/ruff/isort/prettier/eslint) as needed.

## Git Hygiene
- `.gitignore` excludes virtualenvs (`.vnv/`, `.venv/`), `_recovery/`, logs, node_modules, collected static, and OS/editor junk.
- `git gc --prune=now` already run; repo pushed to `origin/main`.

## Troubleshooting
- Migration conflicts: fake the migration then re-run migrate (see above).
- Verification emails: ensure `DEFAULT_FROM_EMAIL` and mail backend configured; resend in UI.
- Consent/device ID: identifiers won’t persist without consent; check `Consent.getState()` in the browser.
