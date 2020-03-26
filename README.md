# Slack Modbot
Slack bot for managing large communities and high volume of users.

The initial idea was to reply to keywords and redirect users to the right channel.
The bot is meant in a modular way, meaning new extensions can be added (quite) easily.

Currently:
- The Keywords extension will reply to users with specific keywords, in an ephemeral message (rather than in public like Slackbot)
- There are no other extension built yet

## Ideas for new extensions
- Keywords: include a template of message, so that we can have a consistent message
- New extension: List all users of a given thread (to invite them easily in a separate channel) - Maybe the bot should invite them directly?
- New extension: detect / react to spam. To be efficient, this would require admin access, which I don't want to have (see disclaimer below)
- New extension: Send the description of a channel when joining it (to highlight the description)
- New extension: Greet new users when they join the workspace (This would be a duplicate of Greetbot)

## Improvements
- Ensure links posted by the bot works ('#something' should be a link)
- Keywords extension: Reply in threads rather than ephemeral messages (so that it's visible by other users) - However threads may not be very visible
- Reply to "help"
- Reply to users in direct message
- Include limitation of messages sent per user (to avoid spamming people)
- Switch to a production-ready server (Flask was a default choice)
-

## Issues to be fixed
- Restrict extensions by channel (and provide admins a way to control that)
- In the log, include the name of the person (not just the ID)
- New extension to manage other extensions (start, stop, activate on a given channel, ...)
- New extension to manage the bot itself (emergency shutdown)



# IMPORTANT

I'm not a Python expert. Neither am I a professional developer, so use anything here at your own risk!
