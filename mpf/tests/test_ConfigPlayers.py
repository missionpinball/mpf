# All the individual config players have their own tests, but this tests the
# generic ConfigPlayer functionality
from collections import namedtuple

from mpf.tests.MpfTestCase import MpfTestCase
from mpf.core.config_player import ConfigPlayer

PlayCall = namedtuple('PlayCall',
                      'settings mode caller priority play_kwargs kwargs',
                      verbose=False)

class BananaPlayer(ConfigPlayer):
    config_file_section = 'banana_player'
    show_section = 'bananas'
    machine_collection_name = 'bananas'

    def __init__(self, machine):
        super().__init__(machine)
        self.machine.bananas = dict()
        self.machine.banana_play_calls = list()

    def play(self, settings, mode=None, caller=None, priority=None,
             play_kwargs=None, **kwargs):

        self.machine.banana_play_calls.append(PlayCall(
            settings, mode, caller, priority, play_kwargs, kwargs))

    def clear(self, caller, priority):
        pass

    def get_express_config(self, value):
        return dict(banana=value)

    def get_full_config(self, value):
        return value


player_cls = BananaPlayer


class TestConfigPlayers(MpfTestCase):

    def getConfigFile(self):
        return 'test_config_players.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/config_players/'

    def setUp(self):
        self.machine_config_patches['mpf']['config_players'] = dict()
        self.machine_config_patches['mpf']['config_players']['banana'] = \
            'mpf.tests.test_ConfigPlayers'

        super().setUp()

    def test_config_player(self):
        self.assertIn('bananas', ConfigPlayer.show_players)
        self.assertIn('banana_player', ConfigPlayer.config_file_players)

        # post events to make sure banana_player is called
        self.machine.events.post('event1')
        self.advance_time_and_run()

        play_call = self.machine.banana_play_calls.pop()

        self.assertEqual(play_call.settings, {'bananas': {'express': {}}})
        self.assertEqual(play_call.mode, None)
        self.assertEqual(play_call.caller, None)  # todo
        self.assertEqual(play_call.play_kwargs, None)  # todo
        self.assertEqual(play_call.kwargs, {'hold': None})  # todo

        self.machine.events.post('event2')
        self.advance_time_and_run()

        play_call = self.machine.banana_play_calls.pop()

        self.assertEqual(play_call.settings,
                         {'bananas': {'some': {'banana': 'key'}}})
        self.assertEqual(play_call.mode, None)
        self.assertEqual(play_call.caller, None)  # todo
        self.assertEqual(play_call.play_kwargs, None)  # todo
        self.assertEqual(play_call.kwargs, {'hold': None})  # todo

        self.machine.events.post('event3')
        self.advance_time_and_run()

        play_call = self.machine.banana_play_calls.pop()

        self.assertEqual(play_call.settings,
                         {'bananas': {'this_banana': {'some': 'key'},
                                      'that_banana': {'some': 'key'}}})
        self.assertEqual(play_call.mode, None)
        self.assertEqual(play_call.caller, None)  # todo
        self.assertEqual(play_call.play_kwargs, None)  # todo
        self.assertEqual(play_call.kwargs, {'hold': None})  # todo

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

        self.assertEqual(play_call.settings, {'bananas': {'express': {}}})
        # Mode should be passed properly
        self.assertEqual(play_call.mode, self.machine.modes['mode1'])
        self.assertEqual(play_call.caller, self.machine.modes['mode1'])
        self.assertEqual(play_call.play_kwargs, None)  # todo
        self.assertEqual(play_call.kwargs, {'hold': None})  # todo

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
        self.assertEqual(play_call.mode, None)
        # self.assertEqual(play_call.caller, None)  # todo
        # self.assertEqual(play_call.play_kwargs, None)  # todo
        # self.assertEqual(play_call.kwargs, {})  # todo

        self.assertEqual(1, len(self.machine.show_controller.running_shows))

        # todo add tests for mode 1 show, make sure the mode is passed
        # todo make sure it stops when the mode ends, that banana clear is
        # called when it stops, and that it doesn't start again once the mode
        # is not running

    def test_empty_config_player_section(self):
        self.machine.modes.mode2.start()
        self.advance_time_and_run()
        self.machine.modes.mode2.stop()
        self.advance_time_and_run()
