"""
Generic Django Project Package
------------------------------

This file MUST remain minimal, deterministic, and completely side-effect free.

Purposes:
    • Marks this directory as a Python package.
    • Exposes stable, lightweight project metadata (__version__, __author__, __description__).
    • Guarantees import-safety for manage.py, ASGI, and WSGI boot processes.
    • Prevents ANY automatic code execution, framework initialization, or heavy imports.
    • Protects against accidental inclusion of non-Python content.

Rules:
    • DO NOT import Django or project modules here.
    • DO NOT perform I/O, logging, settings access, or dynamic logic.
    • DO NOT use try/except — this file must never hide initialization issues.
    • Content must always remain pure constants + metadata only.

This structure is hardened for enterprise deployments where stability,
repeatability, and deterministic imports are essential.
"""

__all__ = ["__version__", "__author__", "__description__"]

# ---------------------------------------------------------------------
# PROJECT METADATA (STATIC — SAFE — NO SIDE EFFECTS)
# ---------------------------------------------------------------------

# Semantic Version (bump per release/tag)
__version__ = "1.0.0"

# Generic, reusable project metadata
__author__ = "Application System"
__description__ = "Core initializer for the Django application package."