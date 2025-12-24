# Generated manually for adding country detection fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_add_can_create_blog_posts'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='country_detected_at',
            field=models.DateTimeField(blank=True, help_text='When the country was auto-detected from IP', null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='phone_country_code',
            field=models.CharField(blank=True, default='', help_text='Phone country code (e.g., +1, +44, +966)', max_length=5),
        ),
    ]
