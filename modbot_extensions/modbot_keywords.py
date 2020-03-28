#!/usr/bin/env python

"""
    With this extension, the bot will reply when a given keyword is detected

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
import re

import modbot_extension


class Keywords(modbot_extension.ModbotExtension):
    """
    Replies to messages containing given keywords with specific replies

    Attributes:
        name                The name of the extension
        keywords            A dict object of the form keyword:reply_data.
        config_file         The name of the configuration file
        config_data         For configuration that can be modified by the bot
        config_file         The name of the configuration file
        replies             Replies to various queries
        keyword_template    The template to reply to quickadd keywords
    """

    name = 'Keywords'
    keywords = {}
    config_file = 'modbot_keywords_.json'
    config_data = {
        'reply_in_thread': True,
        'reply_in_ephemeral': False,
        'reply_to_keywords_by_admins': True,
    }
    keyword_template_text = '\n'.join((
        'Bonjour et bienvenue sur le Slack des volontaires!',
        'Les missions sont proposées sur des canaux par compétences.',
        'D\'après ton message, tu peux rejoindre {channels}',
        '--',
        'Par ailleurs, inutile de se présenter (il y a beaucoup de monde ici, si tout le monde le fait on va se perdre), pourrais-tu supprimer ton message? (via les 3 points à droite de ton message quand tu le survoles)',
        'Il y a également plusieurs règles de fonctionnement sur #général et un tutoriel sur #tutoriel_slack.',
        '--',
        '_Note: je suis un bot (bleep blop!)._ Je suis un peu bête, je peux me tromper. Si je vous embête, contactez un modérateur.',
    ))
    replies = {
        'config_in_public': '\n'.join((
            'Hello!',
            'Please configure me here, not in public (I\'m a bit shy...)'
        )),
        'config_in_im': '\n'.join((
            'Hello!',
            'Welcome to the keywords config page!',
            '',
            '- Type *keyword list* for the list of keywords',
            '- Type *keyword add* _new_keyword message to display_ to add new keywords',
            '- Type *keyword quickadd* _new_keyword_ #channel1 #channel2 to add new keywords by using the template',
            '- Type *keyword delete* _existing_keyword_ to delete a keyword',
            '- Type *keyword config* to change my behavior',
            '',
            '*Attention!* Actions are performed without confirmation',
        )),
        'keyword_add_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'keyword_add_confirmation': '\n'.join((
            'Thanks! I\'ll reply to {keyword} now',
        )),

        'keyword_template_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'keyword_template_missing_channel': '\n'.join((
            'I didn\'t see the {channels} part in your template',
        )),
        'keyword_template_confirmation': '\n'.join((
            'Thanks! I\'ll use this new template now',
        )),

        'keyword_quickadd_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'keyword_quickadd_missing_channel': '\n'.join((
            'I didn\'t see a link to a channel in your request',
        )),
        'keyword_quickadd_confirmation': '\n'.join((
            'Thanks! I\'ll reply to {keyword} now',
        )),

        'keyword_delete_missing_param': '\n'.join((
            'I didn\'t understand your request, could you retry?',
        )),
        'keyword_delete_inexistant': '\n'.join((
            'This keyword doesn\t exist',
        )),
        'keyword_delete_confirmation': '\n'.join((
            'Thanks! I won\'t reply to {keyword} anymore',
        )),

        'keyword_config_list': '\n'.join((
            'Hello!',
            'Welcome to the configuration page to change my behavior',
            '',
            'Type *keyword config* _key_ _value_ to change a value',
            '',
            'List of configuration keys:',
            '{config_keys}',
            '',
            '_Note:_ Enabling both _reply_in_thread_ and _reply_in_ephemeral_ mean users will receive 2 messages',
            '',
            '*Attention!* Actions are performed without confirmation',
        )),
        'keyword_config_types': {
            'boolean': 'Expected value: True or False.',
            'str': 'Expected value: Free text. Can be formatted with markdown',
        },
        'keyword_config_descriptions': {
            'reply_in_thread': 'The bot will reply publicly inside a thread.',
            'reply_in_ephemeral': 'The bot will reply privately.',
            'reply_to_keywords_by_admins': 'The bot will reply to admins if they say keywords.',
        },
        'keyword_config_current_value': '\n'.join((
            ' - Current value:',
        )),
        'keyword_config_confirmation': '\n'.join((
            'Thanks! Configuration modified.',
        )),
        'keyword_config_failure': '\n'.join((
            'This settings can\'t be modified in this way. Sorry!',
        )),
        'keyword_config_unknown_key': '\n'.join((
            'I don\'t know that parameter...',
        )),

        'keyword_list': '\n'.join((
            'Here is the list of configured keywords',
            '*Keywords without templates*',
            '{keywords}'
            '',
            '',
            '*Keywords that use the template*',
            '{template_keywords}',
        )),
    }

    def __init__(self, slack_web_client, settings):
        """
        Loads keywords from config

        The superclass method ensured proper storage of various attributes

        :param ModbotWebclient slack_web_client: Slack web client
        :param dict settings: The settings to be applied by the module
        :return: None
        """
        super().__init__(slack_web_client, settings)
        self.config_file = settings['config_file']
        self.load_config()
        self.log_info('[Keyword] Module started and ready to go')

    def load_config(self):
        """Loads keywords from config file. Does nothing if file unreadable."""
        try:
            with open(self.config_file, "r") as config_file:
                data = json.loads(config_file.read().strip())
                if 'keywords' in data:
                    self.keywords = data['keywords']
                if 'config_data' in data:
                    self.config_data = data['config_data']
                if 'keyword_template_text' in data:
                    self.config_data = data['keyword_template_text']
        except IOError:
            logger.info('Keyword: Configuration file read error.')

    def save_config(self):
        """Saves keywords into the config file."""
        with open(self.config_file, "w") as config_file:
            json.dump({
                'keywords': self.keywords,
                'template': self.config_data,
                'keyword_template_text': self.keyword_template_text,
            }, config_file, ensure_ascii=False)

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
            'type': ['thread', 'ephemeral'],
            'thread_ts': event['ts'],
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

        # Configuration keywords
        if 'keyword' in event_text_sanitized.split(' '):
            # Exclude non-authorized people
            if self.user_is_admin(event['user']) \
                    and self.user_is_owner(event['user']):

                # Redirect to a private chat (no config in public)
                if event['channel_type'] == 'channel':
                    reply_data = self.switch_to_im(event)
                else:
                    if event_text_sanitized.startswith('keyword list'):
                        reply_data = self.keyword_list(event)
                    elif event_text_sanitized.startswith('keyword add'):
                        reply_data = self.keyword_add(event)
                    elif event_text_sanitized.startswith('keyword delete'):
                        reply_data = self.keyword_delete(event)
                    elif event_text_sanitized.startswith('keyword quickadd'):
                        reply_data = self.keyword_quickadd(event)
                    elif event_text_sanitized.startswith('keyword template'):
                        reply_data = self.keyword_template(event)
                    elif event_text_sanitized.startswith('keyword config'):
                        reply_data = self.keyword_config(event)
                    else:
                        reply_data = self.keyword(event)

        # We have a config message to send
        if reply_data and reply_data['ready_to_send']:
            reply_message.update(reply_data)
        else:
            # Reply if non-admin OR if replies to admin are allowed
            if self.config_data['reply_to_keywords_by_admins'] \
                    or not (self.user_is_admin(event['user'])
                            or self.user_is_owner(event['user'])):
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
        :rtype: dict
        """
        reply_data = {'type': 'regular'}

        # Just make the list and send it
        self.log_info('[Keyword] List viewed by %s', event['user'])
        keywords_list = '\n'.join([
            '*' + keyword + '* : ' + message
            for keyword, message in self.keywords.items()
            if isinstance(message, str)
        ])
        template_keywords_list = ', '.join([
            '*' + keyword + '* : #' + " #".join(message)
            for keyword, message in self.keywords.items()
            if not isinstance(message, str)])

        reply_text = self.replies['keyword_list'] \
            .replace('{keywords}', keywords_list) \
            .replace('{template_keywords}', template_keywords_list)
        reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def keyword_add(self, event):
        """
        Reacts to 'keyword add' messages

        :param dict event: The event received
        :return: Message to be sent
        :rtype: dict
        """
        reply_data = {'type': 'regular'}

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
            self.save_config()
            self.log_info('[Keyword] New keyword %s by %s',
                          keyword,
                          event['user'])
            reply_text = self.replies['keyword_add_confirmation'] \
                .replace('{keyword}', keyword)
            reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def keyword_template(self, event):
        """
        Reacts to 'keyword template' messages

        :param dict event: The event received
        :return: Message to be sent
        :rtype: dict
        """
        reply_data = {'type': 'regular'}

        # Data is missing from the keyword
        if len(event['text'].split(' ')) < 3:
            self.log_info('[Keyword] Template keyword missing info by user %s',
                          event['user'])
            reply_text = self.replies['keyword_template_missing_param']
            reply_data.update({'text': reply_text})
        else:
            template = event['text'][len('keyword template '):]
            if '{channels}' not in template:
                self.log_info(
                    '[Keyword] Template keyword missing {channels} by user %s',
                    event['user'])
                reply_text = self.replies['keyword_template_missing_channel']
                reply_data.update({'text': reply_text})
            else:
                self.keyword_template_text = template
                self.log_info('[Keyword] New template %s',
                              event['user'])
                reply_text = self.replies['keyword_template_confirmation']
                reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def keyword_quickadd(self, event):
        """
        Reacts to 'keyword quickadd' messages

        :param dict event: The event received
        :return: Message to be sent
        :rtype: dict
        """
        reply_data = {'type': 'regular'}

        # Data is missing from the keyword
        if len(event['text'].split(' ')) < 4:
            self.log_info('[Keyword] Quickadd keyword missing info by user %s',
                          event['user'])
            reply_text = self.replies['keyword_quickadd_missing_param']
            reply_data.update({'text': reply_text})
        else:
            _, _, keyword, *channels = event['text'].split(' ')
            list_channels = [x for x in channels
                             if x.startswith('<') and x.endswith('>')]
            if not list_channels:
                self.log_info(
                    '[Keyword] Quickadd keyword without channels by user %s',
                    event['user'])
                reply_text = self.replies['keyword_quickadd_missing_channel']
                reply_data.update({'text': reply_text})
            else:
                keyword = keyword.lower()
                self.keywords[keyword] = list_channels
                self.save_config()
                self.log_info('[Keyword] New quick keyword %s by %s',
                              keyword,
                              event['user'])
                reply_text = self.replies['keyword_quickadd_confirmation'] \
                    .replace('{keyword}', keyword)
                reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def keyword_delete(self, event):
        """
        Reacts to 'keyword delete' messages

        :param dict event: The event received
        :return: Message to be sent
        :rtype: dict
        """
        reply_data = {'type': 'regular'}

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
                self.save_config()
                self.log_info('[Keyword] Keyword %s deleted by %s',
                              keyword,
                              event['user'])
                reply_text = self.replies['keyword_delete_confirmation'] \
                    .replace('{keyword}', keyword)
                reply_data.update({'text': reply_text})
            else:
                reply_text = self.replies['keyword_delete_inexistant'] \
                    .replace('{keyword}', keyword)
                reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def keyword_config(self, event):
        """
        Reacts to 'keyword config' messages

        :param dict event: The event received
        :return: Message to be sent
        :rtype: False or dict
        """
        reply_data = {'type': 'regular'}

        # Data is missing from the keyword, so we go back to config "homepage"
        if len(event['text'].split(' ')) < 4:
            return self.keyword_config_list(event)

        _, _, key, *value = event['text'].split(' ')
        key = key.lower()
        value = ' '.join(value)
        if key in self.config_data:
            # For boolean values, check that we have received a boolean value
            if isinstance(self.config_data[key], bool) \
                    and value.lower() in ['true', 'false', '0', '1']:
                if value.lower() in ['false', '0']:
                    self.config_data[key] = False
                else:
                    self.config_data[key] = True
                reply_data.update({
                    'text': self.replies['keyword_config_confirmation'],
                })
            elif isinstance(self.config_data[key], str):
                self.config_data[key] = bool(value)
                reply_data.update({
                    'text': self.replies['keyword_config_confirmation'],
                })
            else:
                reply_data.update({
                    'text': self.replies['keyword_config_failure'],
                })
        else:
            reply_data.update({
                'text': self.replies['keyword_config_unknown_key'],
            })

        if 'text' in reply_data:
            reply_data.update({'ready_to_send': True})
            return reply_data
        else:
            return False

    def keyword_config_list(self, event):
        """
        Reacts to 'keyword config' and 'keyword config list' messages

        :param dict event: The event received
        :return: Message to be sent
        :rtype: dict
        """
        reply_data = {'type': 'regular'}

        # Just make the list and send it
        self.log_info('[Keyword] Config list viewed by %s', event['user'])

        config_list = '\n'.join([
            '*' + key + '* : '
            + self.replies['keyword_config_descriptions'][key] + ' '
            + self.replies['keyword_config_types']['boolean']
            + self.replies['keyword_config_current_value'] + ' '
            + str(value) + ' '
            for key, value in self.config_data.items()
            if isinstance(value, bool)
        ])

        config_list += '\n'.join([
            '*' + key + '* : '
            + self.replies['keyword_config_descriptions'][key] + ' '
            + self.replies['keyword_config_types']['str']
            + self.replies['keyword_config_current_value'] + ' '
            + value + ' '
            for key, value in self.config_data.items()
            if isinstance(value, str)
        ])

        config_list += '\n'.join([
            '*' + key + '* : '
            + self.replies['keyword_config_descriptions'] + ' '
            + self.replies['keyword_config_current_value'] + ' '
            + str(value) + ' '
            for key, value in self.config_data.items()
            if not isinstance(value, str) and not isinstance(value, bool)
        ])

        reply_text = self.replies['keyword_config_list'] \
            .replace('{config_keys}', config_list)
        reply_data.update({'text': reply_text})

        reply_data.update({'ready_to_send': True})
        return reply_data

    def switch_to_im(self, event):
        """
        Replies through IM when receiving config keywords in public

        :param dict event: The event received
        :return: Message to be sent
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
        keyword_reply = self.keywords[matching_keywords[0]]
        if isinstance(keyword_reply, str):
            reply_data.update({
                'text': keyword_reply,
                'ready_to_send': True
            })
        else:
            channels = ['#' + channel
                        for channel in keyword_reply
                        if '#' not in channel]
            channels += [channel
                         for channel in keyword_reply
                         if '#' in channel]
            reply_text = self.keyword_template_text \
                .replace('{channels}', ' '.join(channels))
            reply_data.update({
                'text': reply_text,
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
        if '#' in reply_message['text']:
            list_channels = set([x[1:]
                                 for x in re.split(r'\s', reply_message['text'])
                                 if x.startswith('#')])
            for channel in list_channels:
                channel_data = self.get_channel_info(channel)
                if channel_data:
                    reply_message['text'] = reply_message['text'].replace(
                        '#' + channel,
                        '<#' + channel_data['id'] + '>'
                    )

        if 'regular' in reply_message['type']:
            reply_to_send = reply_message.copy()
            del reply_to_send['type']
            del reply_to_send['thread_ts']
            self.web_client.chat_postMessage(reply_to_send)

        if 'ephemeral' in reply_message['type'] \
                and self.config_data['reply_in_ephemeral']:
            reply_to_send = reply_message.copy()
            del reply_to_send['type']
            del reply_to_send['thread_ts']
            self.web_client.chat_postEphemeral(reply_to_send)

        if 'thread' in reply_message['type'] \
                and self.config_data['reply_in_thread']:
            reply_to_send = reply_message.copy()
            del reply_to_send['type']
            self.web_client.chat_postMessage(reply_to_send)


modbot_extension.extension_store.register_extension(Keywords)
