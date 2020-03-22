import os
import logging
from bot_web_client import BotWebClient
from slackeventsapi import SlackEventAdapter
from base_bot_module import BaseBotModule
import importlib
import time




settings = {
  'main': {
    'username': os.environ.get("SLACK_BOT_USERNAME"),
    'icon_emoji': ":robot_face:",
    'user_id': '', # This will be determined upon startup
  },

  'active_bot_modules': {
    'KeywordsModule': {
      'module_name': 'keywords_module',
      'class_name':  'KeywordsModule',
    }
  }
}


slack_events_adapter = SlackEventAdapter(os.environ.get("SLACK_SIGNING_SECRET"), "/slack/events")


# Initialize a Web API client
slack_web_client = BotWebClient(token=os.environ.get('SLACK_BOT_TOKEN'))
slack_web_client.set_bot_settings(settings['main'])

bot_modules = []


# ============== Message Events ============= #
# When a user sends a DM, the event type will be 'message'.
# Here we'll link the message callback to the 'message' event.
@slack_events_adapter.on("message")
def message(payload):
  global start_time
  event = payload.get("event", {})

  # Ignores all old events
  if float(payload['event_time']) < start_time:
    logger.info('Event ignored - Happened before connection : %s compared to %f', payload['event_time'], start_time)
    return

  elif 'subtype' in event and event['subtype'] == 'message_deleted':
    for bot_module in bot_modules:
      bot_module.on_message_deletion(event)
    return

  elif 'subtype' in event and event['subtype'] == 'message_changed':
    for bot_module in bot_modules:
      bot_module.on_message_changed(event)
    return

  elif 'user' in event and event['user'] == settings['main']['user_id']:
    logger.info('Event ignored - Emitted by the bot')
    return

  logger.debug(payload)

  for bot_module in bot_modules:
    bot_module.on_message(event)


if __name__ == "__main__":
  logger = logging.getLogger()
  logger.setLevel(os.environ.get("DEBUG_LEVEL", logging.DEBUG))
  logger.addHandler(logging.StreamHandler())

  # Determine own identity
  settings['main']['user_id'] = slack_web_client.auth_test()['user_id']
  logger.info('Connected with user ID %s', settings['main']['user_id'])


  if 'active_bot_modules' in settings:
    for bot_module_name in settings['active_bot_modules']:
      module_name      = settings['active_bot_modules'][bot_module_name]['module_name']
      class_name       = settings['active_bot_modules'][bot_module_name]['class_name']
      module_settings  = settings['active_bot_modules'][bot_module_name]
      new_module = getattr(importlib.import_module(module_name), class_name)
      bot_modules.append(new_module(slack_web_client, module_settings))

  start_time = time.time()
  logger.info('Server started at %f', start_time)
  slack_events_adapter.start(port=os.environ.get("PORT", 80))