from base_bot_module import BaseBotModule
import os, json




class KeywordsModule (BaseBotModule):
  """Replies to messages containing given keywords with specific replies"""

  keywords = {}
  keywords_file_name = ''

  def __init__(self, slack_web_client, settings):
    super().__init__(slack_web_client, settings)
    # Load keywords
    self.load_keywords()

  # Loads keywords based on the configuration file
  def load_keywords (self):
    self.keywords_file_name = os.path.join(os.path.abspath(__file__).replace('.py', '_config.json'))
    try:
      data = open(self.keywords_file_name, "r")
      self.keywords = json.loads(data.read().strip())
      data.close()
    except IOError:
      logger.info('Keyword: config file not found')


  # Saves keywords in the configuration file
  def save_keywords (self):
    pointer = open(self.keywords_file_name, "w")
    json.dump(self.keywords, pointer, ensure_ascii=False, indent=2)
    pointer.close()

  # When receiving a message
  def on_message(self, event):
    payload = {
      'channel': event['channel'],
      'user': event['user'],
    }

    event_text_lower = event['text'].lower()

    accents_replacements = {
                'à': 'a', 'ä': 'a', 'â': 'a',
      'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e',
                          'ï': 'i', 'ï': 'i',
                          'ö': 'o', 'ô': 'o',
                'ù': 'u', 'ü': 'u', 'û': 'u',
    }

    for i, j in accents_replacements.items():
        event_text_lower = event_text_lower.replace(i, j)

    # Handle messages from admins first
    if 'keyword' in event_text_lower.split(' '):
      user = self.get_user_info(event['user'])
      if not user['is_admin'] and not user['is_owner']:
        self.log_info('Keyword détecté de config par utilisateur non admin - Utilisateur %s - Le processing continue', event['user'])
      else:
        # Redirect to a private chat so that we're not discussing in public
        if event['channel_type'] == 'channel':
          self.log_info('Keyword détecté de config sur canal public - Utilisateur %s - Redirigé vers une discussion privée', event['user'])

          open_IM_conversation = self.webClient.conversations_open({
            'users': [event['user']],
            'return_im': True
          })
          payload.update({'channel': open_IM_conversation['channel']['id']})

          payload.update({'text': 'Bonjour!\nJ\'ai remarqué que vous vouliez me configurer. Pourriez-vous le faire en privé?\nJe suis un peu timide...'})
        if event['channel_type'] == 'im':

          # Add a keyword
          if event_text_lower[0:11] == 'keyword add':
            if len(event['text'].split(' ')) < 4:
              self.log_info('Keyword - Erreur de données de %s', event['user'])
              payload.update({'text': 'Je n\'ai pas bien compris, pourriez-vous réessayer?'})
            else:
              _, _, keyword, *message = event['text'].split(' ')
              keyword = keyword.lower()
              self.keywords[keyword] = ' '.join(message)
              self.save_keywords()
              self.log_info('Keyword %s ajouté par %s', keyword, event['user'])
              payload.update({'text': 'Merci pour votre ajout! Je répondrai maintenant au mot-clé ' + keyword})


          # List all keywords
          elif event_text_lower[0:12] == 'keyword list':
            self.log_info('Keyword - Consultation de la config par %s', event['user'])
            payload.update({'text': 'Voici tous les mots-clés définis: \n' + '\n'.join(['*' + keyword + '* : ' + message for keyword, message in self.keywords.items()])})

          # Delete a keyword
          elif event_text_lower[0:14] == 'keyword delete':
            if len(event['text'].split(' ')) < 3:
              self.log_info('Keyword - Erreur de données de %s', event['user'])
              payload.update({'text': 'Je n\'ai pas bien compris, pourriez-vous réessayer?'})
            else:
              _, _, keyword, *_ = event['text'].split(' ')
              keyword = keyword.lower()
              if keyword in self.keywords:
                del self.keywords[keyword]
                self.save_keywords()
              self.log_info('Keyword %s supprimé par %s', keyword, event['user'])
              payload.update({'text': 'Merci pour votre suppression! Je ne répondrai plus au mot-clé ' + keyword})
          else:
            payload.update({
              'blocks':[
                {
                  'type': 'section',
                  'text': {
                    'type': 'mrkdwn',
                    'text': '''Configuration des mots-clés.\nPour voir la liste des mots-clés, dites 'keyword list'\nSi vous souhaitez ajouter un mot-clé, dites 'keyword add mot_cle message à envoyer'\nSi vous souhaitez supprimer un mot-clé, dites 'keyword delete mot_cle'\nAttention, les actions sont faites sans confirmation!!!'''
                  },

                },
              ],
            })
            self.log_info('Keyword de config - Utilisateur %s - Demande d\'action envoyée', event['user'])

    else:
      reply = self._get_reply_message (event_text_lower)
      if reply:
        keyword, reply_message = reply
        payload.update({'text': reply_message})
        self.log_info('Keyword détecté : %s de l\'utilisateur %s', keyword, event['user'])

    if 'text' in payload or 'blocks' in payload:
      if event['channel_type'] == 'im':
        self.webClient.chat_postMessage(payload)
      else:
        self.webClient.chat_postEphemeral(payload)
      return True

    # No keyword found
    else:
      return False




  # Finds which message should be sent based on the keywords
  def _get_reply_message(self, message_received):
    matching_keywords = [x for x in self.keywords if x in message_received.split(' ')]

    if matching_keywords != []:
      text = self.keywords[matching_keywords[0]]
      return (matching_keywords[0], text)
    return False
