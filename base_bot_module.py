import logging, time

class BaseBotModule:
  global logging

  settings = {}
  state = {'channels': {}, 'users': {}}
  last_data_refresh = 0

  def __init__(self, slack_web_client, settings):
    self.webClient = slack_web_client
    self.settings = settings
    self.last_data_refresh = time.time()

  def on_message (self, event):
    pass

  def on_message_deletion (self, event):
    pass

  def on_message_changed (self, event):
    pass

  def log_info (self, msg, *args, **kwargs):
    global logging
    logging.info (msg, *args, **kwargs)

  def get_user_info (self, user):
    if (self.last_data_refresh + 60*10) < time.time():
      self.state = {'channels': {}, 'users': {}}
      self.log_info('Refreshing cache of users and channels')

    if user not in self.state['users']:
      self.state['users'][user] = self.webClient.users_info(user=user)['user']

    return self.state['users'][user]

