"""
SEO Celery Tasks - Background automation for sitemap building, link checking, and URL inspection.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=120,
    time_limit=180,
)
def build_sitemap_async(self, sitemap_type: str = "all", notify: bool = False):
    """
    Build sitemap entries for published content asynchronously.

    Args:
        sitemap_type: 'blog', 'firmwares', 'tags', 'pages', or 'all'
        notify: Send notification to search engines after building
    """
    try:
        from django.contrib.sites.models import Site

        from apps.seo.models import SitemapEntry

        site = Site.objects.get_current()
        base_url = f"https://{site.domain}"
        entries_created = 0

        if sitemap_type in ("blog", "all"):
            try:
                from apps.blog.models import Post, PostStatus

                posts = Post.objects.filter(status=PostStatus.PUBLISHED)

                for post in posts.iterator():
                    entry, created = SitemapEntry.objects.update_or_create(
                        url=f"{base_url}/blog/{post.slug}/",
                        defaults={
                            "changefreq": "weekly",
                            "priority": 0.8,
                            "lastmod": post.updated_at or post.created_at,
                            "is_active": True,
                        },
                    )
                    if created:
                        entries_created += 1

                logger.info(f"Sitemap: Processed {posts.count()} blog posts")
            except Exception as e:
                logger.error(f"Sitemap blog error: {e}")

        if sitemap_type in ("firmwares", "all"):
            try:
                from apps.firmwares.models import Model

                models = Model.objects.filter(is_active=True)

                for model in models.iterator():
                    entry, created = SitemapEntry.objects.update_or_create(
                        url=f"{base_url}/firmwares/{model.brand.slug}/{model.slug}/",
                        defaults={
                            "changefreq": "daily",
                            "priority": 0.9,
                            "lastmod": model.updated_at
                            if hasattr(model, "updated_at")
                            else timezone.now(),
                            "is_active": True,
                        },
                    )
                    if created:
                        entries_created += 1

                logger.info(f"Sitemap: Processed {models.count()} firmware models")
            except Exception as e:
                logger.error(f"Sitemap firmwares error: {e}")

        if sitemap_type in ("tags", "all"):
            try:
                from apps.tags.models import Tag

                tags = Tag.objects.filter(is_active=True)

                for tag in tags.iterator():
                    entry, created = SitemapEntry.objects.update_or_create(
                        url=f"{base_url}/tags/{tag.slug}/",
                        defaults={
                            "changefreq": "weekly",
                            "priority": 0.6,
                            "lastmod": tag.updated_at
                            if hasattr(tag, "updated_at")
                            else timezone.now(),
                            "is_active": True,
                        },
                    )
                    if created:
                        entries_created += 1

                logger.info(f"Sitemap: Processed {tags.count()} tags")
            except Exception as e:
                logger.error(f"Sitemap tags error: {e}")

        # Invalidate sitemap cache
        cache.delete_many(
            [
                "sitemap_index",
                f"sitemap_{sitemap_type}",
                "sitemap_all",
            ]
        )

        logger.info(
            f"Sitemap build complete: {entries_created} new entries for type '{sitemap_type}'"
        )

        # Notify search engines if requested
        if notify:
            notify_search_engines.delay()

        return {"status": "success", "entries_created": entries_created}

    except Exception as exc:
        logger.error(f"Sitemap build failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def check_links_async(self, limit: int = 100):
    """
    Check sitemap URLs for broken links and update status.

    Args:
        limit: Maximum number of URLs to check per run
    """
    import requests

    from apps.seo.models import SitemapEntry

    try:
        entries = SitemapEntry.objects.filter(
            is_active=True, last_checked__isnull=True
        ).order_by("?")[:limit]

        if not entries.exists():
            # Check oldest entries if no unchecked ones
            entries = SitemapEntry.objects.filter(is_active=True).order_by(
                "last_checked"
            )[:limit]

        results = {"checked": 0, "ok": 0, "broken": 0}

        for entry in entries:
            try:
                response = requests.head(entry.url, timeout=10, allow_redirects=True)
                entry.http_status = response.status_code
                entry.last_checked = timezone.now()

                if response.status_code >= 400:
                    results["broken"] += 1
                    logger.warning(
                        f"Broken link detected: {entry.url} (HTTP {response.status_code})"
                    )
                else:
                    results["ok"] += 1

                entry.save(update_fields=["http_status", "last_checked"])
                results["checked"] += 1

            except requests.RequestException as e:
                entry.http_status = 0
                entry.last_checked = timezone.now()
                entry.save(update_fields=["http_status", "last_checked"])
                results["broken"] += 1
                logger.error(f"Link check failed for {entry.url}: {e}")

        logger.info(
            f"Link check complete: {results['checked']} checked, {results['ok']} OK, {results['broken']} broken"
        )
        return results

    except Exception as exc:
        logger.error(f"Link check task failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2)
def inspect_url_async(self, url: str) -> dict:
    """
    Inspect a single URL for SEO metrics and HTTP status.

    Args:
        url: The URL to inspect

    Returns:
        Dict with HTTP status, response time, redirect chain, etc.
    """
    import time

    import requests

    try:
        result = {
            "url": url,
            "inspected_at": timezone.now().isoformat(),
            "status_code": None,
            "response_time_ms": None,
            "redirect_chain": [],
            "headers": {},
            "error": None,
        }

        start = time.time()
        response = requests.get(url, timeout=15, allow_redirects=True)
        result["response_time_ms"] = round((time.time() - start) * 1000)
        result["status_code"] = response.status_code

        # Capture redirect chain
        if response.history:
            result["redirect_chain"] = [
                {"url": r.url, "status": r.status_code} for r in response.history
            ]

        # Capture relevant SEO headers
        seo_headers = ["content-type", "x-robots-tag", "link", "cache-control"]
        result["headers"] = {
            k: v for k, v in response.headers.items() if k.lower() in seo_headers
        }

        logger.info(f"URL inspection complete: {url} (HTTP {result['status_code']})")
        return result

    except requests.RequestException as e:
        logger.error(f"URL inspection failed for {url}: {e}")
        return {
            "url": url,
            "inspected_at": timezone.now().isoformat(),
            "status_code": None,
            "error": str(e),
        }


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def notify_search_engines(self):
    """
    Notify Google and Bing of sitemap updates via ping.
    """
    import requests
    from django.contrib.sites.models import Site

    try:
        site = Site.objects.get_current()
        sitemap_url = f"https://{site.domain}/sitemap.xml"

        results = {}

        # Ping Google
        try:
            google_url = f"https://www.google.com/ping?sitemap={sitemap_url}"
            resp = requests.get(google_url, timeout=10)
            results["google"] = resp.status_code == 200
            logger.info(f"Google sitemap ping: HTTP {resp.status_code}")
        except Exception as e:
            results["google"] = False
            logger.error(f"Google ping failed: {e}")

        # Ping Bing
        try:
            bing_url = f"https://www.bing.com/ping?sitemap={sitemap_url}"
            resp = requests.get(bing_url, timeout=10)
            results["bing"] = resp.status_code == 200
            logger.info(f"Bing sitemap ping: HTTP {resp.status_code}")
        except Exception as e:
            results["bing"] = False
            logger.error(f"Bing ping failed: {e}")

        return results

    except Exception as exc:
        logger.error(f"Search engine notification failed: {exc}")
        raise self.retry(exc=exc)


@shared_task
def regenerate_seo_for_content_type(content_type_id: int, batch_size: int = 50):
    """
    Regenerate SEO metadata for all objects of a given content type.
    Useful for bulk SEO updates after algorithm changes.
    """
    from django.contrib.contenttypes.models import ContentType

    from apps.seo.auto import apply_post_seo

    try:
        ct = ContentType.objects.get(pk=content_type_id)
        model_class = ct.model_class()

        if not model_class:
            logger.error(f"Model class not found for content type {content_type_id}")
            return

        # Handle blog posts
        if ct.app_label == "blog" and ct.model == "post":
            from apps.blog.models import PostStatus

            queryset = model_class.objects.filter(status=PostStatus.PUBLISHED)

            count = 0
            for obj in queryset.iterator():
                try:
                    apply_post_seo(obj)
                    count += 1
                except Exception as e:
                    logger.error(
                        f"SEO regeneration failed for {ct.model} {obj.pk}: {e}"
                    )

            logger.info(f"SEO regenerated for {count} {ct.model} objects")
            return {"regenerated": count}

        logger.warning(
            f"SEO regeneration not implemented for {ct.app_label}.{ct.model}"
        )
        return {"regenerated": 0}

    except Exception as e:
        logger.error(f"SEO regeneration task failed: {e}")
        return {"error": str(e)}
