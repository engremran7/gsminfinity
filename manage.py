#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Default to development settings for local execution unless explicitly overridden.
    # Production deployments must set DJANGO_SETTINGS_MODULE explicitly (e.g., gsminfinity.settings).
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gsminfinity.settings_dev')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
