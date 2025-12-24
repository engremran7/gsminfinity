#!/usr/bin/env python3
"""
Repository Cleanup Script
Removes old files, duplicates, and unused code
"""
import os
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).parent.parent

# Files/patterns to remove
CLEANUP_PATTERNS = [
    # Old/backup files
    ('**/*_old.*', 'Old files'),
    ('**/*_backup.*', 'Backup files'),
    ('**/*.bak', 'Backup files'),
    ('**/*.tmp', 'Temporary files'),
    ('**/*.orig', 'Original files'),
    
    # Test files (keep in tests/ directory only)
    ('apps/**/test_*.py', 'Test files outside tests/'),
    ('apps/**/*_test.py', 'Test files outside tests/'),
    
    # Duplicate templates (keep only one version)
    ('templates/account/login_new.html', 'Duplicate login template'),
    ('templates/account/auth_base.html', 'Duplicate auth template'),
    ('templates/account/auth_form.html', 'Duplicate form template'),
    
    # Duplicate security folders
    ('security/', 'Duplicate security folder'),
    ('security_suite/', 'Duplicate security_suite folder'),
]

def cleanup():
    """Remove old and duplicate files"""
    print("=" * 70)
    print("REPOSITORY CLEANUP")
    print("=" * 70)
    
    removed_count = 0
    
    for pattern, description in CLEANUP_PATTERNS:
        matches = list(PROJECT_ROOT.glob(pattern))
        
        if matches:
            print(f"\n{description}:")
            for file_path in matches:
                # Skip if it's in .venv or node_modules
                if '.venv' in str(file_path) or 'node_modules' in str(file_path):
                    continue
                
                try:
                    if file_path.is_file():
                        print(f"  Removing: {file_path.relative_to(PROJECT_ROOT)}")
                        file_path.unlink()
                        removed_count += 1
                    elif file_path.is_dir():
                        print(f"  Removing: {file_path.relative_to(PROJECT_ROOT)}/")
                        shutil.rmtree(file_path)
                        removed_count += 1
                except Exception as e:
                    print(f"  ✗ Error removing {file_path}: {e}")
    
    print("\n" + "=" * 70)
    print(f"✓ Cleanup complete: {removed_count} items removed")
    print("=" * 70)

if __name__ == '__main__':
    response = input("This will remove old/duplicate files. Continue? (yes/no): ")
    if response.lower() == 'yes':
        cleanup()
    else:
        print("Cleanup cancelled")

