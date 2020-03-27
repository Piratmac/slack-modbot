#!/usr/bin/env python

"""
    Modified slack.WebClient class for simplified calls
"""


from slack import WebClient
from slack.errors import SlackApiError


class ModbotWebclient (WebClient):
    """
    Allows sending data to Slack through various means

    Overriden methods are meant to simplify the use by bot modules.
    Most methods will add the settings to modules' data.

    Attributes:
        settings    Configuration used by the bot to send data
    """
    settings = {
        'username': 'keyword_bot',
        'icon_emoji': ":robot_face:",
        'user_id': '',
        }

    def set_client_settings(self, settings):
        """
        Stores settings provided by the main file

        :param dict settings: The settings to be applied by the module
        :return: None

        """
        self.settings.update(settings)

    def chat_postMessage(self, input_data):
        """
        Sends a regular message

        :param dict input_data: The message to be sent
        """
        payload = self.settings.copy()
        payload.update(input_data)

        return super().chat_postMessage(**payload)

    def conversations_open(self, input_data):
        """
        Opens a new IM

        :param dict input_data: The message to be sent
        """
        payload = self.settings.copy()
        payload.update(input_data)

        return super().conversations_open(**payload)

    def chat_postEphemeral(self, input_data):
        """
        Sends an ephemeral message

        Ephemeral messages are temporary and visible only by the recipient.
        This is useful for posting on public channels.

        :param dict input_data: The message to be sent
        """
        payload = self.settings.copy()
        payload.update(input_data)

        return super().chat_postEphemeral(**payload)
