# Users App

Custom user management with allauth integration, email verification, MFA hooks, notifications, and device approval flows.

## Capabilities
- Custom user model with profile fields and rate-limit middleware.
- Email verification: TTL + resend cooldown, countdown UI (`templates/users/verify_email.html`), signals to sync `email_verified_at`.
- MFA/TOTP hooks, password reset, security questions, throttled login in admin suite.
- Notifications: list/detail JSON endpoints, non-HTMX actions.
- Device approval: pending token stored in session, approval/eviction views, banner on `users/devices`.

## Key Files
- `models.py` — User model and related settings.
- `views.py` — Login, devices, device approval/eviction, dashboard/profile.
- `views_notifications.py` — Notification APIs and pages.
- `middleware/` — Profile completion, rate limits.
- `services/` — Admin profile helpers, recaptcha, device utilities.

## Templates
- `templates/account/*` — allauth flows (login/signup/reset).
- `templates/users/verify_email.html` — countdown + resend.
- `templates/users/devices.html` — device list + approval banner.

## Signals
- Sync allauth confirmed emails into `email_verified_at`.

## Dependencies
- django-allauth, django-crispy-forms, crispy-bootstrap5, requests (recaptcha), PyJWT (allauth provider).
