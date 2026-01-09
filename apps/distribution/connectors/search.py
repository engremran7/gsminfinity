"""
Search Engine Indexing Connectors - Google Indexing API, Bing URL Submission
"""

from __future__ import annotations

import json
import logging

import requests

from apps.distribution.models import ShareJob, SocialAccount

from . import ConnectorResult

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 30


class GoogleIndexingConnector:
    """
    Google Indexing API connector.

    Required SocialAccount config:
    - config.service_account_json: Google Cloud service account JSON (as string or dict)

    Setup:
    1. Create a Google Cloud project
    2. Enable the Indexing API
    3. Create a service account with Indexing API access
    4. Verify site ownership in Google Search Console
    5. Add service account email as owner in Search Console
    """

    channel = "google_indexing"
    API_URL = "https://indexing.googleapis.com/v3/urlNotifications:publish"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def send(self, job: ShareJob) -> ConnectorResult:
        try:
            account = SocialAccount.objects.filter(
                channel=self.channel, is_active=True
            ).first()

            if not account:
                return ConnectorResult(
                    ok=False,
                    message="No active Google Indexing account configured",
                    response_code="NO_ACCOUNT",
                )

            # Get service account credentials
            service_account = account.config.get("service_account_json")
            if not service_account:
                return ConnectorResult(
                    ok=False,
                    message="No service_account_json in config",
                    response_code="NO_CREDENTIALS",
                )

            if isinstance(service_account, str):
                try:
                    service_account = json.loads(service_account)
                except json.JSONDecodeError:
                    return ConnectorResult(
                        ok=False,
                        message="Invalid service_account_json format",
                        response_code="INVALID_CREDENTIALS",
                    )

            # Get URL from job payload
            url = job.payload.get("url") if job.payload else None
            if not url:
                return ConnectorResult(
                    ok=False, message="No URL in job payload", response_code="NO_URL"
                )

            # Get access token using service account
            access_token = self._get_access_token(service_account)
            if not access_token:
                return ConnectorResult(
                    ok=False,
                    message="Failed to obtain access token",
                    response_code="AUTH_FAILED",
                )

            # Submit URL for indexing
            notification_type = job.payload.get("action", "URL_UPDATED")
            if notification_type not in ("URL_UPDATED", "URL_DELETED"):
                notification_type = "URL_UPDATED"

            response = requests.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": url,
                    "type": notification_type,
                },
                timeout=HTTP_TIMEOUT,
            )

            if response.status_code == 200:
                result = response.json()
                return ConnectorResult(
                    ok=True,
                    message=f"URL submitted for indexing: {notification_type}",
                    external_id=result.get("urlNotificationMetadata", {})
                    .get("latestUpdate", {})
                    .get("notifyTime", ""),
                    response_code="200",
                )
            else:
                error = (
                    response.json().get("error", {}).get("message", response.text[:200])
                )
                logger.warning(
                    f"Google Indexing API error: {response.status_code} - {error}"
                )
                return ConnectorResult(
                    ok=False,
                    message=f"Google API error: {error}",
                    response_code=str(response.status_code),
                )

        except requests.RequestException as e:
            logger.error(f"Google Indexing request failed: {e}")
            return ConnectorResult(
                ok=False,
                message=f"Network error: {str(e)[:200]}",
                response_code="NETWORK_ERROR",
            )
        except Exception as e:
            logger.exception(f"Google Indexing connector error: {e}")
            return ConnectorResult(
                ok=False,
                message=f"Connector error: {str(e)[:200]}",
                response_code="ERROR",
            )

    def _get_access_token(self, service_account: dict) -> str | None:
        """Get OAuth2 access token using service account JWT assertion."""
        try:
            import time

            import jwt

            now = int(time.time())
            payload = {
                "iss": service_account.get("client_email"),
                "scope": "https://www.googleapis.com/auth/indexing",
                "aud": self.TOKEN_URL,
                "iat": now,
                "exp": now + 3600,
            }

            private_key = service_account.get("private_key", "")
            assertion = jwt.encode(payload, private_key, algorithm="RS256")

            response = requests.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
                timeout=HTTP_TIMEOUT,
            )

            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                logger.error(f"Failed to get Google access token: {response.text}")
                return None

        except ImportError:
            logger.error("PyJWT not installed - required for Google Indexing API")
            return None
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None


class BingConnector:
    """
    Bing URL Submission API connector.

    Required SocialAccount config:
    - config.api_key: Bing Webmaster Tools API key
    - config.site_url: Your verified site URL (e.g., https://example.com)

    Setup:
    1. Sign up for Bing Webmaster Tools
    2. Verify your site ownership
    3. Get API key from Settings > API Access
    """

    channel = "bing_indexing"
    API_URL = "https://ssl.bing.com/webmaster/api.svc/json/SubmitUrl"

    def send(self, job: ShareJob) -> ConnectorResult:
        try:
            account = SocialAccount.objects.filter(
                channel=self.channel, is_active=True
            ).first()

            if not account:
                return ConnectorResult(
                    ok=False,
                    message="No active Bing Indexing account configured",
                    response_code="NO_ACCOUNT",
                )

            api_key = account.config.get("api_key", "")
            site_url = account.config.get("site_url", "")

            if not api_key or not site_url:
                return ConnectorResult(
                    ok=False,
                    message="Missing api_key or site_url in config",
                    response_code="NO_CREDENTIALS",
                )

            # Get URL from job payload
            url = job.payload.get("url") if job.payload else None
            if not url:
                return ConnectorResult(
                    ok=False, message="No URL in job payload", response_code="NO_URL"
                )

            # Ensure URL belongs to the verified site
            if not url.startswith(site_url.rstrip("/")):
                return ConnectorResult(
                    ok=False,
                    message=f"URL must belong to verified site: {site_url}",
                    response_code="INVALID_URL",
                )

            # Submit URL to Bing
            params = {
                "apikey": api_key,
                "siteUrl": site_url,
                "url": url,
            }

            response = requests.get(
                self.API_URL,
                params=params,
                timeout=HTTP_TIMEOUT,
            )

            if response.status_code == 200:
                # Bing returns empty response on success
                return ConnectorResult(
                    ok=True,
                    message="URL submitted to Bing for indexing",
                    response_code="200",
                )
            else:
                error = response.text[:200] if response.text else "Unknown error"
                logger.warning(f"Bing API error: {response.status_code} - {error}")
                return ConnectorResult(
                    ok=False,
                    message=f"Bing API error: {error}",
                    response_code=str(response.status_code),
                )

        except requests.RequestException as e:
            logger.error(f"Bing Indexing request failed: {e}")
            return ConnectorResult(
                ok=False,
                message=f"Network error: {str(e)[:200]}",
                response_code="NETWORK_ERROR",
            )
        except Exception as e:
            logger.exception(f"Bing Indexing connector error: {e}")
            return ConnectorResult(
                ok=False,
                message=f"Connector error: {str(e)[:200]}",
                response_code="ERROR",
            )
