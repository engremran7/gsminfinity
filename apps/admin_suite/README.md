# Admin Suite

Custom staff-gated admin shell for content, security, ads, SEO, distribution, users, and settings.

## Capabilities
- Staff-only login with throttling; non-staff are logged out and warned.
- Sections: overview, security (devices/crawlers/risk), consent, pages, blog, content, marketing, AI, distribution, ads, tags, SEO, registry, comments, users, settings/email.
- Command palette JSON endpoint for quick navigation.
- Distribution: manage SocialAccounts (tokens/config), enable/disable, retry/cancel jobs, view settings/stats.
- Security: device/crawler/risk actions; breadcrumb + quick actions.

## Key Files
- `views.py` — Auto-imports views_* modules; exports helpers from `views_shared`.
- `views_shared.py` — staff_member_required wrapper (Admin Suite login), breadcrumb/render helpers.
- `views_auth.py` — Admin login, security question flows.
- `views_distribution.py` — Distribution page (accounts/jobs/settings).
- `templates/admin_suite/*` — Layout, nav, header, section pages; padding adjusted to avoid footer overlap.

## Notes
- Uses local CSS/JS; no CDNs/HTMX.
- Redirects to admin_suite login for staff gating; honors ADMIN_SUITE_ENABLED flag.
