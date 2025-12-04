
from __future__ import annotations

from . import StubConnector


class RssConnector(StubConnector):
    channel = "rss"


class AtomConnector(StubConnector):
    channel = "atom"


class JsonFeedConnector(StubConnector):
    channel = "json"


class WebSubConnector(StubConnector):
    channel = "websub"


