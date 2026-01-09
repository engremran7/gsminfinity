from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.blog.models import (
    Category,
    CategoryTranslation,
    Post,
    PostTranslation,
    TagTranslation,
)
from apps.i18n.translation_provider import get_translator
from apps.tags.models import Tag


class Command(BaseCommand):
    help = "Translate blog content (posts/categories/tags) into target languages using configured provider."

    def add_arguments(self, parser):
        parser.add_argument(
            "--langs",
            required=True,
            help="Comma-separated target languages, e.g. ar,es",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing translations instead of skipping",
        )
        parser.add_argument(
            "--source",
            default="en",
            help="Source language code (default=en)",
        )

    def handle(self, *args, **options):
        targets = [c.strip() for c in options["langs"].split(",") if c.strip()]
        force = options.get("force", False)
        source = options.get("source") or "en"
        if not targets:
            self.stderr.write("No target languages provided.")
            return
        translator = get_translator()

        def maybe_translate_texts(texts: list[str], lang: str) -> list[str]:
            if not texts:
                return texts
            try:
                return translator.translate(texts, lang, source)
            except Exception as exc:  # pragma: no cover - defensive
                self.stderr.write(f"Translation error for {lang}: {exc}")
                return texts

        total_posts = 0
        for lang in targets:
            for post in Post.objects.all():
                if (
                    not force
                    and PostTranslation.objects.filter(
                        post=post, language=lang
                    ).exists()
                ):
                    continue
                translated = maybe_translate_texts(
                    [
                        post.title or "",
                        post.summary or "",
                        post.body or "",
                        post.seo_title or "",
                        post.seo_description or "",
                    ],
                    lang,
                )
                title, summary, body, seo_title, seo_desc = translated
                PostTranslation.objects.update_or_create(
                    post=post,
                    language=lang,
                    defaults={
                        "title": title,
                        "summary": summary,
                        "body": body,
                        "seo_title": seo_title or title,
                        "seo_description": seo_desc or summary,
                    },
                )
                total_posts += 1

            for cat in Category.objects.all():
                if (
                    not force
                    and CategoryTranslation.objects.filter(
                        category=cat, language=lang
                    ).exists()
                ):
                    continue
                name = maybe_translate_texts([cat.name or ""], lang)[0]
                CategoryTranslation.objects.update_or_create(
                    category=cat,
                    language=lang,
                    defaults={"name": name},
                )

            for tag in Tag.objects.all():
                if (
                    not force
                    and TagTranslation.objects.filter(tag=tag, language=lang).exists()
                ):
                    continue
                name, desc = maybe_translate_texts(
                    [tag.name or "", getattr(tag, "description", "") or ""], lang
                )
                TagTranslation.objects.update_or_create(
                    tag=tag,
                    language=lang,
                    defaults={"name": name, "description": desc},
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Translated content into {lang} (posts processed: {total_posts})."
                )
            )
