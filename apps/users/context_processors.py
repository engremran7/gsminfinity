# Keep users-specific processors minimal; site settings are injected via site_settings app.
def user_context(request):
    return {"is_authenticated":request.user.is_authenticated}
