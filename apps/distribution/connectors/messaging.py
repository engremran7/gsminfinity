
from __future__ import annotations

from . import StubConnector


class TelegramConnector(StubConnector):
    channel = "telegram"


class DiscordConnector(StubConnector):
    channel = "discord"


class SlackConnector(StubConnector):
    channel = "slack"


class WhatsAppConnector(StubConnector):
    channel = "whatsapp"


