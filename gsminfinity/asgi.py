### SIZE: 415 bytes
### HASH: 071A5276CC9338EECA059B17A06BEB38247089AAFF876E9371722470440DEE4A

"""
ASGI config for gsminfinity project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gsminfinity.settings")

application = get_asgi_application()