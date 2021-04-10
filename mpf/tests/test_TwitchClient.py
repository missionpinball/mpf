from unittest.mock import MagicMock

import sys
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class MockEvent:

    """Copy of the irc Events class."""

    def __init__(self, type, source, target, arguments=None, tags=None):

        self.type = type
        self.source = source
        self.target = target
        if arguments is None:
            arguments = []
        self.arguments = arguments
        if tags is None:
            tags = []
        self.tags = tags


class MockSingleServerIRCBot():

    """Mock server."""

    def __init__(self, server_list, nickname, realname, reconnection_interval=None, recon=None, **connect_params):
        self.connection = MagicMock()

    def start(self):
        pass


class TestTwitchClient(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/twitch_client/'

    def setUp(self):
        self.machine_config_patches['mpf']['plugins'] = ['mpf.plugins.twitch_bot.TwitchBot']
        sys.modules['irc.bot'] = MagicMock()
        sys.modules['irc.bot'].SingleServerIRCBot = MockSingleServerIRCBot
        super().setUp()

    def tearDown(self):
        del sys.modules['irc.bot']

    def test_twitch_chat(self):
        """Test connect and event posting."""
        self.mock_event("twitch_chat_message")
        tags = [
            {"key": "msg-id", "value": None},
            {"key": "bits", "value": None},
            {"key": "display-name", "value": "Some User"},
            {"key": "msg-param-months", "value": None},
            {"key": "message", "value": None},
        ]
        event = MockEvent("pubmsg", "some_user", "bot", ["Hello Bot"], tags)
        self.machine.plugins[0].client.on_pubmsg("some_channel", event)
        self.advance_time_and_run(.1)
        self.assertEventCalledWith("twitch_chat_message", is_command=False, line_1='Hello Bot', line_2='', line_3='',
                                   line_4='', line_5='', line_6='', line_count=1, message='Hello Bot', user='Some User')
        self.assertMachineVarEqual("Some User", "twitch_last_chat_user")
        self.assertMachineVarEqual("Hello Bot", "twitch_last_chat_message")

    def test_twitch_bits(self):
        """Test connect and event posting."""
        self.mock_event("twitch_bit_donation")
        tags = [
            {"key": "msg-id", "value": None},
            {"key": "bits", "value": 42},
            {"key": "display-name", "value": "Some User"},
            {"key": "msg-param-months", "value": None},
            {"key": "message", "value": None},
        ]
        event = MockEvent("pubmsg", "some_user", "bot", ["Hello Bot"], tags)
        self.machine.plugins[0].client.on_pubmsg("some_channel", event)
        self.advance_time_and_run(.1)
        self.assertEventCalled("twitch_bit_donation")
        self.assertMachineVarEqual("Some User", "twitch_last_bits_user")
        self.assertMachineVarEqual(42, "twitch_last_bits_amount")

    def test_twitch_sub(self):
        """Test connect and event posting."""
        self.mock_event("twitch_subscription")
        tags = [
            {"key": "msg-id", "value": "sub"},
            {"key": "bits", "value": None},
            {"key": "display-name", "value": "Some User"},
            {"key": "msg-param-months", "value": 1},
            {"key": "message", "value": "Sub message"},
        ]
        event = MockEvent("usernotice", "some_user", "bot", ["Hello Bot"], tags)
        self.machine.plugins[0].client.on_usernotice("some_channel", event)
        self.advance_time_and_run(.1)
        self.assertEventCalled("twitch_subscription")

    def test_twitch_resub(self):
        """Test connect and event posting."""
        self.mock_event("twitch_subscription")
        tags = [
            {"key": "msg-id", "value": "resub"},
            {"key": "bits", "value": None},
            {"key": "display-name", "value": "Some User"},
            {"key": "msg-param-months", "value": 42},
            {"key": "message", "value": "Sub message"},
        ]
        event = MockEvent("usernotice", "some_user", "bot", ["Hello Bot"], tags)
        self.machine.plugins[0].client.on_usernotice("some_channel", event)
        self.advance_time_and_run(.1)
        self.assertEventCalled("twitch_subscription")

    def test_twitch_gift_sub(self):
        """Test connect and event posting."""
        self.mock_event("twitch_subscription")
        tags = [
            {"key": "msg-id", "value": "subgift"},
            {"key": "bits", "value": None},
            {"key": "display-name", "value": "Some User"},
            {"key": "msg-param-months", "value": 1},
            {"key": "message", "value": "Sub message"},
        ]
        event = MockEvent("usernotice", "some_user", "bot", ["Hello Bot"], tags)
        self.machine.plugins[0].client.on_usernotice("some_channel", event)
        self.advance_time_and_run(.1)
        self.assertEventCalled("twitch_subscription")

    def test_twitch_anon_gift_sub(self):
        """Test connect and event posting."""
        self.mock_event("twitch_subscription")
        tags = [
            {"key": "msg-id", "value": "anonsubgift"},
            {"key": "bits", "value": None},
            {"key": "display-name", "value": "Some User"},
            {"key": "msg-param-months", "value": 42},
            {"key": "message", "value": "Sub message"},
        ]
        event = MockEvent("usernotice", "some_user", "bot", ["Hello Bot"], tags)
        self.machine.plugins[0].client.on_usernotice("some_channel", event)
        self.advance_time_and_run(.1)
        self.assertEventCalled("twitch_subscription")

    def test_twitch_sub_no_message(self):
        """Test connect and event posting."""
        self.mock_event("twitch_subscription")
        tags = [
            {"key": "msg-id", "value": "sub"},
            {"key": "bits", "value": None},
            {"key": "display-name", "value": "Some User"},
            {"key": "msg-param-months", "value": 1},
            {"key": "message", "value": "Sub message"},
        ]
        event = MockEvent("usernotice", "some_user", "bot", [], tags)
        self.machine.plugins[0].client.on_usernotice("some_channel", event)
        self.advance_time_and_run(.1)
        self.assertEventCalled("twitch_subscription")

    def test_twitch_raid(self):
        """Test connect and event posting."""
        self.mock_event("twitch_raid")
        tags = [
            {"key": "msg-id", "value": "raid"},
            {"key": "bits", "value": None},
            {"key": "display-name", "value": "Some User"},
            {"key": "msg-param-months", "value": 1},
            {"key": "message", "value": "Sub message"},
        ]
        event = MockEvent("usernotice", "some_user", "bot", ["Hello Bot"], tags)
        self.machine.plugins[0].client.on_usernotice("some_channel", event)
        self.advance_time_and_run(.1)
        self.assertEventCalled("twitch_raid")
