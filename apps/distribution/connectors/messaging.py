
from __future__ import annotations

from . import LoggingConnector


class TelegramConnector(LoggingConnector):
    channel = "telegram"


class DiscordConnector(LoggingConnector):
    channel = "discord"


class SlackConnector(LoggingConnector):
    channel = "slack"


class WhatsAppConnector(LoggingConnector):
    channel = "whatsapp"


