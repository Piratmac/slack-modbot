#!/usr/bin/env python

"""
    Base class for all of the bot's extensions
"""

import logging
import time

logger = logging.getLogger(__name__)


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
        web_client          The client used to send messages

    """

    name = ''
    settings = {}
    state = {'channels': {}, 'users': {}}
    state_last_refresh = 0
    web_client = {}

    def __init__(self, web_client, settings):
        """
        Stores a reference to the web client (for sending data) and settings

        This method should be executed by all inheriting classes.
        The data originates from the main Bot class

        :param ModbotWebclient web_client: Slack web client for sending data
        :param dict settings: The settings to be applied by the module
        :return: None
        """
        self.web_client = web_client
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

    def help(self, event):
        """Does nothing. Triggered when help is requested."""
        pass

    def log_info(self, msg, *args, **kwargs):
        """Log errors while replacing the user ID with its name."""
        if 'user' in kwargs:
            user_data = self.get_user_info(kwargs['user'])
            if user_data:
                msg = msg.replace(
                    '%user',
                    user_data['profile']['real_name_normalized']
                    + ' <' + kwargs['user'] + '>'
                )
            del kwargs['user']

        logger.info(msg, *args, **kwargs)

    def get_user_info(self, user):
        """
        Gets user data, either from the cache or from Slack directly.

        Refer to https://api.slack.com/methods/users.info

        :param str user: The user ID of the user we're searching for
        :return: The data about the user, in Slack's format
        :rtype: dict

        """
        if (self.state_last_refresh + 60*10) < time.time():
            self.state = {'channels': {}, 'users': {}}
            self.log_info('[BotExtension] Refreshing cache')

        if user not in self.state['users']:
            user_data = self.web_client.users_info(user=user)
            if user_data['ok']:
                self.state['users'][user] = user_data['user']
                return self.state['users'][user]
            else:
                logger.warning('[BotExtension] Couldn\'t find user %s', user)
                return False
        else:
            return self.state['users'][user]

        return False

    def get_channel_info(self, channel):
        """
        Gets data on a given channel.

        Refer to https://api.slack.com/methods/conversations.list

        :param str channel: The channel ID or label to find
        :return: The data about the channel, in Slack's format
        :rtype: dict

        """
        if (self.state_last_refresh + 60*10) < time.time() \
                or not self.state['channels']:
            self.state = {'channels': {}, 'users': {}}
            self.log_info('[BotExtension] Refreshing cache')
            self.state['channels'] = \
                self.web_client.conversations_list()['channels']

        # Parse the channel name
        # Received either as #channel or <#channel_id|channel_name>
        if '<' in channel:
            channel = channel.split('|')[0][2:]
        elif channel[0] == '#':
            channel = channel[1:]

        # Check if the channel is there (either ID or name)
        channel_found = [chan
                         for chan in self.state['channels']
                         if chan['name'] == channel
                         or chan['id'] == channel
                         ]

        if channel_found:
            return channel_found[0]
        return False

    def user_is_admin(self, user):
        """
        Returns True if the user is an admin, False otherwise

        :param str user: The user ID of the user we're searching for
        :return: True if the user is admin, False otherwise
        :rtype: Boolean

        """
        user_data = self.get_user_info(user)

        if user_data:
            return user_data['is_admin']
        else:
            return False

    def user_is_owner(self, user):
        """
            Returns True if the user is an owner, False otherwise

            :param str user: The user ID of the user we're searching for
            :return: True if the user is owner, False otherwise
            :rtype: Boolean

        """
        user_data = self.get_user_info(user)

        if user_data:
            return user_data['is_owner']
        else:
            return False


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
            self.extensions[extension_class.name.lower()] = {
                'class': extension_class,
                'loaded': False,
                'enabled': False,
                'enabled_for_im': True,
                'enabled_for_channels': set(),
            }
        logging.info(
            '[ExtStore] Extension ' + extension_class.name + ' registered'
        )

    def load_extension(self, name, slack_web_client, ext_settings={}):
        """
        Loads an extension

        This allows the extension to link with the web client

        :param object slack_web_client: The Modbot web client
        :param dict ext_settings: Extension settings as set in main program
        """
        if not self.is_registered(name):
            logging.info('[ExtStore] Extension ' + name + ' unknown')
            return False
        if not self.is_loaded(name):
            self.extensions[name.lower()].update({
                'instance': self.extensions[name.lower()]['class'](
                    slack_web_client, ext_settings
                ),
                'loaded': True,
            })
        logging.info('[ExtStore] Extension ' + name + ' loaded')
        return True

    def enable_extension(self, name):
        """
        Enables an extension

        This allows the extension to receive data from Slack

        :param str name: The extension's name
        :return: True if extension was enabled, False otherwise
        :rtype: Boolean
        """
        if not self.is_registered(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not registered'
            )
            return False
        elif not self.is_loaded(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not loaded'
            )
            return False
        else:
            self.extensions[name.lower()].update({
                'enabled': True,
            })
            logging.info(
                '[ExtStore] Extension ' + name + ' enabled'
            )
            return True

    def enable_extension_for(self, name, channel):
        """
        Enables an extension for a given channel

        This allows the extension to receive data from Slack for this channel

        :param str name: The extension's name
        :return: True if extension was enabled, False otherwise
        :rtype: Boolean
        """
        if not self.is_registered(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not registered'
            )
            return False
        elif not self.is_loaded(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not loaded'
            )
            return False
        else:
            self.extensions[name.lower()]['enabled_for_channels'].add(channel)
            logging.info(
                '[ExtStore] Extension ' + name + ' enabled for ' + channel
            )
            return True

    def enable_extension_for_im(self, name):
        """
        Enables an extension for IM messages

        This allows the extension to receive data from Slack for IM messages

        :param str name: The extension's name
        :return: True if extension was enabled, False otherwise
        :rtype: Boolean
        """
        if not self.is_registered(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not registered'
            )
            return False
        elif not self.is_loaded(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not loaded'
            )
            return False
        else:
            self.extensions[name.lower()]['enabled_for_im'] = True
            logging.info(
                '[ExtStore] Extension ' + name + ' enabled for IMs'
            )
            return True

    def disable_extension(self, name):
        """
        Disables an extension

        This prevents the extension to receive data from Slack

        :param str name: The extension's name
        :return: True if extension was disabled, False otherwise
        :rtype: Boolean
        """
        if not self.is_registered(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not registered'
            )
            return False
        elif not self.is_enabled(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not enabled'
            )
            return False
        else:
            self.extensions[name.lower()].update({
                'enabled': False,
            })
            logging.info(
                '[ExtStore] Extension ' + name + ' disabled'
            )
            return True

    def disable_extension_for(self, name, channel):
        """
        Disables an extension for a given channel

        This prevents the extension to receive data from Slack on some channels

        :param str name: The extension's name
        :return: True if extension was disabled, False otherwise
        :rtype: Boolean
        """
        if not self.is_registered(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not registered'
            )
            return False
        elif not self.is_enabled(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not enabled'
            )
            return False
        else:
            self.extensions[name.lower()]['enabled_for_channels'].remove(channel)
            logging.info(
                '[ExtStore] Extension ' + name + ' disabled for ' + channel
            )
            return True

    def disable_extension_for_im(self, name):
        """
        Disables an extension for a given channel

        This prevents the extension to receive data from Slack for IMs

        :param str name: The extension's name
        :return: True if extension was disabled, False otherwise
        :rtype: Boolean
        """
        if not self.is_registered(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not registered'
            )
            return False
        elif not self.is_enabled(name):
            logging.info(
                '[ExtStore] Extension ' + name + ' not enabled'
            )
            return False
        else:
            self.extensions[name.lower()]['enabled_for_im'] = False
            logging.info(
                '[ExtStore] Extension ' + name + ' disabled for IMs'
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
            if self.is_loaded(name):
                self.enable_extension(name)

    def disable_all(self):
        """
        Disables all loaded extensions

        This prevents all extensions to receive data from Slack

        :param str name: The extension's name
        :return: True if extension was enabled, False otherwise
        :rtype: Boolean
        """
        for name in self.extensions:
            if self.is_enabled(name):
                self.disable_extension(name)

    def is_registered(self, name):
        """
        Indicates whether an extension is registered or not

        :param str name: The extension's name
        :return: True if extension is registered, False otherwise
        :rtype: Boolean
        """
        return (name.lower() in self.extensions)

    def is_loaded(self, name):
        """
        Indicates whether an extension is loaded or not

        :param str name: The extension's name
        :return: True if extension is enabled, False otherwise
        :rtype: Boolean
        """
        if self.is_registered(name) \
                and self.extensions[name.lower()]['loaded']:
            return True
        return False

    def is_enabled(self, name):
        """
        Indicates whether an extension is enabled or not

        :param str name: The extension's name
        :return: True if extension is enabled, False otherwise
        :rtype: Boolean
        """
        if self.is_registered(name) \
                and self.extensions[name.lower()]['enabled']:
            return True
        return False

    def is_enabled_for(self, name, event):
        """
        Indicates whether an extension is enabled in a given context

        :param str name: The extension's name
        :param dict event: The received event
        :return: True if extension is enabled for this event, False otherwise
        :rtype: Boolean
        """
        ext = self.extensions[name.lower()]
        if self.is_registered(name) and ext['enabled']:
            if event['channel_type'] == 'im':
                return ext['enabled_for_im']
            else:
                return event['channel'] in ext['enabled_for_channels']
        return False

    def is_enabled_in_im(self, name):
        """
        Indicates whether an extension is enabled in IM (direct messages)

        :param str name: The extension's name
        :param dict event: The received event
        :return: True if extension is enabled in IM, False otherwise
        :rtype: Boolean
        """
        ext = self.extensions[name.lower()]
        if self.is_registered(name) and ext['enabled']:
            return ext['enabled_for_im']
        return False

    def list_enabled_for(self, name):
        """
        Indicates on which channels an extension is enabled

        :param str name: The extension's name
        :return: A set of channels where the extension is enabled
        :rtype: set
        """
        ext = self.extensions[name.lower()]
        if self.is_registered(name) and ext['enabled']:
            return ext['enabled_for_channels']
        return False


class ExtensionManager(ModbotExtension):
    """
    Manages extensions

    Attributes:
        name                The name of the extension
        web_client          The client used to send messages

    """
    name = 'ExtensionManager'
    web_client = {}

    name = 'ExtensionManager'
    replies = {
        'config_in_public': '\n'.join((
            'Hello!',
            'Please configure me here, not in public (I\'m a bit shy...)'
        )),
        'extension_help': '\n'.join((
            'Hello!',
            'Type *help* for help.',
            'Type *help* _extension_ for help on a specific extension.',
            '',
            'For the extension manager (admins only!):',
            '- Type *extension list* for the list of extensions',
            '- Type *extension load* _extension_ to load an extension',
            '- Type *extension enable* _extension_ to enable an extension',
            '- Type *extension disable* _extension_ to enable an extension',
            'List of extensions: {extensions}',
        )),
        'extension_help_no_extension_found': '\n'.join((
            'There is no extension with that name. Try *help* for the list',
        )),
        'extension_list': '\n'.join((
            'Hello!',
            'Here are all identified extensions:',
            '{extensions}',
        )),
        'extension_enabled': '\n'.join((
            'Enabled globally',
        )),
        'extension_enabled_for': '\n'.join((
            'enabled on channels',
        )),
        'extension_enabled_in_im': '\n'.join((
            'enabled in direct messages',
        )),
        'extension_disabled': '\n'.join((
            'Disabled globally',
        )),
        'extension_load_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'extension_load_success': '\n'.join((
            'Success: Extension {extension} loaded successfully',
        )),
        'extension_load_failure': '\n'.join((
            'Fail: Extension {extension} could not be loaded',
        )),
        'extension_enable_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'extension_enable_success': '\n'.join((
            'Success: Extension {extension} enabled successfully',
        )),
        'extension_enable_failure': '\n'.join((
            'Fail: Extension {extension} could not be enabled',
        )),
        'extension_enable_for_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'extension_enable_for_success': '\n'.join((
            'Success: Extension {extension} enabled successfully on channel {channel}',
        )),
        'extension_enable_for_failure': '\n'.join((
            'Fail: Extension {extension} could not be enabled',
        )),
        'extension_enable_for_im_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'extension_enable_for_im_success': '\n'.join((
            'Success: Extension {extension} enabled successfully for IMs',
        )),
        'extension_enable_for_im_failure': '\n'.join((
            'Fail: Extension {extension} could not be enabled',
        )),
        'extension_disable_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'extension_disable_success': '\n'.join((
            'Success: Extension {extension} disabled successfully',
        )),
        'extension_disable_failure': '\n'.join((
            'Fail: Extension {extension} could not be disabled',
        )),
        'extension_disable_for_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'extension_disable_for_success': '\n'.join((
            'Success: Extension {extension} disabled successfully on channel {channel}',
        )),
        'extension_disable_for_failure': '\n'.join((
            'Fail: Extension {extension} could not be disabled',
        )),
        'extension_disable_for_im_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'extension_disable_for_im_success': '\n'.join((
            'Success: Extension {extension} disabled successfully for IMs',
        )),
        'extension_disable_for_im_failure': '\n'.join((
            'Fail: Extension {extension} could not be disabled',
        )),
    }

    def __init__(self, slack_web_client, settings):
        """
        Doesn't do much, except calling the superclass' method

        :param ModbotWebclient slack_web_client: Slack web client
        :param dict settings: The settings to be applied by the module
        :return: None
        """
        super().__init__(slack_web_client, settings)
        self.log_info('[ExtManager] Module started and ready to go')

    def on_message(self, event):
        """
        Processes received events and sends a reply

        :param dict event: The event received
        :return: True if a message was sent, False otherwise
        :rtype: Boolean
        """
        reply_message = {
            'channel': event['channel'],
            'user': event['user'],
            'ready_to_send': False,
            'type': 'ephemeral',
        }
        reply_data = False

        # Handle received messages
        if event['text'] in ['help', 'extension help', 'help extension']:
            reply_data = self.help(event)
        elif event['text'].startswith('help '):
            reply_data = self.help_other_extension(event)
        elif event['text'].startswith('extension'):
            if event['text'].startswith('extension list'):
                reply_data = self.extension_list(event)
            elif event['text'].startswith('extension load '):
                reply_data = self.extension_add(event)
            elif event['text'].startswith('extension enable '):
                reply_data = self.extension_enable(event)
            elif event['text'].startswith('extension enable_for '):
                reply_data = self.extension_enable_for(event)
            elif event['text'].startswith('extension enable_for_im '):
                reply_data = self.extension_enable_for_im(event)
            elif event['text'].startswith('extension disable '):
                reply_data = self.extension_disable(event)
            elif event['text'].startswith('extension disable_for '):
                reply_data = self.extension_disable_for(event)
            elif event['text'].startswith('extension disable_for_im '):
                reply_data = self.extension_disable_for_im(event)

        # We have a config message to send
        if reply_data and reply_data['ready_to_send']:
            reply_message.update(reply_data)
            if reply_message['ready_to_send']:
                self._send_reply_message(reply_message)
                return True

        # No reply found
        else:
            return False

    def help(self, event):
        """
        Reacts to 'help' messages

        :param dict event: The event received
        :return: Message to be sent, False otherwise
        :rtype: False or dict
        """
        global extension_store
        reply_data = {'type': 'regular'}

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        self.log_info('[ExtManager] Help viewed by %user', user=event['user'])

        extensions_list = ', '.join(extension_store.extensions)

        reply_text = self.replies['extension_help'] \
            .replace('{extensions}', extensions_list)
        reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def help_other_extension(self, event):
        """
        Reacts to 'help extension' messages

        :param dict event: The event received
        :return: Message to be sent, False otherwise
        :rtype: False or dict
        """
        global extension_store
        reply_data = {'type': 'regular'}

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        self.log_info('[ExtManager] Help viewed by %user', user=event['user'])

        _, extension, *_ = event['text'].split(' ')
        if extension in extension_store.extensions:
            reply_data = extension_store \
                         .extensions[extension]['instance'] \
                         .help(event)
        else:
            reply_text = self.replies['extension_help_no_extension_found']
            reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def extension_list(self, event):
        """
        Reacts to 'extension list' messages

        :param dict event: The event received
        :return: Message to be sent, False otherwise
        :rtype: False or dict
        """
        global extension_store
        reply_data = {'type': 'regular'}

        # Exclude non-authorized people
        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info(
                '[ExtManager] Config: "list" by non-admin user %user',
                user=event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        # Just make the list and send it
        self.log_info('[ExtManager] List viewed by %user', user=event['user'])
        ext_list = []
        for extension in extension_store.extensions:
            ext_message = '*' + extension + '* : '
            if extension_store.is_enabled(extension):
                ext_message += self.replies['extension_enabled']
                if extension_store.is_enabled_in_im(extension):
                    ext_message += ', ' \
                                   + self.replies['extension_enabled_in_im']
                list_channels = extension_store.list_enabled_for(extension)
                if list_channels:
                    ext_message += ', ' + self.replies['extension_enabled_for']
                    ext_message += ' <#' + '> <#'.join(list_channels) + '>'
            else:
                ext_message += self.replies['extension_disabled']
            ext_list.append(ext_message)

        ext_list = '\n'.join(ext_list)

        reply_text = self.replies['extension_list'] \
            .replace('{extensions}', ext_list)
        reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def extension_load(self, event):
        """
        Reacts to 'extension load' messages

        :param dict event: The event received
        :return: Message to be sent, False otherwise
        :rtype: False or dict
        """
        global extension_store
        reply_data = {'type': 'regular'}

        # Exclude non-authorized people
        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info(
                '[ExtManager] Config: "load" by non-admin %user',
                user=event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        # Missing argument
        if len(event['text'].split(' ')) < 3:
            self.log_info(
                '[ExtManager] Config: Load missing info by user %user',
                user=event['user']
            )
            reply_text = self.replies['extension_load_missing_param']
            reply_data.update({'text': reply_text})
        else:
            ext_name = event['text'].split(' ')[2].lower()
            load_status = extension_store.load_extension(
                ext_name,
                self.web_client,
                self.settings['extensions'][ext_name]
            )
            if load_status:
                self.log_info(
                    '[ExtManager] Extension %s loaded by %user',
                    ext_name,
                    user=event['user']
                )
                reply_text = self.replies['extension_load_success'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})
            else:
                reply_text = self.replies['extension_load_failure'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def extension_enable(self, event):
        """
        Reacts to 'extension enable' messages

        :param dict event: The event received
        :return: Message to be sent, False otherwise
        :rtype: False or dict
        """
        global extension_store
        reply_data = {'type': 'regular'}

        # Exclude non-authorized people
        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info(
                '[ExtManager] Config: "enable" by non-admin user %user',
                user=event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        # Missing argument
        if len(event['text'].split(' ')) < 3:
            self.log_info(
                '[ExtManager] Config: Enable missing info by user %user',
                user=event['user'])
            reply_text = self.replies['extension_enable_missing_param']
            reply_data.update({'text': reply_text})
        else:
            ext_name = event['text'].split(' ')[2].lower()
            enable_status = extension_store.enable_extension(ext_name)
            if enable_status:
                self.log_info(
                    '[ExtManager] Extension %s enabled by %user',
                    ext_name,
                    user=event['user']
                )
                reply_text = self.replies['extension_enable_success'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})
            else:
                reply_text = self.replies['extension_enable_failure'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def extension_enable_for(self, event):
        """
        Reacts to 'extension enable_for' messages

        :param dict event: The event received
        :return: Message to be sent, False otherwise
        :rtype: False or dict
        """
        global extension_store
        reply_data = {'type': 'regular'}

        # Exclude non-authorized people
        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info(
                '[ExtManager] Config: "enable_for" by non-admin user %user',
                user=event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        # Missing argument
        if len(event['text'].split(' ')) < 4:
            self.log_info(
                '[ExtManager] Config: Enable_for missing info by user %user',
                user=event['user'])
            reply_text = self.replies['extension_enable_for_missing_param']
            reply_data.update({'text': reply_text})
        else:
            _, _, ext_name, channel, *_ = event['text'].split(' ')
            ext_name = ext_name.lower()
            channel = self.get_channel_info(channel)

            enable_status = extension_store. \
                enable_extension_for(ext_name, channel['id'])
            if enable_status and channel:
                self.log_info(
                    '[ExtManager] Extension %s enabled by %user on '
                    + channel['name'],
                    ext_name,
                    user=event['user'],
                )
                reply_text = self.replies['extension_enable_for_success'] \
                    .replace('{extension}', ext_name) \
                    .replace('{channel}', '<#' + channel['id'] + '>')
                reply_data.update({'text': reply_text})
            else:
                reply_text = self.replies['extension_enable_for_failure'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def extension_enable_for_im(self, event):
        """
        Reacts to 'extension enable_for_im' messages

        :param dict event: The event received
        :return: Message to be sent, False otherwise
        :rtype: False or dict
        """
        global extension_store
        reply_data = {'type': 'regular'}

        # Exclude non-authorized people
        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info(
                '[ExtManager] Config: "enable_for_im" by non-admin user %user',
                user=event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        # Missing argument
        if len(event['text'].split(' ')) < 3:
            self.log_info(
                '[ExtManager] Config: Enable_for_im missing info by user %user',
                user=event['user'])
            reply_text = self.replies['extension_enable_for_im_missing_param']
            reply_data.update({'text': reply_text})
        else:
            _, _, ext_name, *_ = event['text'].split(' ')
            ext_name = ext_name.lower()

            enable_status = extension_store.enable_extension_for_im(ext_name)
            if enable_status:
                self.log_info(
                    '[ExtManager] Extension %s enabled by %user for IMs',
                    ext_name,
                    user=event['user'],
                )
                reply_text = self.replies['extension_enable_for_im_success'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})
            else:
                reply_text = self.replies['extension_enable_for_im_failure'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def extension_disable(self, event):
        """
        Reacts to 'extension disable' messages

        :param dict event: The event received
        :return: Message to be sent, False otherwise
        :rtype: False or dict
        """
        global extension_store
        reply_data = {'type': 'regular'}

        # Exclude non-authorized people
        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info(
                '[ExtManager] Config: "disable" by non-admin %user',
                user=event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        # Missing argument
        if len(event['text'].split(' ')) < 3:
            self.log_info(
                '[ExtManager] Config: Disable missing info by %user',
                user=event['user'])
            reply_text = self.replies['extension_disable_missing_param']
            reply_data.update({'text': reply_text})
        else:
            ext_name = event['text'].split(' ')[2].lower()
            disable_status = extension_store.disable_extension(ext_name)
            if disable_status:
                self.log_info(
                    '[ExtManager] Extension %s disabled by %user',
                    ext_name,
                    user=event['user']
                )
                reply_text = self.replies['extension_disable_success'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})
            else:
                reply_text = self.replies['extension_disable_failure'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def extension_disable_for(self, event):
        """
        Reacts to 'extension disable_for' messages

        :param dict event: The event received
        :return: Message to be sent, False otherwise
        :rtype: False or dict
        """
        global extension_store
        reply_data = {'type': 'regular'}

        # Exclude non-authorized people
        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info(
                '[ExtManager] Config: "disable_for" by non-admin user %user',
                user=event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        # Missing argument
        if len(event['text'].split(' ')) < 4:
            self.log_info(
                '[ExtManager] Config: disable_for missing info by user %user',
                user=event['user'])
            reply_text = self.replies['extension_disable_for_missing_param']
            reply_data.update({'text': reply_text})
        else:
            _, _, ext_name, channel, *_ = event['text'].split(' ')
            ext_name = ext_name.lower()
            channel = self.get_channel_info(channel)

            disable_status = extension_store. \
                disable_extension_for(ext_name, channel['id'])
            if disable_status and channel:
                self.log_info(
                    '[ExtManager] Extension %s disabled by %user on '
                    + channel['name'],
                    ext_name,
                    user=event['user'],
                )
                reply_text = self.replies['extension_disable_for_success'] \
                    .replace('{extension}', ext_name) \
                    .replace('{channel}', '<#' + channel['id'] + '>')
                reply_data.update({'text': reply_text})
            else:
                reply_text = self.replies['extension_disable_for_failure'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def extension_disable_for_im(self, event):
        """
        Reacts to 'extension disable_for_im' messages

        :param dict event: The event received
        :return: Message to be sent, False otherwise
        :rtype: False or dict
        """
        global extension_store
        reply_data = {'type': 'regular'}

        # Exclude non-authorized people
        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info(
                '[ExtManager] Config: "disable_for_im" by non-admin user %user',
                user=event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        # Missing argument
        if len(event['text'].split(' ')) < 3:
            self.log_info(
                '[ExtManager] Config: disable_for_im missing info by user %user',
                user=event['user'])
            reply_text = self.replies['extension_disable_for_im_missing_param']
            reply_data.update({'text': reply_text})
        else:
            _, _, ext_name, *_ = event['text'].split(' ')
            ext_name = ext_name.lower()

            disable_status = extension_store.disable_extension_for_im(ext_name)
            if disable_status:
                self.log_info(
                    '[ExtManager] Extension %s disabled for IMs by %user',
                    ext_name,
                    user=event['user'],
                )
                reply_text = self.replies['extension_disable_for_im_success'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})
            else:
                reply_text = self.replies['extension_disable_for_im_failure'] \
                    .replace('{extension}', ext_name)
                reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def switch_to_im(self, event):
        """
        Replies through IM when receiving config requests in public

        :param dict event: The event received
        :return: False for unauthorized users,
                 a reply_data message otherwise
        :rtype: False or dict
        """
        reply_data = {'type': 'regular'}

        # Open an IM (private) chat to get the channel ID
        try:
            open_IM_conversation = self.web_client.conversations_open({
                'users': [event['user']],
                'return_im': True
            })
        except SlackApiError as e:
            self.log_info(
                '[ExtManager] FAIL: User data query for %user - Abort IM',
                user=event['user'])
            return False
        # If IM chat could be open, simply send a message
        else:
            reply_data.update({
                'channel': open_IM_conversation['channel']['id'],
                'text': self.replies['config_in_public'],
                'ready_to_send': True,
            })
            return reply_data

    def _send_reply_message(self, reply_message):
        """
        Sends the reply in the proper type (regular or ephemeral)

        :param str reply_message: The message to be sent
        :return: None
        """
        del reply_message['ready_to_send']
        if reply_message['type'] == 'regular':
            del reply_message['type']
            self.web_client.chat_postMessage(reply_message)
        else:
            del reply_message['type']
            self.web_client.chat_postEphemeral(reply_message)


extension_store = ExtensionStore()
