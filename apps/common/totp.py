"""
Legacy TOTP helpers.

For new code, prefer apps.users.mfa.TOTPService. These functions
remain as thin wrappers for backward compatibility.
"""

from __future__ import annotations

from typing import Optional

from apps.users.mfa import TOTPService


def generate_totp(
    secret: str,
    for_time: Optional[int] = None,
    digits: int = 6,
    digest: str = "sha1",
    period: int = 30,
) -> str:
    return TOTPService.generate_current_code(
        secret=secret,
        period=period,
        digits=digits,
        at_time=for_time,
    )


def verify_totp(
    secret: str,
    token: str,
    window: int = 1,
    digits: int = 6,
    digest: str = "sha1",
    period: int = 30,
) -> bool:
    return TOTPService.verify(
        secret=secret,
        code=token,
        tolerance=window,
        period=period,
        digits=digits,
    )
