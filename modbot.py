#!/usr/bin/env python

"""
    This is a Slack bot.

    The bot's extensions provide functionalities.
    This file is only meant to fire up the links with Slack servers.
"""

__author__ = "Piratmac"
__copyright__ = "Copyright 2020"
__license__ = "GPL"
__version__ = "0.1"
__maintainer__ = "Piratmac"
__email__ = "piratmac@gmail.com"
__status__ = "Development"


import os
import logging
import importlib
import time

from slackeventsapi import SlackEventAdapter

from modbot_extension import extension_store, ExtensionManager
from webclient import ModbotWebclient

# Checks important variables
if os.environ.get("SLACK_SIGNING_SECRET") is None \
        or os.environ.get('SLACK_BOT_TOKEN') is None:
    raise ValueError('Missing signing secret or bot token')

# Configuration. Will not be modified by the bot.
settings = {
    'webclient': {
        'username': os.environ.get("SLACK_BOT_USERNAME", 'modbot'),
    },

    'api_endpoint': '/slack/events',
    'signing_secret': os.environ.get("SLACK_SIGNING_SECRET"),
    'bot_token': os.environ.get("SLACK_BOT_TOKEN"),
    'host': os.environ.get("HOST", '127.0.0.1'),
    'port': os.environ.get("PORT", 80),

    'extensions': {
        'Keywords': {
            'module_name': 'modbot_keywords',
            'config_file': os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'modbot_extensions',
                'modbot_keywords.json'),
        },
    }
}

# Short-lived data that can be modified by the bot
state = {
    'start_time': 0,
    'user_id': '',
}

# List of active / loaded extensions (stores instances of the extensions)
loaded_extensions = []

# Adapter meant to send data to Slack
slack_events_adapter = None

# Server receiving events from Slack
slack_web_client = None

# Configure the logger
logger = logging.getLogger()
logger.setLevel(os.environ.get("DEBUG_LEVEL", logging.DEBUG))
logger.addHandler(logging.StreamHandler())

# Prepare the reception of data from Slack
slack_events_adapter = SlackEventAdapter(
    settings['signing_secret'],
    settings['api_endpoint'])

# Starts the client which sends data to Slack
slack_web_client = ModbotWebclient(token=settings['bot_token'])
slack_web_client.set_client_settings(settings['webclient'])

# Determine the user ID of the bot (to prevent self-replies)
bot_user_data = slack_web_client.auth_test()
state['user_id'] = bot_user_data['user_id']
logger.info('[Bot] Connected with user ID %s', state['user_id'])

# Reception of messages from the adapter
@slack_events_adapter.on("message")
def message(payload):
    """
    Receives a message from a given user and routes it.

    The payload is a JSON variable.
    Refer to https://api.slack.com/reference/messaging/payload

    This function will separate message reception, deletion and modification.
    It then sends the event to the corresponding extension method.

    :param dict payload: Data received from Slack
    :return: True if messages were processed, False otherwise
    """
    global state, logger, extension_store
    event = payload.get("event", {})

    # Ignores all old events
    if float(payload['event_time']) < state['start_time']:
        logger.info('[Bot] Event happened before startup, ignoring')
        return False

    elif 'subtype' in event and event['subtype'] == 'message_deleted':
        for ext in extension_store.extensions:
            if extension_store.is_enabled(ext):
                extension_store \
                    .extensions[ext]['instance'] \
                    .on_message_deletion(event)
        return True

    elif 'subtype' in event and event['subtype'] == 'message_changed':
        for ext in extension_store.extensions:
            if extension_store.is_enabled(ext):
                extension_store \
                    .extensions[ext]['instance'] \
                    .on_message_changed(event)
        return True

    elif 'user' in event and event['user'] == state['user_id']:
        logger.info('[Bot] Event triggered by the bot, ignoring')
        return False

    logger.debug(payload)

    for ext in extension_store.extensions:
        if extension_store.is_enabled(ext):
            extension_store \
                .extensions[ext]['instance'] \
                .on_message(event)
    return False


# Load and enable extensions, as well as the extension manager
extension_store.register_extension(ExtensionManager)
extension_store.load_extension(
    'ExtensionManager',
    slack_web_client,
    )
extension_store.enable_extension('ExtensionManager')
for ext_name, ext_settings in settings['extensions'].items():
    __import__(
        'modbot_extensions.' + ext_settings['module_name'],
        globals(),
        locals(),
        [ext_name])
    extension_store.load_extension(ext_name, slack_web_client, ext_settings)
    extension_store.enable_extension(ext_name)

# Start the reception of data
state['start_time'] = time.time()
logger.info('[Bot] Server started at %f', state['start_time'])
slack_events_adapter.start(settings['host'], settings['port'])
