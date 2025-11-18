# apps/common/totp.py
import base64, hmac, hashlib, struct, time
from typing import Optional

def _int_to_bytes(i: int) -> bytes:
    return struct.pack(">Q", i)

def _normalize_secret(secret: str) -> bytes:
    s = secret.strip().replace(" ", "").upper()
    pad = (-len(s)) % 8
    if pad:
        s += "=" * pad
    return base64.b32decode(s)

def generate_totp(secret: str, for_time: Optional[int] = None,
                  digits: int = 6, digest: str = "sha1", period: int = 30) -> str:
    if for_time is None:
        for_time = int(time.time())
    counter = int(for_time // period)
    key = _normalize_secret(secret)
    msg = _int_to_bytes(counter)
    algo = getattr(hashlib, digest)
    hmac_digest = hmac.new(key, msg, algo).digest()
    offset = hmac_digest[-1] & 0x0F
    code = (struct.unpack(">I", hmac_digest[offset:offset+4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)

def verify_totp(secret: str, token: str, window: int = 1,
                digits: int = 6, digest: str = "sha1", period: int = 30) -> bool:
    try:
        int(token)
    except ValueError:
        return False
    token = str(token).zfill(digits)
    now = int(time.time())
    for offset in range(-window, window + 1):
        t = now + offset * period
        if hmac.compare_digest(generate_totp(secret, t, digits, digest, period), token):
            return True
    return False
