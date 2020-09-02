"""IRC Chat Bot for monitoring a Twitch chatroom."""

import sys
import irc.bot
import requests
import logging
import textwrap


class TwitchClient(irc.bot.SingleServerIRCBot):

    """Thread to process Twitch chat events."""

    TWITCH_PLAYS_ENABLED = False

    def __init__(self, machine, username, password, channel):
        """Initialize Twitch Bot."""
        self.log = logging.getLogger('twitch_client')
        self.machine = machine
        self.password = password
        self.channel = '#' + channel

        # Create IRC bot connection
        server = 'irc.chat.twitch.tv'
        port = 6667
        self.log.info('Connecting to ' + server + ' on port ' + str(port) + '...')
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, 'oauth:' + password)], username, username)
        # self.connection.add_global_handler("all_events", self.on_all_events, -100)

    def on_welcome(self, c, e):
        """Framework will call when IRC server is joined."""
        self.log.info('Joining ' + self.channel)

        # You must request specific capabilities before you can use them
        c.cap('REQ', ':twitch.tv/membership')
        c.cap('REQ', ':twitch.tv/tags')
        c.cap('REQ', ':twitch.tv/commands')
        c.join(self.channel)

    def on_pubmsg(self, c, e):
        """Framework will call when a public message is posted in chat."""
        # If a chat message starts with ! or ?, try to run it as a command
        if e.arguments[0][:1] == '!' or e.arguments[0][:1] == '?':
            cmd = e.arguments[0].split(' ')[0][1:]
            self.do_command(e, cmd.lower())
        else:
            user = e.source.split('!')[0]
            message = 'Chat: [' + user + '] ' + e.arguments[0] + ' : ' + str(e)
            self.log.info(message.replace(self.password, 'XXXXX'))
            tags = self.build_tag_dict(e.tags)
            bits = tags.get('bits')
            message_type = tags.get('msg-id')
            user = tags.get('display-name', user)
            if message_type == 'sub' or message_type == 'resub':
                months = tags.get('msg-param-months', 1)
                subscriber_message = tags.get('message', '')
                self.machine.events.post(
                    'twitch_subscription',
                    user=user,
                    message=e.arguments[0],
                    months=int(months),
                    subscriber_message=subscriber_message
                )
            elif bits is not None:
                self.machine.set_machine_var('twitch_last_bits_user', user)
                self.machine.set_machine_var('twitch_last_bits_amount', bits)
                self.machine.events.post('twitch_bit_donation', user=user, message=e.arguments[0], bits=int(bits))
            else:
                length, lines = self.split_message(e.arguments[0], 6)
                self.machine.set_machine_var('twitch_last_chat_user', user)
                self.machine.set_machine_var('twitch_last_chat_message', e.arguments[0])
                self.machine.set_machine_var('twitch_last_chat_message_line_count', length)
                self.machine.set_machine_var('twitch_last_chat_message_line_1', lines[0])
                self.machine.set_machine_var('twitch_last_chat_message_line_2', lines[1])
                self.machine.set_machine_var('twitch_last_chat_message_line_3', lines[2])
                self.machine.set_machine_var('twitch_last_chat_message_line_4', lines[3])
                self.machine.set_machine_var('twitch_last_chat_message_line_5', lines[4])
                self.machine.set_machine_var('twitch_last_chat_message_line_6', lines[5])
                self.machine.events.post(
                    'twitch_chat_message',
                    user=user,
                    message=e.arguments[0],
                    line_count=length,
                    line_1=lines[0],
                    line_2=lines[1],
                    line_3=lines[2],
                    line_4=lines[3],
                    line_5=lines[4],
                    line_6=lines[5]
                )

    def on_privmsg(self, c, e):
        """Framework will call when a private message is posted in chat."""
        user = e.source.split('!')[0]
        self.log.info('Private chat: [' + user + '] ' + e.arguments[0])

    def on_all_events(self, c, e):
        """Framework will call when any IRC event is posted."""
        message = 'All Events: ' + e
        self.log.info(message.replace(self.password, 'XXXXX'))

    def do_command(self, e, cmd):
        """Handle a chat command (starts with ? or !)."""
        user = e.source.split('!')[0]
        self.log.info('Received command: [' + user + '] ' + cmd)

        if self.TWITCH_PLAYS_ENABLED:
            if cmd == 'l':
                self.machine.events.post('twitch_flip_left', user=user)
            elif cmd == 'r':
                self.machine.events.post('twitch_flip_right', user=user)

    def is_connected(self):
        """Return true if the server is connected."""
        return self.connection.is_connected()

    def build_tag_dict(self, seq):
        """Build a Python dict from IRC chat tags."""
        return dict((d['key'], d['value']) for (index, d) in enumerate(seq))

    def split_message(self, message, min_lines):
        """Split up a string into lines broken on words."""
        lines = textwrap.wrap(message, 21)
        length = len(lines)

        if length < min_lines:
            lines += [''] * (min_lines - len(lines))

        return length, lines
