
from __future__ import annotations

from . import ConnectorResult, StubConnector


class TwitterConnector(StubConnector):
    channel = "twitter"


class LinkedInConnector(StubConnector):
    channel = "linkedin"


class FacebookConnector(StubConnector):
    channel = "facebook"


class InstagramConnector(StubConnector):
    channel = "instagram"


class PinterestConnector(StubConnector):
    channel = "pinterest"


class RedditConnector(StubConnector):
    channel = "reddit"


class TikTokConnector(StubConnector):
    channel = "tiktok"


