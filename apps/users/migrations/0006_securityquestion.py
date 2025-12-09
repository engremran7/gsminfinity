from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_username_change_limits"),
    ]

    operations = [
        migrations.CreateModel(
            name="SecurityQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_key", models.CharField(choices=[("first_pet", "Name of your first pet?"), ("mother_maiden", "What is your mother's maiden name?"), ("first_school", "Name of your first school?"), ("city_born", "City where you were born?"), ("custom", "Custom question")], default="first_pet", max_length=50)),
                ("custom_question", models.CharField(blank=True, default="", max_length=255)),
                ("answer_hash", models.CharField(max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="security_question", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Security Question",
                "verbose_name_plural": "Security Questions",
            },
        ),
    ]

