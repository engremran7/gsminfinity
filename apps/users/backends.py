"""
apps.users.backends
-------------------
Import shim for backward and settings compatibility.
Delegates to apps.users.auth_backends.MultiFieldAuthBackend.
"""

from __future__ import annotations
from importlib import import_module
import sys

module = import_module("apps.users.auth_backends")

# expose all public names (safe passthrough)
globals().update(module.__dict__)

# ensure dotted-path import consistency
sys.modules[__name__] = module
