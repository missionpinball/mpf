"""IRC Chat Bot for monitoring a Twitch chatroom."""
from functools import partial

import logging
import textwrap

try:
    from irc.bot import SingleServerIRCBot
    IMPORT_SUCCESS = True
except ImportError:
    SingleServerIRCBot = object     # prevent class loading error
    IMPORT_SUCCESS = False

MYPY = False
if MYPY:   # pragma: no cover
    import asyncio  # pylint: disable-msg=cyclic-import,unused-import


class TwitchClient(SingleServerIRCBot):

    """Thread to process Twitch chat events."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, machine, username, password, channel, loop):
        """Initialize Twitch Bot."""
        self.log = logging.getLogger('twitch_client')
        self.machine = machine
        self.password = password
        self.channel = '#' + channel.lower()
        self.loop = loop    # type: asyncio.AbstractEventLoop

        if not IMPORT_SUCCESS:
            raise AssertionError('Please install irc extension using "pip3 install irc" to use the twitch client.')

        # Create IRC bot connection
        server = 'irc.chat.twitch.tv'
        port = 6667
        self.log.info('Connecting to %s on port %s...', server, port)
        super().__init__([(
            server, port,
            (password if password.lower().startswith('oauth:') else ('oauth:' + password))
        )], username, username)
        # self.connection.add_global_handler("all_events", self.on_all_events, -100)

    def on_welcome(self, c, e):
        """Framework will call when IRC server is joined."""
        del e
        self.log.info('Joining %s', self.channel)

        # You must request specific capabilities before you can use them
        c.cap('REQ', ':twitch.tv/membership')
        c.cap('REQ', ':twitch.tv/tags')
        c.cap('REQ', ':twitch.tv/commands')
        c.join(self.channel)

    def on_pubmsg(self, c, e):
        """Framework will call when a public message is posted in chat."""
        del c
        # If a chat message starts with ! or ?, try to run it as a command
        is_command = False
        if e.arguments[0][:1] == '!' or e.arguments[0][:1] == '?':
            cmd = e.arguments[0].split(' ')[0][1:]
            self.do_command(e, cmd.lower())
            is_command = True

        self.process_twitch_event(e, is_command)

    def on_privmsg(self, c, e):
        """Framework will call when a private message is posted in chat."""
        del c
        self.log.info('Private Chat: %s', e.arguments[0])

    def on_usernotice(self, c, e):
        """Framework will call when a user notice is posted in chat."""
        del c
        self.process_twitch_event(e)

    def on_all_events(self, c, e):
        """Framework will call when any IRC event is posted."""
        del c
        message = 'All Events: ' + e
        self.log.info(message.replace(self.password, 'XXXXX'))

    def do_command(self, e, cmd):
        """Handle a chat command (starts with ? or !)."""
        user = e.source.split('!')[0]
        self.log.info('Received command: [' + user + '] ' + cmd.lower())

        self.post_event_in_mpf('twitch_command', user=user, command=cmd.lower())
        '''event: twitch_command
        desc: A user typed a line that begins with ! or ?
        args:
        command: The text after the ! or ?
        user: The chat user who executed the command
        '''

    def post_event_in_mpf(self, event, *args, **kwargs):
        """Post event in MPF via async loop to prevent race conditions."""
        self.loop.call_soon_threadsafe(partial(self.machine.events.post, event, *args, **kwargs))

    def set_machine_variable_in_mpf(self, name, value):
        """Set machine var in MPF via async loop to prevent race conditions."""
        self.loop.call_soon_threadsafe(self.machine.variables.set_machine_var, name, value)

    def is_connected(self):
        """Return true if the server is connected."""
        return self.connection.is_connected()

    def process_twitch_event(self, e, is_command=False):
        """Process the event and delegate to the proper handler."""
        tags = self.build_tag_dict(e.tags)
        message = next(iter(e.arguments or []), '')
        bits = tags.get('bits')
        message_type = tags.get('msg-id', '')
        user = tags.get('display-name', 'Unknown')
        is_sub = message_type in ('sub', 'resub')
        is_gift_sub = message_type in ('subgift', 'anonsubgift')
        is_raid = message_type == 'raid'

        log_message = 'Chat: [' + user + '] ' + message + ' : ' + str(e)
        self.log.info(log_message.replace(self.password, 'XXXXX'))

        if is_sub or is_gift_sub:
            self.process_subscription(user, message, tags, is_gift_sub)
        elif is_raid:
            self.process_raid(user, tags)
        elif bits is not None:
            self.process_bits(user, message, bits)
        else:
            self.process_chat(user, message, is_command)

    def process_subscription(self, user, message, tags, is_gift):
        """Send the subscription event to MPF."""
        months = tags.get('msg-param-months' if is_gift else 'msg-param-cumulative-months', 1)
        subscriber_message = tags.get('message', '')
        sub_plan = tags.get('msg-param-sub-plan', '')
        sub_plan_name = tags.get('msg-param-sub-plan-name', '')
        sub_recipient = tags.get('msg-param-recipient-display-name', user) if is_gift else user
        self.set_machine_variable_in_mpf('twitch_last_sub_user', user)
        self.set_machine_variable_in_mpf('twitch_last_sub_recipient', sub_recipient)
        self.set_machine_variable_in_mpf('twitch_last_sub_months', int(months))
        self.set_machine_variable_in_mpf('twitch_last_sub_message', subscriber_message)
        self.set_machine_variable_in_mpf('twitch_last_sub_plan', sub_plan)
        self.set_machine_variable_in_mpf('twitch_last_sub_plan_name', sub_plan_name)
        self.set_machine_variable_in_mpf('twitch_last_sub_is_gift', is_gift)
        self.post_event_in_mpf(
            'twitch_subscription',
            user=user,
            message=message,
            months=int(months),
            subscriber_message=subscriber_message,
            sub_plan=sub_plan,
            sub_plan_name=sub_plan_name,
            sub_recipient=sub_recipient,
            gift=is_gift
        )
        '''event: twitch_subscription
        desc: A chat user has subscribed or resubscribed on Twitch
        args:
        gift: True if this sub was gifted by another user
        message: Chat message text
        months: The number of months that the user has been a subscriber
        sub_plan: The subscription tier (Prime, 1000, 2000, 3000)
        sub_plan_name: The streamer specific name for the sub tier
        sub_recipient: The user who is subscribing
        subscriber_message: The message the user typed when subscribing
        user: The chat user name who paid for the subscription
        '''

    def process_raid(self, user, tags):
        """Send the raid event to MPF."""
        raid_user = tags.get('msg-param-displayName', user)
        raid_count = tags.get('msg-param-viewerCount', 0)
        self.set_machine_variable_in_mpf('twitch_last_raid_user', raid_user)
        self.set_machine_variable_in_mpf('twitch_last_raid_count', int(raid_count))
        self.post_event_in_mpf(
            'twitch_raid',
            raid_user=raid_user,
            raid_count=int(raid_count)
        )
        '''event: twitch_raid
        desc: Another Twitch user has raided your channel
        args:
        raid_user: The user who raided
        raid_count: The count of viewers in the raid
        '''

    def process_bits(self, user, message, bits):
        """Send the bit donation event to MPF."""
        self.set_machine_variable_in_mpf('twitch_last_bits_user', user)
        self.set_machine_variable_in_mpf('twitch_last_bits_amount', int(bits))
        self.post_event_in_mpf('twitch_bit_donation', user=user, message=message, bits=int(bits))
        '''event: twitch_bit_donation
        desc: A chat user has donated bits on Twitch
        args:
        message: Chat message text
        bits: The number of bits donated
        user: The chat user name who subscribed
        '''

    def process_chat(self, user, message, is_command):
        """Send the chat event to MPF."""
        length, lines = self.split_message(message, 6)
        self.set_machine_variable_in_mpf('twitch_last_chat_user', user)
        self.set_machine_variable_in_mpf('twitch_last_chat_message', message)
        self.set_machine_variable_in_mpf('twitch_last_chat_message_line_count', length)
        self.set_machine_variable_in_mpf('twitch_last_chat_message_line_1', lines[0])
        self.set_machine_variable_in_mpf('twitch_last_chat_message_line_2', lines[1])
        self.set_machine_variable_in_mpf('twitch_last_chat_message_line_3', lines[2])
        self.set_machine_variable_in_mpf('twitch_last_chat_message_line_4', lines[3])
        self.set_machine_variable_in_mpf('twitch_last_chat_message_line_5', lines[4])
        self.set_machine_variable_in_mpf('twitch_last_chat_message_line_6', lines[5])
        self.post_event_in_mpf(
            'twitch_chat_message',
            user=user,
            message=message,
            line_count=length,
            is_command=is_command,
            line_1=lines[0],
            line_2=lines[1],
            line_3=lines[2],
            line_4=lines[3],
            line_5=lines[4],
            line_6=lines[5]
        )
        '''event: twitch_chat_message
        desc: A chat message was received via Twitch
        args:
        line_count: The number of lines that the text splitter produced
        line_1: Split line 1
        line_2: Split line 2
        line_3: Split line 3
        line_4: Split line 4
        line_5: Split line 5
        line_6: Split line 6
        message: Full chat message text
        user: The chat user name who subscribed
        '''

    @staticmethod
    def build_tag_dict(seq):
        """Build a Python dict from IRC chat tags."""
        return dict((d['key'], d['value']) for (index, d) in enumerate(seq))

    @staticmethod
    def split_message(message, min_lines):
        """Split up a string into lines broken on words."""
        lines = textwrap.wrap(message, 21)
        length = len(lines)

        if length < min_lines:
            lines += [''] * (min_lines - len(lines))

        return length, lines
