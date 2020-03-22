from slack import WebClient

class BotWebClient (WebClient):
  def set_bot_settings (self, settings):
    self.settings = settings

  def chat_postMessage(self, input_data):
    payload = self.settings.copy()
    payload.update(input_data)

    return super().chat_postMessage(**payload)


  def conversations_open(self, input_data):
    payload = self.settings.copy()
    payload.update(input_data)

    return super().conversations_open(**payload)



  def chat_postEphemeral(self, input_data):
    payload = self.settings.copy()
    payload.update(input_data)

    return super().chat_postEphemeral(**payload)


  def conversations_join(self, channel, **kwargs):
    kwargs.update({"channel": channel})
    return super().api_call("conversations.join", json=kwargs)
