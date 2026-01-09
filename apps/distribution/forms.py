from __future__ import annotations

from django import forms

from apps.distribution.models import SocialAccount


class SocialAccountForm(forms.ModelForm):
    class Meta:
        model = SocialAccount
        fields = [
            "channel",
            "account_name",
            "access_token",
            "refresh_token",
            "token_expires_at",
            "config",
            "is_active",
        ]
        widgets = {
            "access_token": forms.PasswordInput(render_value=True),
            "refresh_token": forms.PasswordInput(render_value=True),
        }
