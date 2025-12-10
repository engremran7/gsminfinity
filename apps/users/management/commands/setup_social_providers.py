"""
Management command to set up test social authentication providers.
Usage: python manage.py setup_social_providers
"""

from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    help = "Set up test social authentication providers (Google, Facebook, Microsoft, GitHub)"

    def handle(self, *args, **options):
        site = Site.objects.get_current()
        
        providers = [
            {
                "provider": "google",
                "name": "Google OAuth",
                "client_id": "your-google-client-id.apps.googleusercontent.com",
                "secret": "your-google-client-secret",
            },
            {
                "provider": "facebook",
                "name": "Facebook Login",
                "client_id": "your-facebook-app-id",
                "secret": "your-facebook-app-secret",
            },
            {
                "provider": "microsoft",
                "name": "Microsoft OAuth",
                "client_id": "your-microsoft-client-id",
                "secret": "your-microsoft-client-secret",
            },
            {
                "provider": "github",
                "name": "GitHub OAuth",
                "client_id": "your-github-client-id",
                "secret": "your-github-client-secret",
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for provider_data in providers:
            social_app, created = SocialApp.objects.get_or_create(
                provider=provider_data["provider"],
                defaults={
                    "name": provider_data["name"],
                    "client_id": provider_data["client_id"],
                    "secret": provider_data["secret"],
                }
            )
            
            if created:
                social_app.sites.add(site)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Created {provider_data['name']} ({provider_data['provider']})"
                    )
                )
                created_count += 1
            else:
                # Update existing
                social_app.name = provider_data["name"]
                social_app.client_id = provider_data["client_id"]
                social_app.secret = provider_data["secret"]
                social_app.save()
                social_app.sites.add(site)
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ Updated existing {provider_data['name']} ({provider_data['provider']})"
                    )
                )
                updated_count += 1
        
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Setup complete! Created {created_count}, Updated {updated_count}"
            )
        )
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "⚠ IMPORTANT: These are placeholder credentials and won't work for actual OAuth."
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "  To enable real social login, configure actual OAuth credentials in Django Admin:"
            )
        )
        self.stdout.write("  http://127.0.0.1:8000/admin/socialaccount/socialapp/")
        self.stdout.write("")
        self.stdout.write("  Get OAuth credentials from:")
        self.stdout.write("  • Google: https://console.cloud.google.com/apis/credentials")
        self.stdout.write("  • Facebook: https://developers.facebook.com/apps/")
        self.stdout.write("  • Microsoft: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade")
        self.stdout.write("  • GitHub: https://github.com/settings/developers")
