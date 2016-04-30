from mpf.config_players.plugin_player import PluginPlayer
from mpf.core.config_player import ConfigPlayer
import mpf.core.config_validator
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.MpfTestCase import TestMachineController


# Override the plugin player functionality so that it pulls in our test one
def _register_plugin_config_players(self):
    TestConfigPlayer.register_with_mpf(self)
    TestConfigPlayer2.register_with_mpf(self)

TestMachineController._register_plugin_config_players = _register_plugin_config_players


class TestConfigPlayer(PluginPlayer):
    config_file_section = 'test_player'
    show_section = 'tests'

    def get_express_config(self, value):
        return dict(some=value)

    def validate_config(self, config):
        validated_config = dict()

        for event, settings in config.items():
            validated_config[event] = dict()
            validated_config[event][self.show_section] = dict()

            if not isinstance(settings, dict):
                settings = {settings: dict()}

        return validated_config

    def validate_show_config(self, device, device_settings):
        if device_settings is None:
            device_settings = device

        if not isinstance(device_settings, dict):
            device_settings = self.get_express_config(device_settings)


        devices = [device]

        return_dict = dict()
        for device in devices:
            return_dict[device] = device_settings

        return return_dict

    def register_with_mpf(machine):
        return 'test', TestConfigPlayer(machine)

class TestConfigPlayer2(PluginPlayer):
    config_file_section = 'test2_player'
    show_section = 'test2s'

    def get_express_config(self, value):
        return dict(some=value)

    def validate_config(self, config):
        validated_config = dict()

        for event, settings in config.items():
            validated_config[event] = dict()
            validated_config[event][self.show_section] = dict()
            if not isinstance(settings, dict):
                settings = {settings: dict()}

        return validated_config

    def validate_show_config(self, device, device_settings):
        if device_settings is None:
            device_settings = device

        if not isinstance(device_settings, dict):
            device_settings = self.get_express_config(device_settings)

        devices = [device]

        return_dict = dict()
        for device in devices:
            return_dict[device] = device_settings

        return return_dict

    def register_with_mpf(machine):
        return 'test2', TestConfigPlayer2(machine)


class TestPluginConfigPlayer(MpfTestCase):
    def getConfigFile(self):
        return 'plugin_config_player.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/plugin_config_player/'

    def setUp(self):

        self.add_to_config_validator('test_player',
                                     dict(__valid_in__='machine, mode'))
        self.add_to_config_validator('test2_player',
                                     dict(__valid_in__='machine, mode'))

        super().setUp()

    def __init__(self, methodName):
        super().__init__(methodName)
        # remove config patch which disables bcp
        del self.machine_config_patches['bcp']

    def test_plugin_config_player(self):
        self.patch_bcp()
        self.assertIn('tests', ConfigPlayer.show_players)
        self.assertIn('test_player', ConfigPlayer.config_file_players)
        self.assertIn('test2s', ConfigPlayer.show_players)
        self.assertIn('test2_player', ConfigPlayer.config_file_players)

        # event1 is in the test_player only. Check that it's sent as a
        # trigger
        self.machine.events.post('event1')
        self.advance_time_and_run()
        self.assertIn(('trigger', None, dict(name='event1')),
                      self.sent_bcp_commands)

        # event2 is in the test_player and test2_player. Check that it's only
        # sent once
        self.sent_bcp_commands = list()
        self.machine.events.post('event2')
        self.advance_time_and_run()
        self.assertIn(('trigger', None, dict(name='event2')),
              self.sent_bcp_commands)
        self.assertEqual(1, len(self.sent_bcp_commands))

        # event3 is test2_player only. Check that it's only sent once
        self.sent_bcp_commands = list()
        self.machine.events.post('event3')
        self.advance_time_and_run()
        self.assertIn(('trigger', None, dict(name='event3')),
              self.sent_bcp_commands)
        self.assertEqual(1, len(self.sent_bcp_commands))

        # event4 isn't used in any player. Check that it's not sent
        self.sent_bcp_commands = list()
        self.machine.events.post('event4')
        self.advance_time_and_run()
        self.assertNotIn(('trigger', None, dict(name='event4')),
              self.sent_bcp_commands)
        self.assertEqual(0, len(self.sent_bcp_commands))

        # Start mode1
        self.machine.modes['mode1'].start()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes['mode1'].active)

        # event4 is in test_player for mode1, so make sure it sends now
        self.sent_bcp_commands = list()
        self.machine.events.post('event4')
        self.advance_time_and_run()

        self.assertIn(('trigger', None, dict(name='event4')),
                      self.sent_bcp_commands)

        # Stop mode 1
        self.machine.modes['mode1'].stop()
        self.advance_time_and_run()

        # post event4 again, and it should not be sent since that mode was
        # stopped
        self.sent_bcp_commands = list()
        self.machine.events.post('event4')
        self.advance_time_and_run()
        self.assertNotIn(('trigger', None, dict(name='event4')),
              self.sent_bcp_commands)
        self.assertEqual(0, len(self.sent_bcp_commands))

        # event1, event2, and event3 should still work. Even though they were
        # in mode1, they were also in the base config

        # event1
        self.sent_bcp_commands = list()
        self.machine.events.post('event1')
        self.advance_time_and_run()
        self.assertIn(('trigger', None, dict(name='event1')),
                      self.sent_bcp_commands)

        # event2
        self.sent_bcp_commands = list()
        self.machine.events.post('event2')
        self.advance_time_and_run()
        self.assertIn(('trigger', None, dict(name='event2')),
              self.sent_bcp_commands)
        self.assertEqual(1, len(self.sent_bcp_commands))

        self.sent_bcp_commands = list()

        # event3
        self.sent_bcp_commands = list()
        self.machine.events.post('event3')
        self.advance_time_and_run()
        self.assertIn(('trigger', None, dict(name='event3')),
              self.sent_bcp_commands)
        self.assertEqual(1, len(self.sent_bcp_commands))

    def test_plugin_from_show(self):
        self.patch_bcp()

        self.machine.shows['show1'].play()
        self.advance_time_and_run()
