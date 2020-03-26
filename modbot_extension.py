#!/usr/bin/env python

"""
    Base class for all of the bot's extensions
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
        name                The name of the extension
        settings            Configuration data for a module.
        state               Short-lived data common to all modules
        state_last_refresh  Last refresh of state (determines when to clean it)

    """
    global logging

    name = ''
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


class ExtensionStore(object):
    """
    The extension store

    All modbot classes must register themselves via register_extension

    Attributes:
        extensions          All registered extensions

    """

    extensions = {}

    def register_extension(self, extension_class):
        """
        Registers an extension

        All extensions must call this method to get registered

        :param object extension_class: The extension's class
        """
        if extension_class.name not in self.extensions:
            self.extensions[extension_class.name] = {
                'class': extension_class,
                'loaded': False,
                'enabled': False,
            }
        logging.info(
            '[ExtStore] Extension ' + extension_class.name + ' registered'
        )

    def load_extension(self, name, slack_web_client, ext_settings):
        """
        Loads an extension

        This allows the extension to link with the web client

        :param object slack_web_client: The Modbot web client
        :param dict ext_settings: Extension settings as set in main program
        """
        if not self.extensions[name]['loaded']:
            self.extensions[name].update({
                'instance': self.extensions[name]['class'](
                    slack_web_client, ext_settings
                ),
                'loaded': True,
            })
        logging.info('[ExtStore] Extension ' + name + ' loaded')

    def enable_extension(self, name):
        """
        Enables an extension

        This allows the extension to receive data from Slack

        :param str name: The extension's name
        :return: True if extension was enabled, False otherwise
        :rtype: Boolean
        """
        if name not in self.extensions:
            logging.info(
                '[ExtStore] Extension ' + name + ' not registered'
            )
            return False
        else:
            self.extensions[name].update({
                'enabled': True,
            })
            logging.info(
                '[ExtStore] Extension ' + name + ' enabled'
            )
            return True

    def load_all(self, slack_web_client, ext_settings):
        """
        Loads all registered extensions

        :param object slack_web_client: The Modbot web client
        :param dict ext_settings: Extension settings as set in main program
        """
        for extension in self.extensions:
            self.load_extension(extension, slack_web_client, ext_settings)

    def enable_all(self):
        """
        Enables all loaded extensions

        This allows the extension to receive data from Slack

        :param str name: The extension's name
        :return: True if extension was enabled, False otherwise
        :rtype: Boolean
        """
        for name in self.extensions:
            if self.is_enabled(name):
                self.enable_extension(name)

    def is_enabled(self, name):
        """
        Indicates whether an extension is loaded or not

        :param str name: The extension's name
        :return: True if extension is enabled, False otherwise
        :rtype: Boolean
        """
        if name in self.extensions and self.extensions[name]['enabled']:
            return True
        return False

extension_store = ExtensionStore()
modbot_extension.extension_store.register_extension(Keywords)



