# All the individual config players have their own tests, but this tests the
# generic ConfigPlayer functionality
from collections import namedtuple

from mpf.assets.show import Show
from mpf.config_players.device_config_player import DeviceConfigPlayer
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.core.config_player import ConfigPlayer

PlayCall = namedtuple('PlayCall', ['settings', 'key', 'priority', 'kwargs'])


class BananaPlayer(DeviceConfigPlayer):
    config_file_section = 'banana_player'
    show_section = 'bananas'
    machine_collection_name = 'bananas'

    def __init__(self, machine):
        super().__init__(machine)
        self.machine.bananas = dict()
        self.machine.banana_play_calls = list()

    def play(self, settings, context, calling_context, key=None, priority=0, start_time=None, **kwargs):
        del start_time
        self.machine.banana_play_calls.append(PlayCall(
            settings, key, priority, kwargs))

    def _clear(self, key):
        pass

    def get_express_config(self, value):
        return dict(banana=value)

    def get_full_config(self, value):
        return value


class TestConfigPlayers(MpfTestCase):

    def getConfigFile(self):
        return 'test_config_players.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/config_players/'

    def setUp(self):
        self.machine_config_patches['mpf']['config_players'] = dict()
        self.machine_config_patches['mpf']['config_players']['banana'] = \
            'mpf.tests.test_ConfigPlayers.BananaPlayer'

        self.add_to_config_validator('banana_player',
                                     dict(__valid_in__='machine, mode'))

        # Hack around globals in shows
        Show.next_id = 0

        super().setUp()

    def test_config_player(self):
        self.assertIn('bananas', self.machine.show_controller.show_players)

        # post events to make sure banana_player is called
        self.machine.events.post('event1')
        self.advance_time_and_run()

        play_call = self.machine.banana_play_calls.pop()

        self.assertEqual(play_call.settings, {'express': {}})
        self.assertEqual(play_call.key, None)
        self.assertEqual(play_call.kwargs, {})

        self.machine.events.post('event2')
        self.advance_time_and_run()

        play_call = self.machine.banana_play_calls.pop()

        self.assertEqual(play_call.settings,
                         {'some': {'banana': 'key'}})
        self.assertEqual(play_call.key, None)
        self.assertEqual(play_call.kwargs, {})  # todo

        self.machine.events.post('event3')
        self.advance_time_and_run()

        play_call = self.machine.banana_play_calls.pop()

        self.assertEqual(play_call.settings,
                         {'this_banana': {'some': 'key'},
                          'that_banana': {'some': 'key'}})
        self.assertEqual(play_call.key, None)
        self.assertEqual(play_call.kwargs, {})  # todo

        # event5 is in mode1, so make sure it is not called now

        self.assertEqual(0, len(self.machine.banana_play_calls))

        self.machine.events.post('event5')
        self.advance_time_and_run()

        self.assertEqual(0, len(self.machine.banana_play_calls))

        # Start the mode, make sure the mode player enables
        self.machine.modes['mode1'].start()
        self.advance_time_and_run()

        self.machine.events.post('event5')
        self.advance_time_and_run()

        play_call = self.machine.banana_play_calls.pop()

        self.assertEqual(play_call.settings, {'express': {}})
        # Mode should be passed properly
        # self.assertEqual(play_call.key, 'mode1')
        self.assertEqual(play_call.kwargs, {})  # todo

        # stop the mode, make sure the event doesn't fire
        self.machine.modes['mode1'].stop()
        self.advance_time_and_run()

        self.machine.events.post('event5')
        self.advance_time_and_run()

        self.assertEqual(0, len(self.machine.banana_play_calls))

        # Start a show
        self.machine.events.post('event4')
        self.advance_time_and_run()

        play_call = self.machine.banana_play_calls.pop()
        self.assertEqual(play_call.settings, {'banana1': {'banana': 'express'}})
        # self.assertEqual(play_call.key, 'show1.1')
        self.assertEqual(play_call.kwargs, {'show_tokens': {}})  # todo

        self.assertEqual(1, len(self.machine.show_player.instances['_global']['show_player']))

        # todo add tests for mode 1 show, make sure the mode is passed
        # todo make sure it stops when the mode ends, that banana clear is
        # called when it stops, and that it doesn't start again once the mode
        # is not running

    def test_empty_config_player_section(self):
        self.machine.modes.mode2.start()
        self.advance_time_and_run()
        self.machine.modes.mode2.stop()
        self.advance_time_and_run()
