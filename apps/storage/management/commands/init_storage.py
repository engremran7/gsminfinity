# Management command to setup initial shared drives and service accounts
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.storage.models import SharedDriveAccount, ServiceAccount
import os


class Command(BaseCommand):
    help = 'Initialize shared drives and service accounts configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--drives',
            type=int,
            default=3,
            help='Number of shared drives to create (default: 3)'
        )
        parser.add_argument(
            '--accounts-per-drive',
            type=int,
            default=100,
            help='Number of service accounts per drive (default: 100)'
        )
    
    def handle(self, *args, **options):
        num_drives = options['drives']
        accounts_per_drive = options['accounts_per_drive']
        
        self.stdout.write(
            f'Creating {num_drives} shared drives with {accounts_per_drive} service accounts each...'
        )
        
        for drive_num in range(1, num_drives + 1):
            # Create shared drive
            drive, created = SharedDriveAccount.objects.get_or_create(
                name=f'SharedDrive_{drive_num}',
                defaults={
                    'drive_id': f'DRIVE_ID_{drive_num}_PLACEHOLDER',
                    'owner_email': f'drive{drive_num}@example.com',
                    'max_files': 400000,
                    'priority': 100 - drive_num,  # Higher priority for first drives
                    'notes': f'Shared drive {drive_num} - Replace DRIVE_ID and credentials'
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created {drive.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ {drive.name} already exists')
                )
            
            # Create service accounts
            created_accounts = 0
            for sa_num in range(1, accounts_per_drive + 1):
                sa_name = f'SA_{drive_num}_{sa_num:03d}'
                sa_email = f'sa-{drive_num}-{sa_num:03d}@project.iam.gserviceaccount.com'
                
                sa, created = ServiceAccount.objects.get_or_create(
                    shared_drive=drive,
                    email=sa_email,
                    defaults={
                        'name': sa_name,
                        'credentials_path': f'/path/to/credentials/{sa_name}.json',
                        'quota_reset_at': timezone.now().replace(
                            hour=0, minute=0, second=0, microsecond=0
                        ) + timezone.timedelta(days=1)
                    }
                )
                
                if created:
                    created_accounts += 1
            
            if created_accounts > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Created {created_accounts} service accounts for {drive.name}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Setup complete! Created {num_drives} drives with '
                f'{num_drives * accounts_per_drive} total service accounts.'
            )
        )
        
        self.stdout.write(
            self.style.WARNING(
                '\n⚠️  IMPORTANT: Update the following in Django admin:'
            )
        )
        self.stdout.write('   1. Replace DRIVE_ID placeholders with actual Google Drive IDs')
        self.stdout.write('   2. Update service account emails with real addresses')
        self.stdout.write('   3. Update credentials_path to point to actual JSON key files')
        self.stdout.write('   4. Update owner_email addresses')
