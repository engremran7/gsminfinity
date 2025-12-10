# Social Authentication Setup Guide

This guide explains how to configure OAuth providers (Google, Facebook, Microsoft, GitHub) for social login/signup on your GSMInfinity site.

## Quick Start

Test providers have been pre-configured with placeholder credentials. To enable **real social authentication**, you need to:

1. Get OAuth credentials from each provider's developer console
2. Update the credentials in Django Admin
3. Configure redirect URIs in provider consoles

---

## 🔐 Getting OAuth Credentials

### 1. Google OAuth Setup

**Developer Console:** https://console.cloud.google.com/apis/credentials

**Steps:**
1. Create a new project or select existing project
2. Go to **APIs & Services > Credentials**
3. Click **Create Credentials > OAuth 2.0 Client ID**
4. Application type: **Web application**
5. Authorized redirect URIs:
   ```
   http://127.0.0.1:8000/accounts/google/login/callback/
   https://yourdomain.com/accounts/google/login/callback/
   ```
6. Copy **Client ID** and **Client Secret**

**Django Admin Update:**
- Navigate to: `Admin > Social applications > Google OAuth`
- Paste **Client ID** into `Client id` field
- Paste **Client Secret** into `Secret key` field
- Save

---

### 2. Facebook Login Setup

**Developer Console:** https://developers.facebook.com/apps/

**Steps:**
1. Create a new app or select existing app
2. Go to **Settings > Basic**
3. Copy **App ID** and **App Secret**
4. Add Facebook Login product
5. Go to **Facebook Login > Settings**
6. Valid OAuth Redirect URIs:
   ```
   http://127.0.0.1:8000/accounts/facebook/login/callback/
   https://yourdomain.com/accounts/facebook/login/callback/
   ```

**Django Admin Update:**
- Navigate to: `Admin > Social applications > Facebook Login`
- Paste **App ID** into `Client id` field
- Paste **App Secret** into `Secret key` field
- Save

---

### 3. Microsoft OAuth Setup

**Developer Console:** https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade

**Steps:**
1. Go to **Azure Portal > Azure Active Directory > App registrations**
2. Click **New registration**
3. Name: Your app name
4. Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
5. Redirect URI: **Web**
   ```
   http://127.0.0.1:8000/accounts/microsoft/login/callback/
   https://yourdomain.com/accounts/microsoft/login/callback/
   ```
6. Copy **Application (client) ID**
7. Go to **Certificates & secrets > New client secret**
8. Copy the **secret value** (not the ID)

**Django Admin Update:**
- Navigate to: `Admin > Social applications > Microsoft OAuth`
- Paste **Application (client) ID** into `Client id` field
- Paste **Secret value** into `Secret key` field
- Save

---

### 4. GitHub OAuth Setup

**Developer Console:** https://github.com/settings/developers

**Steps:**
1. Go to **Settings > Developer settings > OAuth Apps**
2. Click **New OAuth App**
3. Application name: Your app name
4. Homepage URL: `http://127.0.0.1:8000` or `https://yourdomain.com`
5. Authorization callback URL:
   ```
   http://127.0.0.1:8000/accounts/github/login/callback/
   https://yourdomain.com/accounts/github/login/callback/
   ```
6. Copy **Client ID**
7. Click **Generate a new client secret**
8. Copy **Client Secret**

**Django Admin Update:**
- Navigate to: `Admin > Social applications > GitHub OAuth`
- Paste **Client ID** into `Client id` field
- Paste **Client Secret** into `Secret key` field
- Save

---

## 🧪 Testing

After configuring credentials:

1. **Visit signup page**: http://127.0.0.1:8000/accounts/signup/
2. You should see buttons for each configured provider
3. Click a provider button to test OAuth flow
4. Complete authentication with provider
5. You'll be redirected to profile completion page
6. Complete your profile (4-step wizard)
7. Access the site dashboard

---

## 🔧 Django Admin Configuration

**Access:** http://127.0.0.1:8000/admin/socialaccount/socialapp/

Each Social Application needs:
- ✅ **Provider**: Select from dropdown (google, facebook, microsoft, github)
- ✅ **Name**: Friendly name (displayed in admin only)
- ✅ **Client id**: From provider developer console
- ✅ **Secret key**: From provider developer console  
- ✅ **Sites**: Must select at least one site (usually "example.com")
- ⚠️ **Key**: Leave empty (only used by some providers like Twitter)

---

## 🚨 Common Issues

### Buttons Not Showing
- **Check**: Social applications created in admin?
- **Check**: Applications linked to a site?
- **Fix**: Run `python manage.py setup_social_providers`

### OAuth Error: redirect_uri_mismatch
- **Cause**: Redirect URI mismatch between Django and provider console
- **Fix**: Ensure exact match including trailing slash
- **Format**: `{SCHEME}://{DOMAIN}/accounts/{provider}/login/callback/`

### OAuth Error: invalid_client
- **Cause**: Incorrect Client ID or Secret
- **Fix**: Double-check credentials in both admin and provider console

### User Stuck at Profile Page
- **Cause**: Profile completion middleware enforcing onboarding
- **Fix**: Complete all 4 steps of profile wizard

---

## 🔒 Security Notes

- ✅ **Never commit** OAuth secrets to version control
- ✅ **Use environment variables** for production secrets
- ✅ **Rotate secrets** regularly
- ✅ **Use HTTPS** in production (required by most providers)
- ✅ **Configure proper scopes** (email, profile) in provider console

---

## 📝 Provider-Specific Settings

You can add provider-specific configuration in the **Settings** JSON field:

### Google Example:
```json
{
  "scope": ["email", "profile"],
  "access_type": "online"
}
```

### Facebook Example:
```json
{
  "auth_params": {
    "auth_type": "reauthenticate"
  }
}
```

---

## 🆘 Support

- **Django Allauth Docs**: https://django-allauth.readthedocs.io/
- **Provider List**: https://django-allauth.readthedocs.io/en/latest/providers.html
- **GitHub Issues**: Report issues specific to GSMInfinity setup

---

## ✅ Checklist

Before going live:

- [ ] All OAuth credentials configured with real values (not placeholders)
- [ ] Redirect URIs updated to production domain
- [ ] HTTPS enabled on production
- [ ] Social applications linked to correct site in admin
- [ ] Test each provider's login/signup flow
- [ ] Profile completion wizard tested
- [ ] Error handling tested (cancelled OAuth, denied permissions)
- [ ] Secrets stored in environment variables (not hardcoded)
