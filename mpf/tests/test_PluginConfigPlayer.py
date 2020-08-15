from unittest.mock import MagicMock, call

from mpf.config_players.plugin_player import PluginPlayer
from mpf.tests.MpfBcpTestCase import MpfBcpTestCase
from mpf.tests.MpfTestCase import TestMachineController


# Override the plugin player functionality so that it pulls in our test one
def _register_plugin_config_players(self):
    TestConfigPlayer.register_with_mpf(self)
    TestConfigPlayer2.register_with_mpf(self)
    TestConfigPlayer3.register_with_mpf(self)

TestMachineController._register_plugin_config_players = _register_plugin_config_players     # type: ignore


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

    @staticmethod
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

    @staticmethod
    def register_with_mpf(machine):
        return 'test2', TestConfigPlayer2(machine)


class TestConfigPlayer3(PluginPlayer):
    config_file_section = 'test3_player'
    show_section = 'test3s'

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

    @staticmethod
    def register_with_mpf(machine):
        return 'test3', TestConfigPlayer3(machine)


class TestPluginConfigPlayer(MpfBcpTestCase):
    def get_config_file(self):
        return 'plugin_config_player.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/plugin_config_player/'

    def setUp(self):
        self.machine_spec_patches['test_player'] = dict(__valid_in__='machine, mode')
        self.machine_spec_patches['test2_player'] = dict(__valid_in__='machine, mode')

        super().setUp()
        self._bcp_client.send = MagicMock()

    def test_plugin_config_player(self):
        # Setup BCP to monitor mode events
        self._bcp_client.receive_queue.put_nowait(('monitor_start', {'category': 'modes'}))
        self.advance_time_and_run()

        self.assertIn('tests', self.machine.show_controller.show_players)
        self.assertIn('test2s', self.machine.show_controller.show_players)

        # event1 is in the test_player only. Check that it's sent as a
        # trigger
        self._bcp_client.send.reset_mock()
        self.machine.events.post('event1')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_with('trigger', {'priority': 0, 'settings': {'tests': {}},
                                                             'name': 'tests_play', 'calling_context': 'event1',
                                                             'context': '_global'})

        self.assertEqual(1, len(self.machine.bcp.transport._handlers["tests_play"]))
        self._bcp_client.send.reset_mock()
        self.machine.events.post('event1')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_with('trigger', {'priority': 0, 'settings': {'tests': {}},
                                                             'name': 'tests_play', 'calling_context': 'event1',
                                                             'context': '_global'})

        self.assertEqual(1, len(self.machine.bcp.transport._handlers["tests_play"]))
        self._bcp_client.send.reset_mock()

        # event2 is in the test_player and test2_player. Check that it's only
        # sent once
        self.machine.events.post('event2')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_with('trigger', {'calling_context': 'event2', 'context': '_global',
                                                             'priority': 0, 'name': 'test2s_play',
                                                             'settings': {'test2s': {}}})
        self._bcp_client.send.reset_mock()

        # event3 is test2_player only. Check that it's only sent once
        self.machine.events.post('event3')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_with('trigger', {'priority': 0, 'name': 'test2s_play',
                                                             'context': '_global', 'settings': {'test2s': {}},
                                                             'calling_context': 'event3'})
        self._bcp_client.send.reset_mock()

        # fake_event isn't used in any player. Check that it's not sent
        self.machine.events.post('fake_event')
        self.advance_time_and_run()
        assert not self._bcp_client.send.called

        # Start mode1
        self.machine.modes['mode1'].start()
        self.advance_time_and_run()
        self.assertTrue(self.machine.modes['mode1'].active)
        self._bcp_client.send.assert_called_with
        self._bcp_client.send.assert_has_calls([
            call('mode_start', {'name': 'mode1', 'priority': 400}),
            call('mode_list', {'running_modes': [('mode1', 400), ('attract', 10)]})
        ])
        self._bcp_client.send.reset_mock()

        # event4 is in test_player for mode1, so make sure it sends now
        self.machine.events.post('event4')
        self.advance_time_and_run()

        self._bcp_client.send.assert_called_with('trigger', {'settings': {'tests': {}}, 'calling_context': 'event4',
                                                             'priority': 400, 'context': 'mode1', 'name': 'tests_play'})
        self._bcp_client.send.reset_mock()

        # Stop mode 1
        self.machine.modes['mode1'].stop()
        self.advance_time_and_run()
        self._bcp_client.send.assert_has_calls([
            call('trigger', {'context': 'mode1', 'name': 'tests_clear'}),
            call('trigger', {'context': 'mode1', 'name': 'test2s_clear'}),
            call('mode_stop', {'name': 'mode1'}),
            call('mode_list', {'running_modes': [('attract', 10)]})
        ])
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
        self._bcp_client.send.assert_called_with('trigger', {'settings': {'tests': {}}, 'calling_context': 'event1',
                                                             'name': 'tests_play', 'context': '_global', 'priority': 0})
        self._bcp_client.send.reset_mock()

        # event2
        self.machine.events.post('event2')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_with('trigger', {'settings': {'test2s': {}}, 'context': '_global',
                                                             'calling_context': 'event2', 'name': 'test2s_play',
                                                             'priority': 0})
        self._bcp_client.send.reset_mock()

        # event3
        self.machine.events.post('event3')
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_with('trigger', {'context': '_global', 'name': 'test2s_play',
                                                             'calling_context': 'event3', 'settings': {'test2s': {}},
                                                             'priority': 0})
        self._bcp_client.send.reset_mock()

    def test_plugin_from_show(self):
        t1_player = self.machine.show_controller.show_players['tests']
        t1_player.play = MagicMock()

        self.machine.shows['show1'].play()
        self.advance_time_and_run()

        self.assertTrue(t1_player.play.called)
        self.assertEqual(1, len(self.machine.bcp.transport._handlers["tests_play"]))
        self.assertEqual(1, len(self.machine.bcp.transport._handlers["tests_clear"]))

        self.assertIn('tests_play', self.machine.bcp.transport._handlers)
        self.assertIn('tests_clear', self.machine.bcp.transport._handlers)
        self.assertIn('test2s_play', self.machine.bcp.transport._handlers)
        self.assertIn('test2s_clear', self.machine.bcp.transport._handlers)

    def test_conditional_events(self):
        self.machine.events.post('event5')
        self.advance_time_and_run()
        self._bcp_client.send.assert_not_called()
        self._bcp_client.send.reset_mock()

        self.machine.events.post('event5', foo=0)
        self.advance_time_and_run()
        self._bcp_client.send.assert_called_once_with('trigger', {'settings': {'tests': {}}, 'name': 'tests_play',
                                                                  'priority': 0, 'context': '_global',
                                                                  'calling_context': 'event5{foo==0}',
                                                                  'foo': 0})
        self._bcp_client.send.reset_mock()

    def test_plugin_in_show_but_not_standalone(self):
        # tests a plugin player that has an entry in a show, but that does
        # not have a config player entry section in any other config file

        # e.g. a "slides" section in a show, but now "slide_player:"
        # section anywhere

        t3_player = self.machine.show_controller.show_players['test3s']
        t3_player.play = MagicMock()

        self.machine.modes['mode1'].start()
        self.advance_time_and_run()

        self.post_event('start_show3')

        self.assertIn('test3s_play', self.machine.bcp.transport._handlers)
        self.assertIn('test3s_clear', self.machine.bcp.transport._handlers)

        self.assertTrue(t3_player.play.called)
