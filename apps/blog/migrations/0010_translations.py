from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tags", "0001_initial"),
        ("blog", "0009_remove_category_category_parent_name_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language", models.CharField(db_index=True, max_length=10)),
                ("title", models.CharField(blank=True, default="", max_length=200)),
                ("summary", models.TextField(blank=True, default="", max_length=1000)),
                ("body", models.TextField(blank=True, default="")),
                ("seo_title", models.CharField(blank=True, default="", max_length=240)),
                ("seo_description", models.CharField(blank=True, default="", max_length=320)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="translations", to="blog.post")),
            ],
            options={
                "verbose_name": "Post Translation",
                "verbose_name_plural": "Post Translations",
                "unique_together": {("post", "language")},
            },
        ),
        migrations.CreateModel(
            name="TagTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language", models.CharField(db_index=True, max_length=10)),
                ("name", models.CharField(max_length=80)),
                ("description", models.TextField(blank=True, default="")),
                ("tag", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="translations", to="tags.tag")),
            ],
            options={
                "verbose_name": "Tag Translation",
                "verbose_name_plural": "Tag Translations",
                "unique_together": {("tag", "language")},
            },
        ),
        migrations.CreateModel(
            name="CategoryTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language", models.CharField(db_index=True, max_length=10)),
                ("name", models.CharField(max_length=120)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="translations", to="blog.category")),
            ],
            options={
                "verbose_name": "Category Translation",
                "verbose_name_plural": "Category Translations",
                "unique_together": {("category", "language")},
            },
        ),
        migrations.AddIndex(
            model_name="posttranslation",
            index=models.Index(fields=["language"], name="post_translation_lang_idx"),
        ),
        migrations.AddIndex(
            model_name="categorytranslation",
            index=models.Index(fields=["language"], name="category_translation_lang_idx"),
        ),
        migrations.AddIndex(
            model_name="tagtranslation",
            index=models.Index(fields=["language"], name="tag_translation_lang_idx"),
        ),
    ]
