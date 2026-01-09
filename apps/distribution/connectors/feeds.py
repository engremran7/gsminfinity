from __future__ import annotations

from . import LoggingConnector


class RssConnector(LoggingConnector):
    channel = "rss"


class AtomConnector(LoggingConnector):
    channel = "atom"


class JsonFeedConnector(LoggingConnector):
    channel = "json"


class WebSubConnector(LoggingConnector):
    channel = "websub"
