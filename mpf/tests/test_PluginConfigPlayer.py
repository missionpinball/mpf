from unittest.mock import MagicMock, call

from mpf.config_players.plugin_player import PluginPlayer
from mpf.core.config_player import ConfigPlayer
from mpf.tests.MpfBcpTestCase import MpfBcpTestCase
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

    def _validate_config_item(self, device, device_settings):
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

    def _validate_config_item(self, device, device_settings):
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


class TestPluginConfigPlayer(MpfBcpTestCase):
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

        self._bcp_client.send = MagicMock()

    def test_plugin_config_player(self):
        self.assertIn('tests', self.machine.show_controller.show_players)
        self.assertIn('test2s', self.machine.show_controller.show_players)

        # event1 is in the test_player only. Check that it's sent as a
        # trigger
        self._bcp_client.send.reset_mock()
        self.machine.events.post('event1')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_once_with('trigger', {'name': 'event1'})
        self._bcp_client.send.reset_mock()

        # event2 is in the test_player and test2_player. Check that it's only
        # sent once
        self.machine.events.post('event2')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_once_with('trigger', {'name': 'event2'})
        self._bcp_client.send.reset_mock()

        # event3 is test2_player only. Check that it's only sent once
        self.machine.events.post('event3')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_once_with('trigger', {'name': 'event3'})
        self._bcp_client.send.reset_mock()

        # event4 isn't used in any player. Check that it's not sent
        self.machine.events.post('event4')
        self.advance_time_and_run()
        assert not self._bcp_client.send.called

        # Start mode1
        self.machine.modes['mode1'].start()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes['mode1'].active)
        self._bcp_client.send.assert_called_with('mode_start', {'name': 'mode1', 'priority': 400})
        self._bcp_client.send.reset_mock()

        # event4 is in test_player for mode1, so make sure it sends now
        self.machine.events.post('event4')
        self.advance_time_and_run()

        self._bcp_client.send.assert_called_with('trigger', {'name': 'event4'})
        self._bcp_client.send.reset_mock()

        # Stop mode 1
        self.machine.modes['mode1'].stop()
        self.advance_time_and_run()
        self._bcp_client.send.assert_has_calls([
            call('mode_stop', {'name': 'mode1'}),
            call('trigger', {'context': 'mode1', 'name': 'tests_clear'}),
            call('trigger', {'context': 'mode1', 'name':'test2s_clear'})]
        )
        self._bcp_client.send.reset_mock()

        # post event4 again, and it should not be sent since that mode was
        # stopped
        self.machine.events.post('event4')
        self.advance_time_and_run()
        assert not self._bcp_client.send.called

        # event1, event2, and event3 should still work. Even though they were
        # in mode1, they were also in the base config

        # event1
        self.machine.events.post('event1')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_once_with('trigger', {'name': 'event1'})
        self._bcp_client.send.reset_mock()

        # event2
        self.machine.events.post('event2')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_once_with('trigger', {'name': 'event2'})
        self._bcp_client.send.reset_mock()


        # event3
        self.machine.events.post('event3')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_once_with('trigger', {'name': 'event3'})
        self._bcp_client.send.reset_mock()

    def test_plugin_from_show(self):
        self.machine.shows['show1'].play()
        self.advance_time_and_run()
