from __future__ import annotations

from . import LoggingConnector


class MailchimpConnector(LoggingConnector):
    channel = "mailchimp"


class SendGridConnector(LoggingConnector):
    channel = "sendgrid"


class SubstackConnector(LoggingConnector):
    channel = "substack"
