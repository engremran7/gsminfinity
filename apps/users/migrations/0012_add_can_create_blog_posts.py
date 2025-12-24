# Generated migration - add can_create_blog_posts field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_add_notification_preferences'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='can_create_blog_posts',
            field=models.BooleanField(default=True),
        ),
    ]
