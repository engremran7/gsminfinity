"""
Cleanup Old Data Command
Removes old sessions, logs, temporary files, and expired data
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Cleanup old data (sessions, logs, temp files, expired records)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Delete data older than N days (default: 90)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(days=days)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be deleted")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleaning up data older than {days} days ({cutoff.date()})..."
            )
        )

        total_deleted = 0

        # 1. Cleanup expired sessions
        total_deleted += self.cleanup_sessions(dry_run)

        # 2. Cleanup old download sessions
        total_deleted += self.cleanup_download_sessions(cutoff, dry_run)

        # 3. Cleanup old page views (if analytics app exists)
        total_deleted += self.cleanup_page_views(cutoff, dry_run)

        # 4. Cleanup old events
        total_deleted += self.cleanup_events(cutoff, dry_run)

        # 5. Cleanup old ad events
        total_deleted += self.cleanup_ad_events(cutoff, dry_run)

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Total records deleted: {total_deleted:,}")
        )

    def cleanup_sessions(self, dry_run=False):
        """Cleanup expired Django sessions"""
        try:
            from django.contrib.sessions.models import Session

            expired = Session.objects.filter(expire_date__lt=timezone.now())
            count = expired.count()

            if count > 0:
                if not dry_run:
                    expired.delete()
                self.stdout.write(
                    f"  Sessions: {count:,} expired sessions {'would be' if dry_run else ''} deleted"
                )
                return count
            else:
                self.stdout.write("  Sessions: No expired sessions found")
                return 0

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Sessions: Error - {e}"))
            return 0

    def cleanup_download_sessions(self, cutoff, dry_run=False):
        """Cleanup old completed download sessions"""
        try:
            from apps.storage.models import UserDownloadSession

            old_sessions = UserDownloadSession.objects.filter(
                status="completed", created_at__lt=cutoff
            )
            count = old_sessions.count()

            if count > 0:
                if not dry_run:
                    old_sessions.delete()
                self.stdout.write(
                    f"  Download Sessions: {count:,} old sessions {'would be' if dry_run else ''} deleted"
                )
                return count
            else:
                self.stdout.write("  Download Sessions: No old sessions found")
                return 0

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Download Sessions: {e}"))
            return 0

    def cleanup_page_views(self, cutoff, dry_run=False):
        """Cleanup old page view records"""
        try:
            from apps.analytics.models import PageView

            old_views = PageView.objects.filter(created_at__lt=cutoff)
            count = old_views.count()

            if count > 0:
                if not dry_run:
                    old_views.delete()
                self.stdout.write(
                    f"  Page Views: {count:,} old records {'would be' if dry_run else ''} deleted"
                )
                return count
            else:
                self.stdout.write("  Page Views: No old records found")
                return 0

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Page Views: {e}"))
            return 0

    def cleanup_events(self, cutoff, dry_run=False):
        """Cleanup old event records"""
        try:
            from apps.analytics.models import Event

            old_events = Event.objects.filter(created_at__lt=cutoff)
            count = old_events.count()

            if count > 0:
                if not dry_run:
                    old_events.delete()
                self.stdout.write(
                    f"  Events: {count:,} old records {'would be' if dry_run else ''} deleted"
                )
                return count
            else:
                self.stdout.write("  Events: No old records found")
                return 0

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Events: {e}"))
            return 0

    def cleanup_ad_events(self, cutoff, dry_run=False):
        """Cleanup old ad event records"""
        try:
            from apps.ads.models import AdEvent

            old_events = AdEvent.objects.filter(created_at__lt=cutoff)
            count = old_events.count()

            if count > 0:
                if not dry_run:
                    old_events.delete()
                self.stdout.write(
                    f"  Ad Events: {count:,} old records {'would be' if dry_run else ''} deleted"
                )
                return count
            else:
                self.stdout.write("  Ad Events: No old records found")
                return 0

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ad Events: {e}"))
            return 0
