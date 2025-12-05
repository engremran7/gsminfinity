from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("consent", "0004_alter_consentcategory_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="consentpolicy",
            name="public_slug",
            field=models.SlugField(
                blank=True,
                default="",
                help_text="Slug for public page hosting (e.g., 'privacy').",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="consentpolicy",
            name="public_url",
            field=models.URLField(
                blank=True,
                default="",
                help_text="Override URL if hosted externally.",
            ),
        ),
    ]
