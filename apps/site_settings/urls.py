from django.urls import path
from . import views

app_name = "site_settings"

urlpatterns = [
    # 🌐 Public-facing views
    path("", views.site_settings_view, name="site_settings"),  # UI: settings detail page
    path("info/", views.settings_info, name="settings_info"),  # API: JSON snapshot
    path("verification/<str:filename>", views.verification_file, name="verification_file"),  # Serve uploaded verification files

    # 📜 Public policy pages
    path("privacy/", views.privacy_policy, name="privacy_policy"),
    path("terms/", views.terms_of_service, name="terms_of_service"),
    path("verify/", views.site_verification, name="site_verification"),
]