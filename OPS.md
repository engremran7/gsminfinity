# GSMInfinity Operations Guide (OPS.md)

> UTF-8 text, LF line endings only. This document describes concrete, repeatable
> commands to run, test, and operate the GSMInfinity stack.

---

## 1. Environment & Configuration

1. Copy `.env.sample` to `.env` and adjust values:
   ```bash
   cp .env.sample .env
   ```

2. Ensure at least:

   * `DJANGO_SECRET_KEY` is set to a strong random value (64+ chars).
   * `DJANGO_DEBUG=0` in production, `1` only on developer machines.
   * `DJANGO_ALLOWED_HOSTS` contains all public hostnames.
   * Database variables (`DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) match your DB.
   * `TRUSTED_PROXY_COUNT` is set if you run behind a load balancer or reverse proxy.

---

## 2. Backend: Local Development

From the backend project root (where `manage.py` lives):

```bash
python -m venv .venv
. .venv/bin/activate

pip install -r requirements.txt
```

Run database migrations and start the dev server:

```bash
python manage.py migrate
python manage.py createsuperuser  # optional, for admin access
python manage.py runserver 0.0.0.0:8000
```

Key dev defaults:

* Uses `gsminfinity.development` settings for relaxed HTTP-only, console email, verbose logging.
* SQLite is used by default if `DB_NAME` is empty.

---

## 3. Backend: Production Deployment

Environment:

* `DJANGO_DEBUG=0`
* `DJANGO_SETTINGS_MODULE=gsminfinity.settings`
* `DJANGO_ALLOWED_HOSTS` set to all public hostnames.
* Database configured to a production-ready engine (e.g. PostgreSQL).

Typical steps (adapt for your process manager / container):

```bash
pip install -r requirements.txt

python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Run via ASGI/WSGI server (examples):

```bash
gunicorn gsminfinity.wsgi:application
uvicorn gsminfinity.asgi:application
```

Ensure:

* Reverse proxy (nginx/ALB/etc.) sets `X-Forwarded-For` correctly and `TRUSTED_PROXY_COUNT` matches.
* TLS termination is done at the edge proxy; app enforces `SECURE_*` settings from `gsminfinity.settings`.

---

## 4. Tests & CI

Run the backend test suite:

```bash
pytest
# or, if using Django's test runner:
python manage.py test
```

Recommended CI steps (per job):

1. Check out code.
2. Install Python, create venv.
3. `pip install -r requirements.txt` (and any `requirements-dev.txt` if present).
4. `python manage.py migrate --noinput` against a disposable DB.
5. `pytest` (or `python manage.py test`).
6. Optionally run:
   ```bash
   python -m compileall .
   ```
   to catch syntax errors in all modules.

CI guidelines:

* Do not rely on `.env`; set critical variables explicitly in CI (e.g. `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS=testserver`).
* Use an in-memory or containerized DB (PostgreSQL) consistent with production settings.

---

## 5. Static Files & Media

* Run `python manage.py collectstatic --noinput` in build/release jobs.
* Serve `/static/` via your reverse proxy or object storage (S3, etc.).
* Protect `/media/` uploads via appropriate auth if sensitive.

---

## 6. Observability & Logging

* Logging is structured and centralized via `LOGGING` in `gsminfinity/settings.py`.
* For Sentry (or similar), set:
  * `SENTRY_DSN`
  * `SENTRY_ENVIRONMENT` (e.g. `production`, `staging`)

Example integration (environment only; actual wiring is in code if enabled):

```bash
export SENTRY_DSN=https://public-key@o000000.ingest.sentry.io/000000
export SENTRY_ENVIRONMENT=production
```

Monitor:

* 5xx error rates at the proxy and application.
* DB connection pool saturation.
* Queue / worker health if you enable background jobs.

---

## 7. Zero-Downtime Deployments (Checklist)

* Run migrations before switching traffic to new release.
* Ensure static assets for the new release are uploaded and available.
* Keep `TRUSTED_PROXY_COUNT` synced with infrastructure changes.
* Never deploy with `DJANGO_DEBUG=1` in production.

---

## 8. Security Checklist

* `DJANGO_DEBUG=0` in production.
* Non-empty, non-default `DJANGO_SECRET_KEY`.
* `ALLOWED_HOSTS` correctly configured.
* TLS termination on all external endpoints.
* Admin URLs protected (IP allowlist, VPN, or SSO).
* Regularly rotate DB and third-party credentials.

