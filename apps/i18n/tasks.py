"""
i18n Celery Tasks - Background automation for translations.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=60,
    time_limit=120,
)
def auto_translate_key(
    self, key_id: int, target_locale: str, provider: str | None = None
):
    """
    Auto-translate a single TranslationKey to target locale.

    Args:
        key_id: TranslationKey primary key
        target_locale: Target locale code
        provider: Optional provider override
    """
    try:
        from apps.i18n.models import TranslationKey
        from apps.i18n.services import auto_translate

        key = TranslationKey.objects.get(pk=key_id)
        result = auto_translate(key.app_id, key, target_locale, provider)

        if result:
            logger.info(f"Auto-translated key {key.key} to {target_locale}")
            return {"status": "success", "key": key.key, "locale": target_locale}
        else:
            logger.warning(f"Failed to translate key {key.key} to {target_locale}")
            return {"status": "failed", "key": key.key}

    except Exception as exc:
        logger.error(f"Auto-translate task failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
    soft_time_limit=180,
    time_limit=300,
)
def batch_translate_locale(
    self,
    app_id: str,
    target_locale: str,
    namespace: str | None = None,
    limit: int = 100,
):
    """
    Batch translate missing translations for a locale.

    Args:
        app_id: Application identifier
        target_locale: Target locale code
        namespace: Optional namespace filter
        limit: Maximum keys to process
    """
    try:
        from apps.i18n.services import auto_translate_batch

        results = auto_translate_batch(app_id, target_locale, namespace, limit)
        logger.info(f"Batch translate {app_id}/{target_locale}: {results}")
        return results

    except Exception as exc:
        logger.error(f"Batch translate task failed: {exc}")
        raise self.retry(exc=exc)


@shared_task
def process_missing_key_logs(app_id: str | None = None, limit: int = 50):
    """
    Process MissingKeyLog entries and queue them for translation.

    Args:
        app_id: Optional app filter
        limit: Maximum entries to process
    """
    try:
        from django.db.models import Count

        from apps.i18n.models import Locale, MissingKeyLog, TranslationKey

        # Find most requested missing keys
        qs = (
            MissingKeyLog.objects.values("app_id", "namespace", "key")
            .annotate(request_count=Count("id"))
            .order_by("-request_count")
        )

        if app_id:
            qs = qs.filter(app_id=app_id)

        entries = qs[:limit]
        created_count = 0
        queued_count = 0

        supported_locales = list(Locale.objects.values_list("code", flat=True))

        for entry in entries:
            # Create TranslationKey if not exists
            key, created = TranslationKey.objects.get_or_create(
                app_id=entry["app_id"],
                namespace=entry["namespace"],
                key=entry["key"],
                defaults={
                    "status": "pending",
                    "description": f"Auto-created from missing key log ({entry['request_count']} requests)",
                },
            )

            if created:
                created_count += 1

                # Queue translation for all supported locales
                for locale in supported_locales:
                    if locale not in ("en", "en-US"):
                        auto_translate_key.delay(key.pk, locale)
                        queued_count += 1

        # Clean up processed entries
        MissingKeyLog.objects.filter(
            app_id__in=[e["app_id"] for e in entries],
            namespace__in=[e["namespace"] for e in entries],
            key__in=[e["key"] for e in entries],
        ).delete()

        logger.info(
            f"Processed missing keys: {created_count} created, {queued_count} translations queued"
        )
        return {"created": created_count, "queued": queued_count}

    except Exception as e:
        logger.error(f"Process missing keys failed: {e}")
        return {"error": str(e)}


@shared_task
def invalidate_translation_cache(app_id: str, locale: str | None = None):
    """
    Invalidate translation cache for an app/locale.

    Args:
        app_id: Application identifier
        locale: Optional locale to invalidate (all if None)
    """
    try:
        pattern = f"i18n_bundle:{app_id}:{locale or '*'}:*"

        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern(pattern)
        else:
            # Fallback: try to delete specific known keys
            from apps.i18n.models import Locale

            locales = (
                [locale] if locale else Locale.objects.values_list("code", flat=True)
            )

            for loc in locales:
                cache.delete(f"i18n_bundle:{app_id}:{loc}::0")
                cache.delete(f"i18n_theme:{app_id}:{loc}::light")
                cache.delete(f"i18n_theme:{app_id}:{loc}::dark")

        logger.info(f"Translation cache invalidated for {app_id}/{locale or 'all'}")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        return {"error": str(e)}


@shared_task(bind=True, max_retries=2)
def translate_blog_post(self, post_id: int, target_locales: list[str] | None = None):
    """
    Translate a blog post to target locales.

    Args:
        post_id: Blog post primary key
        target_locales: List of target locales (uses all if None)
    """
    try:
        from django.conf import settings

        from apps.blog.models import Post, PostTranslation
        from apps.i18n.models import Locale
        from apps.i18n.translation_provider import get_translator

        post = Post.objects.get(pk=post_id)

        # Get target locales
        if not target_locales:
            target_locales = list(
                Locale.objects.exclude(code__in=["en", "en-US"]).values_list(
                    "code", flat=True
                )
            )

        provider_name = getattr(settings, "TRANSLATION_PROVIDER", "dummy")
        translator = get_translator(provider_name)

        if not translator:
            logger.warning(f"No translator available for provider: {provider_name}")
            return {"status": "no_provider"}

        results = {"translated": 0, "failed": 0}

        for locale in target_locales:
            try:
                # Translate title
                title = translator.translate(post.title, "en", locale)
                # Translate summary
                summary = (
                    translator.translate(post.summary or "", "en", locale)
                    if post.summary
                    else ""
                )

                PostTranslation.objects.update_or_create(
                    post=post,
                    locale=locale,
                    defaults={
                        "title": title or post.title,
                        "summary": summary,
                        "seo_title": title[:60] if title else post.title[:60],
                        "seo_description": summary[:160] if summary else "",
                    },
                )
                results["translated"] += 1

            except Exception as e:
                logger.error(f"Failed to translate post {post_id} to {locale}: {e}")
                results["failed"] += 1

        logger.info(f"Blog post {post_id} translation: {results}")
        return results

    except Exception as exc:
        logger.error(f"Blog post translation failed: {exc}")
        raise self.retry(exc=exc)


@shared_task
def sync_translation_stats():
    """
    Calculate and cache translation coverage statistics.
    """
    try:
        from apps.i18n.models import Locale, TranslationKey, TranslationValue

        stats = {}

        total_keys = TranslationKey.objects.count()
        locales = Locale.objects.all()

        for locale in locales:
            translated = TranslationValue.objects.filter(
                locale=locale.code, status="approved"
            ).count()

            coverage = (translated / total_keys * 100) if total_keys > 0 else 0

            stats[locale.code] = {
                "total_keys": total_keys,
                "translated": translated,
                "coverage_percent": round(coverage, 1),
            }

        # Cache for 1 hour
        cache.set("i18n_translation_stats", stats, timeout=3600)

        logger.info(f"Translation stats synced for {len(locales)} locales")
        return stats

    except Exception as e:
        logger.error(f"Translation stats sync failed: {e}")
        return {"error": str(e)}
