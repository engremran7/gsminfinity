from __future__ import annotations

from . import LoggingConnector


class TwitterConnector(LoggingConnector):
    channel = "twitter"


class LinkedInConnector(LoggingConnector):
    channel = "linkedin"


class FacebookConnector(LoggingConnector):
    channel = "facebook"


class InstagramConnector(LoggingConnector):
    channel = "instagram"


class PinterestConnector(LoggingConnector):
    channel = "pinterest"


class RedditConnector(LoggingConnector):
    channel = "reddit"


class TikTokConnector(LoggingConnector):
    channel = "tiktok"
