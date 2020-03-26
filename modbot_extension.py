#!/usr/bin/env python

"""
    Base module for all of the bot's modules
"""

import logging
import time


class ModbotExtension:
    """
    Describes the "interface" of a bot's module.

    All Bot modules must inherit from this class.

    It ensures methods mandatory for linking with the main class exist.
    Most of the methods will not perform anything.

    Attributes:
        settings            Configuration data for a module.
        state               Short-lived data common to all modules
        state_last_refresh  Last refresh of state (determines when to clean it)

    """
    global logging

    settings = {}
    state = {'channels': {}, 'users': {}}
    state_last_refresh = 0

    def __init__(self, slack_web_client, settings):
        """
        Stores a reference to the web client (for sending data) and settings

        This method should be executed by all inheriting classes.
        The data originates from the main Bot class

        :param BotWebClient slack_web_client: Slack web client for sending data
        :param dict settings: The settings to be applied by the module
        :return: None
        """
        self.webClient = slack_web_client
        self.settings = settings
        self.state_last_refresh = time.time()

    def on_message(self, event):
        """Does nothing. Triggered when receiving messages from Slack."""
        pass

    def on_message_deletion(self, event):
        """Does nothing. Triggered when messages are deleted."""
        pass

    def on_message_changed(self, event):
        """Does nothing. Triggered when messages are edited."""
        pass

    def log_info(self, msg, *args, **kwargs):
        """Log errors without re-import of logging in each module."""
        global logging
        logging.info(msg, *args, **kwargs)

    def get_user_info(self, user):
        """
        Gets user data, either from the cache or from Slack directly.

        Refer to https://api.slack.com/methods/users.info

        :param str user: The user ID of the user we're searching for
        :return: The data from the user, in Slack's format
        :rtype: dict

        """
        if (self.state_last_refresh + 60*10) < time.time():
            self.state = {'channels': {}, 'users': {}}
            self.log_info('Refreshing cache of users and channels')

        if user not in self.state['users']:
            user_data = self.webClient.users_info(user=user)['user']
            self.state['users'][user] = user_data

        return self.state['users'][user]

    def user_is_admin(self, user):
        """
        Returns True if the user is an admin, False otherwise

        :param str user: The user ID of the user we're searching for
        :return: True if the user is admin, False otherwise
        :rtype: Boolean

        """
        user_data = self.get_user_info(user)

        return user_data['is_admin']

    def user_is_owner(self, user):
        """
            Returns True if the user is an owner, False otherwise

            :param str user: The user ID of the user we're searching for
            :return: True if the user is owner, False otherwise
            :rtype: Boolean

        """
        user_data = self.get_user_info(user)

        return user_data['is_owner']
