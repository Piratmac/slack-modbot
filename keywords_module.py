#!/usr/bin/env python

"""
    With this module, the bot will reply when a given keyword is detected

    The behavior is similar to Slackbot, but replies are sent privately.

    Keywords are defined in a configuration file.
    Keywords can be updated by admins or owner of workspaces remotely.

    Reply to keywords will be done privately.
    Updates can only be performed in direct messages ('im')

    Usage:
        As admin, open a direct message with the bot
        Type 'keyword add X Y' to add a new keyword X with reply Y
        Type 'keyword delete X' to remove keyword X
        Type 'keyword list' to have the list of all keywords and the reply
"""


import os
import json

from base_bot_module import BaseBotModule


class KeywordsModule (BaseBotModule):
    """
    Replies to messages containing given keywords with specific replies

    Attributes:
        keywords            A dict object of the form keyword:reply.
        keywords_file_name  The name of the configuration file
    """

    keywords = {}
    keywords_file_name = 'keywords_module_config.json'
    replies = {
        'config_in_public': '\n'.join((
            'Hello!',
            'Please configure me here, not in public (I\'m a bit shy...)'
        )),
        'config_in_im': '\n'.join((
            'Hello!',
            'Welcome to the configuration page',
            '',
            '- Type *keyword list* for the list of keywords',
            '- Type *keyword add* _new_keyword message to display_ to add new keywords',
            '- Type *keyword delete* _existing_keyword_ to delete a keyword',
            '',
            '*Attention!* Actions are performed without confirmation',
        )),
        'keyword_add_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
            ''
        )),
        'keyword_delete_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'keyword_add_confirmation': '\n'.join((
            'Thanks! I\'ll reply to {keyword} now',
        )),
        'keyword_delete_confirmation': '\n'.join((
            'Thanks! I won\'t reply to {keyword} anymore',
        )),
        'keyword_list': '\n'.join((
            'Here is the list of configured keywords:',
            '',
            '{keywords}'
        )),
    }

    def __init__(self, slack_web_client, settings):
        """
        Loads keywords from config

        The superclass method ensured proper storage of various attributes

        :param BotWebClient slack_web_client: Slack web client
        :param dict settings: The settings to be applied by the module
        :return: None
        """
        super().__init__(slack_web_client, settings)
        self.load_keywords()
        self.log_info('[Keyword] Module started and ready to go')

    def load_keywords(self):
        """Loads keywords from config file. Does nothing if file unreadable."""
        try:
            data = open(self.keywords_file_name, "r")
            self.keywords = json.loads(data.read().strip())
            data.close()
        except IOError:
            logger.info('Keyword: Configuration file read error.')

    def save_keywords(self):
        """Saves keywords into the config file."""
        pointer = open(self.keywords_file_name, "w")
        json.dump(self.keywords, pointer, ensure_ascii=False)
        pointer.close()

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

        # Sanitizing the message, to better match keywords
        event_text_sanitized = event['text'].lower()

        accents_replacements = {
            'à': 'a', 'ä': 'a', 'â': 'a',
            'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e',
            'ï': 'i', 'ï': 'i',
            'ö': 'o', 'ô': 'o',
            'ù': 'u', 'ü': 'u', 'û': 'u',
        }

        for i, j in accents_replacements.items():
            event_text_sanitized = event_text_sanitized.replace(i, j)

        # Handle messages from admins first
        if 'keyword' in event_text_sanitized.split(' '):
            if event_text_sanitized.startswith('keyword list'):
                reply_data = self.keyword_list(event)
            elif event_text_sanitized.startswith('keyword add'):
                reply_data = self.keyword_add(event)
            elif event_text_sanitized.startswith('keyword delete'):
                reply_data = self.keyword_delete(event)
            else:
                reply_data = self.keyword(event)

        # We have a config message to send
        if reply_data and reply_data['ready_to_send']:
            reply_message.update(reply_data)
        else:
            reply_data = self.keyword_search_reply(event, event_text_sanitized)
            if reply_data and reply_data['ready_to_send']:
                reply_message.update(reply_data)

        # Let's send this message!
        if reply_message['ready_to_send']:
            self._send_reply_message(reply_message)
            return True

        # No keyword found
        else:
            return False

    def keyword(self, event):
        """
        Reacts to 'keyword' messages

        :param dict event: The event received
        :return: Message to be sent
        :rtype: dict
        """
        reply_data = {'type': 'regular'}

        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info('[Keyword] Config keyword by non-admin user %s',
                          event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)
        # If this already in private, reply with the configuration options
        elif event['channel_type'] == 'im':
            self.log_info('[Keyword] Config keyword in private by user %s',
                          event['user'])
            reply_data.update({
                'text': self.replies['config_in_im'],
                'type': 'regular',
                'ready_to_send': True,
            })
            return reply_data

    def keyword_list(self, event):
        """
        Reacts to 'keyword list' messages

        :param dict event: The event received
        :return: Message to be sent
        :rtype: False or dict
        """
        reply_data = {'type': 'regular'}

        # Exclude non-authorized people
        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info('[Keyword] Config keyword list by non-admin user %s',
                          event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        # Just make the list and send it
        self.log_info('[Keyword] List viewed by %s', event['user'])
        keywords_list = ['*' + keyword + '* : ' + message
                         for keyword, message in self.keywords.items()]
        keywords_list = '\n'.join(keywords_list)
        reply_text = self.replies['keyword_list'] \
            .replace('{keywords}', keywords_list)
        reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def keyword_add(self, event):
        """
        Reacts to 'keyword add' messages

        :param dict event: The event received
        :return: Message to be sent
        :rtype: False or dict
        """
        reply_data = {'type': 'regular'}

        # Exclude non-authorized people
        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info('[Keyword] Config keyword add by non-admin user %s',
                          event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        # Data is missing from the keyword
        if len(event['text'].split(' ')) < 4:
            self.log_info('[Keyword] Add keyword missing info by user %s',
                          event['user'])
            reply_text = self.replies['keyword_add_missing_param']
            reply_data.update({'text': reply_text})
        else:
            _, _, keyword, *message = event['text'].split(' ')
            keyword = keyword.lower()
            self.keywords[keyword] = ' '.join(message)
            self.save_keywords()
            self.log_info('[Keyword] New keyword %s by %s',
                          keyword,
                          event['user'])
            reply_text = self.replies['keyword_add_confirmation'] \
                .replace('{keyword}', keyword)
            reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def keyword_delete(self, event):
        """
        Reacts to 'keyword delete' messages

        :param dict event: The event received
        :return: False for unauthorized users,
                 a reply_data message otherwise
        :rtype: False or dict
        """
        reply_data = {'type': 'regular'}

        # Exclude non-authorized people
        if not self.user_is_admin(event['user']) \
                and not self.user_is_owner(event['user']):
            self.log_info('[Keyword] Config keyword add by non-admin user %s',
                          event['user'])
            return False

        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
            return self.switch_to_im(event)

        # Data is missing from the keyword
        if len(event['text'].split(' ')) < 3:
            self.log_info('[Keyword] Delete keyword missing info by user %s',
                          event['user'])
            reply_text = self.replies['keyword_delete_missing_param']
            reply_data.update({'text': reply_text})
        else:
            _, _, keyword, *_ = event['text'].split(' ')
            keyword = keyword.lower()
            if keyword in self.keywords:
                del self.keywords[keyword]
                self.save_keywords()
            self.log_info('[Keyword] Keyword %s deleted by %s',
                          keyword,
                          event['user'])
            reply_text = self.replies['keyword_delete_confirmation'] \
                .replace('{keyword}', keyword)
            reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def switch_to_im(self, event):
        """
        Replies through IM when receiving config keywords in public

        :param dict event: The event received
        :return: False for unauthorized users,
                 a reply_data message otherwise
        :rtype: False or dict
        """
        reply_data = {'type': 'regular'}

        # Open an IM (private) chat to get the channel ID
        try:
            open_IM_conversation = self.webClient.conversations_open({
                'users': [event['user']],
                'return_im': True
            })
        except SlackApiError as e:
            self.log_info('[Keyword] FAIL: User data query for %s - Abort IM',
                          event['user'])
            return False
        # If IM chat could be open, simply send a message
        else:
            reply_data.update({
                'channel': open_IM_conversation['channel']['id'],
                'text': self.replies['config_in_public'],
                'ready_to_send': True,
            })
            return reply_data

    def keyword_search_reply(self, event, event_text_sanitized):
        """
        Searches for keywords in received message.

        :param str event: The triggering event
        :param str event_text_sanitized: The message received with no accent
        :return: False if no keyword matched,
                 a message to send otherwise
        :rtype: False or dict
        """
        reply_data = {}

        matching_keywords = [x
                             for x in self.keywords
                             if x in event_text_sanitized.split(' ')]

        if not matching_keywords:
            return False

        self.log_info('[Keyword] Keyword %s sent by user %s',
                      matching_keywords[0],
                      event['user'])
        reply_data.update({
            'text': self.keywords[matching_keywords[0]],
            'ready_to_send': True
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
            self.webClient.chat_postMessage(reply_message)
        else:
            del reply_message['type']
            self.webClient.chat_postEphemeral(reply_message)
