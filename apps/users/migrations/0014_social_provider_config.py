# Generated manually for social provider config models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_add_country_detected_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='SocialProviderConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('provider', models.CharField(choices=[('google', 'Google OAuth 2.0'), ('facebook', 'Facebook Login'), ('microsoft', 'Microsoft Azure AD'), ('github', 'GitHub OAuth'), ('apple', 'Apple Sign In'), ('twitter', 'Twitter / X'), ('linkedin', 'LinkedIn'), ('discord', 'Discord'), ('slack', 'Slack')], max_length=32, unique=True)),
                ('display_name', models.CharField(blank=True, help_text='Custom display name', max_length=128)),
                ('auth_flow_type', models.CharField(choices=[('api_credentials', 'API Credentials Only (Client ID + Secret)'), ('browser_oauth', 'Browser OAuth Required'), ('service_account', 'Service Account (JSON)')], default='api_credentials', max_length=32)),
                ('_client_id_encrypted', models.BinaryField(blank=True, db_column='client_id_encrypted', null=True)),
                ('_client_secret_encrypted', models.BinaryField(blank=True, db_column='client_secret_encrypted', null=True)),
                ('_additional_config_encrypted', models.BinaryField(blank=True, db_column='additional_config_encrypted', null=True)),
                ('tenant_id', models.CharField(blank=True, help_text='Microsoft Azure Tenant ID', max_length=255)),
                ('team_id', models.CharField(blank=True, help_text='Apple Team ID', max_length=64)),
                ('key_id', models.CharField(blank=True, help_text='Apple Key ID', max_length=64)),
                ('_access_token_encrypted', models.BinaryField(blank=True, db_column='access_token_encrypted', null=True)),
                ('_refresh_token_encrypted', models.BinaryField(blank=True, db_column='refresh_token_encrypted', null=True)),
                ('token_expiry', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('unconfigured', 'Not Configured'), ('pending_oauth', 'Pending OAuth Flow'), ('active', 'Active'), ('error', 'Configuration Error'), ('disabled', 'Disabled')], default='unconfigured', max_length=32)),
                ('is_enabled', models.BooleanField(default=True)),
                ('scopes', models.JSONField(blank=True, default=list, help_text='OAuth scopes to request')),
                ('settings_json', models.JSONField(blank=True, default=dict, help_text='Provider-specific settings')),
                ('last_tested_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True, default='')),
                ('users_count', models.IntegerField(default=0, help_text='Users who signed up via this provider')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_social_configs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Social Auth Provider',
                'verbose_name_plural': 'Social Auth Providers',
                'ordering': ['provider'],
            },
        ),
        migrations.CreateModel(
            name='AppStoreCredentials',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('store', models.CharField(choices=[('google_play', 'Google Play Console'), ('apple_appstore', 'Apple App Store Connect'), ('huawei_appgallery', 'Huawei AppGallery'), ('samsung_galaxy', 'Samsung Galaxy Store'), ('amazon_appstore', 'Amazon Appstore'), ('microsoft_store', 'Microsoft Store'), ('xiaomi_getapps', 'Xiaomi GetApps'), ('oppo_appmarket', 'OPPO App Market'), ('vivo_appstore', 'Vivo App Store')], max_length=32, unique=True)),
                ('display_name', models.CharField(blank=True, max_length=128)),
                ('auth_type', models.CharField(choices=[('service_account', 'Service Account (JSON)'), ('api_key', 'API Key'), ('oauth2', 'OAuth 2.0'), ('username_password', 'Username & Password')], default='service_account', max_length=32)),
                ('_credentials_encrypted', models.BinaryField(blank=True, db_column='credentials_encrypted', null=True)),
                ('_api_key_encrypted', models.BinaryField(blank=True, db_column='api_key_encrypted', null=True)),
                ('account_email', models.EmailField(blank=True, max_length=254)),
                ('account_id', models.CharField(blank=True, help_text='Developer account ID', max_length=255)),
                ('team_id', models.CharField(blank=True, help_text='Team/Organization ID', max_length=255)),
                ('service_account_json_path', models.CharField(blank=True, max_length=512)),
                ('_access_token_encrypted', models.BinaryField(blank=True, db_column='access_token_encrypted', null=True)),
                ('_refresh_token_encrypted', models.BinaryField(blank=True, db_column='refresh_token_encrypted', null=True)),
                ('token_expiry', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('unconfigured', 'Not Configured'), ('pending_auth', 'Pending Authentication'), ('active', 'Active'), ('error', 'Configuration Error'), ('disabled', 'Disabled')], default='unconfigured', max_length=32)),
                ('is_enabled', models.BooleanField(default=True)),
                ('last_tested_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True, default='')),
                ('apps_count', models.IntegerField(default=0, help_text='Number of apps in this store')),
                ('config', models.JSONField(blank=True, default=dict)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_appstore_configs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'App Store Credentials',
                'verbose_name_plural': 'App Store Credentials',
                'ordering': ['store'],
            },
        ),
    ]
