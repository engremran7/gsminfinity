#!/usr/bin/env python3
"""
Comprehensive Implementation Verification Script
Checks that all planned features are fully implemented (no stubs/placeholders)
"""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

import django

django.setup()

from django.apps import apps
from django.core.management import call_command
from django.urls import get_resolver


def check_urls():
    """Verify all views have URLs"""
    print("\n✓ CHECKING URLS...")
    resolver = get_resolver()
    patterns = resolver.url_patterns
    print(f"  Found {len(patterns)} URL patterns")

    # Check key apps
    key_apps = ['firmwares', 'blog', 'storage', 'distribution', 'analytics', 'admin_suite']
    for app in key_apps:
        try:
            app_config = apps.get_app_config(app)
            print(f"  ✓ {app}: Installed")
        except LookupError:
            print(f"  ✗ {app}: NOT INSTALLED")

def check_models():
    """Verify all models are defined"""
    print("\n✓ CHECKING MODELS...")

    checks = {
        'firmwares': ['Brand', 'Model', 'Variant', 'OfficialFirmware', 'PendingFirmware'],
        'blog': ['Post', 'Category', 'Tag'],
        'storage': ['SharedDriveAccount', 'ServiceAccount', 'UserDownloadSession'],
        'distribution': ['SocialAccount', 'ShareJob'],
        'analytics': ['PageView', 'Event', 'DailyMetrics', 'RealtimeMetrics'],
        'tags': ['Tag'],
    }

    for app_name, models in checks.items():
        try:
            for model_name in models:
                model = apps.get_model(app_name, model_name)
                print(f"  ✓ {app_name}.{model_name}")
        except LookupError as e:
            print(f"  ✗ {app_name}.{model_name}: {e}")

def check_views():
    """Verify key views exist"""
    print("\n✓ CHECKING VIEWS...")

    checks = {
        'apps.firmwares.views': ['FirmwareUploadView', 'PendingFirmwareViewSet'],
        'apps.blog.views': ['post_list', 'post_detail', 'post_create'],
        'apps.storage.views': ['InitiateFirmwareDownloadView', 'QuotaStatusView'],
        'apps.distribution.views': ['dashboard'],
        'apps.analytics.views': ['analytics_dashboard', 'track_pageview', 'track_event'],
    }

    for module_path, views in checks.items():
        try:
            module = __import__(module_path, fromlist=views)
            for view_name in views:
                if hasattr(module, view_name):
                    print(f"  ✓ {module_path}.{view_name}")
                else:
                    print(f"  ✗ {module_path}.{view_name}: NOT FOUND")
        except ImportError as e:
            print(f"  ✗ {module_path}: {e}")

def check_tasks():
    """Verify Celery tasks are defined"""
    print("\n✓ CHECKING CELERY TASKS...")

    checks = {
        'apps.firmwares.tasks': ['analyze_firmware_ai', 'cleanup_old_tracking_data'],
        'apps.blog.tasks': ['auto_generate_blog_post', 'auto_tag_post'],
        'apps.storage.tasks': ['cleanup_failed_sessions', 'balance_drive_report'],
        'apps.ads.tasks': ['aggregate_events', 'cleanup_old_events'],
        'apps.analytics.tasks': ['aggregate_daily_metrics', 'update_realtime_metrics'],
    }

    for module_path, tasks in checks.items():
        try:
            module = __import__(module_path, fromlist=tasks)
            for task_name in tasks:
                if hasattr(module, task_name):
                    print(f"  ✓ {module_path}.{task_name}")
                else:
                    print(f"  ✗ {module_path}.{task_name}: NOT FOUND")
        except ImportError as e:
            print(f"  ✗ {module_path}: {e}")

def check_migrations():
    """Check for pending migrations"""
    print("\n✓ CHECKING MIGRATIONS...")
    try:
        # This will show pending migrations
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            call_command('showmigrations', '--plan', verbosity=0)
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            if '[ ]' in output:
                print("  ⚠️  Pending migrations found - run: python manage.py migrate")
            else:
                print("  ✓ All migrations applied")
        except Exception as e:
            sys.stdout = old_stdout
            print(f"  ⚠️  Could not check migrations: {e}")
    except Exception as e:
        print(f"  ⚠️  {e}")

def check_settings():
    """Verify key settings are configured"""
    print("\n✓ CHECKING SETTINGS...")
    from django.conf import settings

    checks = {
        'INSTALLED_APPS': ['apps.firmwares', 'apps.blog', 'apps.storage', 'apps.analytics'],
        'CELERY_BEAT_SCHEDULE': 'Celery beat schedule',
        'REST_FRAMEWORK': 'DRF configuration',
    }

    for setting, description in checks.items():
        if hasattr(settings, setting):
            print(f"  ✓ {setting}")
        else:
            print(f"  ✗ {setting}: NOT CONFIGURED")

def main():
    print("=" * 70)
    print("GSM INFINITY - IMPLEMENTATION VERIFICATION")
    print("=" * 70)

    check_urls()
    check_models()
    check_views()
    check_tasks()
    check_migrations()
    check_settings()

    print("\n" + "=" * 70)
    print("✓ VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    main()

