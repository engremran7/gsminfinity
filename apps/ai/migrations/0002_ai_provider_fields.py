from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0001_initial"),
    ]

    # All fields already exist in 0001; keep this migration as a no-op for clean installs.
    operations = []
