import hashlib
def get_device_fingerprint(request):
    ua=request.META.get("HTTP_USER_AGENT","")
    ip=request.META.get("HTTP_X_FORWARDED_FOR",request.META.get("REMOTE_ADDR",""))
    session_key=request.session.session_key or ""
    return hashlib.sha256(f"{ua}|{ip}|{session_key}".encode()).hexdigest()
