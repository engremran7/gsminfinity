"""
Messaging Platform Connectors - Telegram, Discord, Slack, WhatsApp
"""
from __future__ import annotations

import logging
import requests
from urllib.parse import quote as url_quote

from . import ConnectorResult, Connector
from apps.distribution.models import ShareJob, SocialAccount

logger = logging.getLogger(__name__)

# Default timeout for HTTP requests (seconds)
HTTP_TIMEOUT = 30


class TelegramConnector:
    """
    Telegram Bot API connector.
    
    Required SocialAccount config:
    - access_token: Bot token from @BotFather
    - config.chat_id: Target chat/channel ID (e.g., @channel_name or -1001234567890)
    """
    channel = "telegram"

    def send(self, job: ShareJob) -> ConnectorResult:
        try:
            # Get social account with credentials
            account = SocialAccount.objects.filter(
                channel=self.channel, is_active=True
            ).first()
            
            if not account or not account.access_token:
                return ConnectorResult(
                    ok=False,
                    message="No active Telegram account configured",
                    response_code="NO_ACCOUNT"
                )
            
            bot_token = account.access_token
            chat_id = account.config.get("chat_id", "")
            
            if not chat_id:
                return ConnectorResult(
                    ok=False,
                    message="No chat_id configured in account",
                    response_code="NO_CHAT_ID"
                )
            
            # Build message from job payload
            payload = job.payload or {}
            title = payload.get("title", "")
            url = payload.get("url", "")
            summary = payload.get("summary", "")[:300]
            hashtags = payload.get("hashtags", [])
            
            # Format message with HTML
            message_parts = []
            if title:
                message_parts.append(f"<b>{self._escape_html(title)}</b>")
            if summary:
                message_parts.append(self._escape_html(summary))
            if url:
                message_parts.append(f"\n🔗 <a href=\"{url}\">Read more</a>")
            if hashtags:
                tags = " ".join(f"#{h.strip('#')}" for h in hashtags[:5])
                message_parts.append(f"\n{tags}")
            
            text = "\n\n".join(message_parts)
            
            # Send via Telegram Bot API
            api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(
                api_url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=HTTP_TIMEOUT,
            )
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get("result", {}).get("message_id", "")
                return ConnectorResult(
                    ok=True,
                    message="Message sent successfully",
                    external_id=str(message_id),
                    response_code="200"
                )
            else:
                error = response.json().get("description", response.text[:200])
                logger.warning(f"Telegram API error: {response.status_code} - {error}")
                return ConnectorResult(
                    ok=False,
                    message=f"Telegram API error: {error}",
                    response_code=str(response.status_code)
                )
                
        except requests.RequestException as e:
            logger.error(f"Telegram request failed: {e}")
            return ConnectorResult(
                ok=False,
                message=f"Network error: {str(e)[:200]}",
                response_code="NETWORK_ERROR"
            )
        except Exception as e:
            logger.exception(f"Telegram connector error: {e}")
            return ConnectorResult(
                ok=False,
                message=f"Connector error: {str(e)[:200]}",
                response_code="ERROR"
            )
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters for Telegram."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class DiscordConnector:
    """
    Discord Webhook connector.
    
    Required SocialAccount config:
    - config.webhook_url: Discord webhook URL
    """
    channel = "discord"

    def send(self, job: ShareJob) -> ConnectorResult:
        try:
            account = SocialAccount.objects.filter(
                channel=self.channel, is_active=True
            ).first()
            
            if not account:
                return ConnectorResult(
                    ok=False,
                    message="No active Discord account configured",
                    response_code="NO_ACCOUNT"
                )
            
            webhook_url = account.config.get("webhook_url", "")
            if not webhook_url:
                return ConnectorResult(
                    ok=False,
                    message="No webhook_url configured",
                    response_code="NO_WEBHOOK"
                )
            
            # Build embed from job payload
            payload = job.payload or {}
            title = payload.get("title", "New Post")
            url = payload.get("url", "")
            summary = payload.get("summary", "")[:400]
            image_url = payload.get("image_url", "")
            
            embed = {
                "title": title[:256],  # Discord title limit
                "description": summary,
                "color": 5814783,  # Nice blue color
            }
            
            if url:
                embed["url"] = url
            if image_url:
                embed["image"] = {"url": image_url}
            
            webhook_payload = {
                "embeds": [embed],
            }
            
            # Send via Discord webhook
            response = requests.post(
                webhook_url,
                json=webhook_payload,
                timeout=HTTP_TIMEOUT,
            )
            
            if response.status_code in (200, 204):
                return ConnectorResult(
                    ok=True,
                    message="Message sent to Discord",
                    response_code=str(response.status_code)
                )
            else:
                error = response.text[:200] if response.text else "Unknown error"
                logger.warning(f"Discord webhook error: {response.status_code} - {error}")
                return ConnectorResult(
                    ok=False,
                    message=f"Discord error: {error}",
                    response_code=str(response.status_code)
                )
                
        except requests.RequestException as e:
            logger.error(f"Discord request failed: {e}")
            return ConnectorResult(
                ok=False,
                message=f"Network error: {str(e)[:200]}",
                response_code="NETWORK_ERROR"
            )
        except Exception as e:
            logger.exception(f"Discord connector error: {e}")
            return ConnectorResult(
                ok=False,
                message=f"Connector error: {str(e)[:200]}",
                response_code="ERROR"
            )


class SlackConnector:
    """
    Slack Webhook connector.
    
    Required SocialAccount config:
    - config.webhook_url: Slack incoming webhook URL
    """
    channel = "slack"

    def send(self, job: ShareJob) -> ConnectorResult:
        try:
            account = SocialAccount.objects.filter(
                channel=self.channel, is_active=True
            ).first()
            
            if not account:
                return ConnectorResult(
                    ok=False,
                    message="No active Slack account configured",
                    response_code="NO_ACCOUNT"
                )
            
            webhook_url = account.config.get("webhook_url", "")
            if not webhook_url:
                return ConnectorResult(
                    ok=False,
                    message="No webhook_url configured",
                    response_code="NO_WEBHOOK"
                )
            
            # Build Slack blocks from job payload
            payload = job.payload or {}
            title = payload.get("title", "New Post")
            url = payload.get("url", "")
            summary = payload.get("summary", "")[:500]
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*<{url}|{title}>*" if url else f"*{title}*"
                    }
                }
            ]
            
            if summary:
                blocks.append({
                    "type": "section",
                    "text": {"type": "plain_text", "text": summary}
                })
            
            slack_payload = {
                "blocks": blocks,
                "unfurl_links": True,
            }
            
            response = requests.post(
                webhook_url,
                json=slack_payload,
                timeout=HTTP_TIMEOUT,
            )
            
            if response.status_code == 200 and response.text == "ok":
                return ConnectorResult(
                    ok=True,
                    message="Message sent to Slack",
                    response_code="200"
                )
            else:
                logger.warning(f"Slack webhook error: {response.status_code} - {response.text}")
                return ConnectorResult(
                    ok=False,
                    message=f"Slack error: {response.text[:200]}",
                    response_code=str(response.status_code)
                )
                
        except requests.RequestException as e:
            logger.error(f"Slack request failed: {e}")
            return ConnectorResult(
                ok=False,
                message=f"Network error: {str(e)[:200]}",
                response_code="NETWORK_ERROR"
            )
        except Exception as e:
            logger.exception(f"Slack connector error: {e}")
            return ConnectorResult(
                ok=False,
                message=f"Connector error: {str(e)[:200]}",
                response_code="ERROR"
            )


class WhatsAppConnector:
    """
    WhatsApp Business API connector (placeholder - requires Meta Business setup).
    
    Note: WhatsApp Business API requires:
    - Meta Business verification
    - WhatsApp Business Account
    - Approved message templates
    """
    channel = "whatsapp"

    def send(self, job: ShareJob) -> ConnectorResult:
        # WhatsApp Business API requires significant setup
        return ConnectorResult(
            ok=False,
            message="WhatsApp Business API requires Meta Business verification and approved templates. Configure via config.whatsapp_business_id and config.phone_number_id in SocialAccount.",
            response_code="NOT_CONFIGURED"
        )