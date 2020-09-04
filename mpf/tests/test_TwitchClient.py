import sys

from mock import MagicMock
from unittest.mock import patch

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestTwitchClient(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/twitch_client/'

    def setUp(self):
        self.machine_config_patches['mpf']['plugins'] = ['mpf.plugins.twitch_bot.TwitchBot']
        sys.modules['irc'] = MagicMock()
        sys.modules['irc.bot'] = MagicMock()
        super().setUp()

    def tearDown(self):
        del sys.modules['irc']
        del sys.modules['irc.bot']

    def test_twitch_client(self):
        """Test connect and event posting."""
        self.assertEventCalled("twitch_connected")
