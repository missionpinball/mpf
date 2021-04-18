from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase

from mpf.tests.MpfGameTestCase import MpfGameTestCase
from unittest.mock import MagicMock, patch


class TestGame(MpfGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/game/'

    def get_platform(self):
        return 'smart_virtual'

    def testSinglePlayerGame(self):
        # setup event callbacks
        self._events = MagicMock()

        # Create handler entries for all game lifecycle events we wish to test
        self.machine.events.add_handler('game_will_start', self._events, event_name='game_will_start')
        self.machine.events.add_handler('game_starting', self._events, event_name='game_starting')
        self.machine.events.add_handler('game_started', self._events, event_name='game_started')
        self.machine.events.add_handler('player_add_request', self._events, event_name='player_add_request')
        self.machine.events.add_handler('player_will_add', self._events, event_name='player_will_add')
        self.machine.events.add_handler('player_adding', self._events, event_name='player_adding')
        self.machine.events.add_handler('player_added', self._events, event_name='player_added')
        self.machine.events.add_handler('player_turn_will_start', self._events, event_name='player_turn_will_start')
        self.machine.events.add_handler('player_turn_starting', self._events, event_name='player_turn_starting')
        self.machine.events.add_handler('player_turn_started', self._events, event_name='player_turn_started')
        self.machine.events.add_handler('ball_will_start', self._events, event_name='ball_will_start')
        self.machine.events.add_handler('ball_starting', self._events, event_name='ball_starting')
        self.machine.events.add_handler('ball_started', self._events, event_name='ball_started')
        self.machine.events.add_handler('ball_will_end', self._events, event_name='ball_will_end')
        self.machine.events.add_handler('ball_ending', self._events, event_name='ball_ending')
        self.machine.events.add_handler('ball_ended', self._events, event_name='ball_ended')
        self.machine.events.add_handler('game_will_end', self._events, event_name='game_will_end')
        self.machine.events.add_handler('game_ending', self._events, event_name='game_ending')
        self.machine.events.add_handler('game_ended', self._events, event_name='game_ended')

        # prepare game
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices["bd_trough"].balls)

        # start game (single player)
        self.start_game()
        self.assertGameIsRunning()
        self.assertPlayerNumber(1)
        self.assertBallNumber(1)

        self.assertEqual(3, self.machine.modes["game"].balls_per_game)

        # Assert game startup sequence
        self.assertEqual(13, self._events.call_count)
        self.assertEqual('game_will_start', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('game_starting', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('player_add_request', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_will_add', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual('player_adding', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('player_added', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[5][1]['num'])
        self.assertEqual('game_started', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual('player_turn_will_start', self._events.call_args_list[7][1]['event_name'])
        self.assertEqual('player_turn_starting', self._events.call_args_list[8][1]['event_name'])
        self.assertEqual('player_turn_started', self._events.call_args_list[9][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[9][1]['number'])
        self.assertEqual('ball_will_start', self._events.call_args_list[10][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[11][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[11][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[11][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[12][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[12][1]['ball'])
        self.assertEqual(1, self._events.call_args_list[12][1]['player'])
        self._events.reset_mock()

        # Drain the first ball
        self.drain_all_balls()
        self.advance_time_and_run()
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)

        # Assert ball drain, next ball start sequence
        self.assertEqual(9, self._events.call_count)
        self.assertEqual('ball_will_end', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ending', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_turn_will_start', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual('player_turn_starting', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('player_turn_started', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[5][1]['number'])
        self.assertEqual('ball_will_start', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[7][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[7][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[7][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[8][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[8][1]['ball'])
        self._events.reset_mock()

        # Drain the second ball
        self.drain_all_balls()
        self.advance_time_and_run()
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)

        # Assert ball drain, next ball start sequence
        self.assertEqual(9, self._events.call_count)
        self.assertEqual('ball_will_end', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ending', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_turn_will_start', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual('player_turn_starting', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('player_turn_started', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[5][1]['number'])
        self.assertEqual('ball_will_start', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[7][1]['event_name'])
        self.assertEqual(0, self._events.call_args_list[7][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[7][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[8][1]['event_name'])
        self.assertEqual(3, self._events.call_args_list[8][1]['ball'])
        self._events.reset_mock()

        # Drain the third (and last) ball
        self.drain_all_balls()
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        # Assert ball drain, game ending sequence
        self.assertEqual(6, self._events.call_count)
        self.assertEqual('ball_will_end', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ending', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('game_will_end', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual('game_ending', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('game_ended', self._events.call_args_list[5][1]['event_name'])

    def testMultiplePlayerGame(self):
        # setup event callbacks
        self._events = MagicMock()

        # Create handler entries for all game lifecycle events we wish to test
        self.machine.events.add_handler('game_will_start', self._events, event_name='game_will_start')
        self.machine.events.add_handler('game_starting', self._events, event_name='game_starting')
        self.machine.events.add_handler('game_started', self._events, event_name='game_started')
        self.machine.events.add_handler('player_add_request', self._events, event_name='player_add_request')
        self.machine.events.add_handler('player_will_add', self._events, event_name='player_will_add')
        self.machine.events.add_handler('player_adding', self._events, event_name='player_adding')
        self.machine.events.add_handler('player_added', self._events, event_name='player_added')
        self.machine.events.add_handler('player_turn_will_start', self._events, event_name='player_turn_will_start')
        self.machine.events.add_handler('player_turn_starting', self._events, event_name='player_turn_starting')
        self.machine.events.add_handler('player_turn_started', self._events, event_name='player_turn_started')
        self.machine.events.add_handler('player_turn_will_end', self._events, event_name='player_turn_will_end')
        self.machine.events.add_handler('player_turn_ending', self._events, event_name='player_turn_ending')
        self.machine.events.add_handler('player_turn_ended', self._events, event_name='player_turn_ended')
        self.machine.events.add_handler('ball_will_start', self._events, event_name='ball_will_start')
        self.machine.events.add_handler('ball_starting', self._events, event_name='ball_starting')
        self.machine.events.add_handler('ball_started', self._events, event_name='ball_started')
        self.machine.events.add_handler('ball_will_end', self._events, event_name='ball_will_end')
        self.machine.events.add_handler('ball_ending', self._events, event_name='ball_ending')
        self.machine.events.add_handler('ball_ended', self._events, event_name='ball_ended')
        self.machine.events.add_handler('game_will_end', self._events, event_name='game_will_end')
        self.machine.events.add_handler('game_ending', self._events, event_name='game_ending')
        self.machine.events.add_handler('game_ended', self._events, event_name='game_ended')

        # prepare game
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices["bd_trough"].balls)

        # start game (first player)
        self.start_game()
        self.advance_time_and_run(5)
        self.assertGameIsRunning()
        self.assertPlayerNumber(1)
        self.assertBallNumber(1)

        self.assertEqual(3, self.machine.modes["game"].balls_per_game)

        # Assert game startup sequence
        self.assertEqual(13, self._events.call_count)
        self.assertEqual('game_will_start', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('game_starting', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('player_add_request', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_will_add', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual('player_adding', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('player_added', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[5][1]['num'])
        self.assertEqual('game_started', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual('player_turn_will_start', self._events.call_args_list[7][1]['event_name'])
        self.assertEqual('player_turn_starting', self._events.call_args_list[8][1]['event_name'])
        self.assertEqual('player_turn_started', self._events.call_args_list[9][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[9][1]['number'])
        self.assertEqual('ball_will_start', self._events.call_args_list[10][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[11][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[11][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[11][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[12][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[12][1]['ball'])
        self.assertEqual(1, self._events.call_args_list[12][1]['player'])
        self._events.reset_mock()

        # add another player (player 2)
        self.add_player()

        # Assert game startup sequence
        self.assertEqual(4, self._events.call_count)
        self.assertEqual('player_add_request', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('player_will_add', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('player_adding', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_added', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[3][1]['num'])
        self._events.reset_mock()

        # Drain the first ball (player 1)
        self.drain_all_balls()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(2)
        self.assertBallNumber(1)

        # Assert ball drain, next ball start sequence
        self.assertEqual(12, self._events.call_count)
        self.assertEqual('ball_will_end', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ending', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_turn_will_end', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual('player_turn_ending', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('player_turn_ended', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual('player_turn_will_start', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual('player_turn_starting', self._events.call_args_list[7][1]['event_name'])
        self.assertEqual('player_turn_started', self._events.call_args_list[8][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[8][1]['number'])
        self.assertEqual('ball_will_start', self._events.call_args_list[9][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[10][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[10][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[10][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[11][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[11][1]['ball'])
        self._events.reset_mock()

        # Drain the first ball (player 2)
        self.drain_all_balls()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)

        # Assert ball drain, next ball start sequence
        self.assertEqual(12, self._events.call_count)
        self.assertEqual('ball_will_end', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ending', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_turn_will_end', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual('player_turn_ending', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('player_turn_ended', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual('player_turn_will_start', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual('player_turn_starting', self._events.call_args_list[7][1]['event_name'])
        self.assertEqual('player_turn_started', self._events.call_args_list[8][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[8][1]['number'])
        self.assertEqual('ball_will_start', self._events.call_args_list[9][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[10][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[10][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[10][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[11][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[11][1]['ball'])
        self._events.reset_mock()

        # Drain the second ball (player 1)
        self.drain_all_balls()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(2)
        self.assertBallNumber(2)

        # Assert ball drain, next ball start sequence
        self.assertEqual(12, self._events.call_count)
        self.assertEqual('ball_will_end', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ending', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_turn_will_end', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual('player_turn_ending', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('player_turn_ended', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual('player_turn_will_start', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual('player_turn_starting', self._events.call_args_list[7][1]['event_name'])
        self.assertEqual('player_turn_started', self._events.call_args_list[8][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[8][1]['number'])
        self.assertEqual('ball_will_start', self._events.call_args_list[9][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[10][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[10][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[10][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[11][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[11][1]['ball'])
        self._events.reset_mock()

        # Player 2 earns extra ball before draining
        self.machine.game.player.extra_balls += 1

        # Drain the ball (player 2 has earned an extra ball so it should still be
        # player 2's turn)
        self.drain_all_balls()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(2)
        self.assertBallNumber(2)

        # Assert ball drain, next ball sequence
        self.assertEqual(6, self._events.call_count)
        self.assertEqual('ball_will_end', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ending', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('ball_will_start', self._events.call_args_list[3][1]['event_name'])
        self.assertTrue(self._events.call_args_list[3][1]['is_extra_ball'])
        self.assertEqual('ball_starting', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[4][1]['balls_remaining'])
        self.assertTrue(self._events.call_args_list[4][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[5][1]['ball'])
        self._events.reset_mock()

        # Drain the second ball (player 2)
        self.drain_all_balls()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)

        # Assert ball drain, next ball start sequence
        self.assertEqual(12, self._events.call_count)
        self.assertEqual('ball_will_end', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ending', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_turn_will_end', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual('player_turn_ending', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('player_turn_ended', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual('player_turn_will_start', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual('player_turn_starting', self._events.call_args_list[7][1]['event_name'])
        self.assertEqual('player_turn_started', self._events.call_args_list[8][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[8][1]['number'])
        self.assertEqual('ball_will_start', self._events.call_args_list[9][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[10][1]['event_name'])
        self.assertEqual(0, self._events.call_args_list[10][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[10][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[11][1]['event_name'])
        self.assertEqual(3, self._events.call_args_list[11][1]['ball'])
        self._events.reset_mock()

        # Drain the third ball (player 1)
        self.drain_all_balls()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(2)
        self.assertBallNumber(3)

        # Assert ball drain, next ball start sequence
        self.assertEqual(12, self._events.call_count)
        self.assertEqual('ball_will_end', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ending', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_turn_will_end', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual('player_turn_ending', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('player_turn_ended', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual('player_turn_will_start', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual('player_turn_starting', self._events.call_args_list[7][1]['event_name'])
        self.assertEqual('player_turn_started', self._events.call_args_list[8][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[8][1]['number'])
        self.assertEqual('ball_will_start', self._events.call_args_list[9][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[10][1]['event_name'])
        self.assertEqual(0, self._events.call_args_list[10][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[10][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[11][1]['event_name'])
        self.assertEqual(3, self._events.call_args_list[11][1]['ball'])
        self._events.reset_mock()

        # Drain the third (and last) ball for player 2
        self.drain_all_balls()
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        # Assert ball drain, game ending sequence
        self.assertEqual(9, self._events.call_count)
        self.assertEqual('ball_will_end', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ending', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_turn_will_end', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual('player_turn_ending', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('player_turn_ended', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual('game_will_end', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual('game_ending', self._events.call_args_list[7][1]['event_name'])
        self.assertEqual('game_ended', self._events.call_args_list[8][1]['event_name'])

    def testGameEvents(self):
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices["bd_trough"].balls)

        self.post_event("start_my_game")
        self.assertGameIsRunning()
        self.advance_time_and_run()
        self.assertPlayerCount(1)
        self.post_event("start_my_game")
        self.assertPlayerCount(1)

        self.post_event("add_my_player")
        self.assertPlayerCount(2)
        self.post_event("add_my_player")
        self.assertPlayerCount(3)
        self.post_event("add_my_player")
        self.assertPlayerCount(4)
        self.post_event("add_my_player")
        self.assertPlayerCount(4)

    def event_handler_relay(self, **kwargs):
        return {'target': 'second_playfield'}

    def testPlayfieldRelayEvent(self):
        self.machine.events.add_handler('ball_start_target', self.event_handler_relay)
        second_playfield = self.machine.playfields['second_playfield']
        with patch.object(second_playfield, 'add_ball', wraps=second_playfield.add_ball) as wrapped_add_ball:
            self.machine.switch_controller.process_switch('s_ball_switch1', 1)
            self.machine.switch_controller.process_switch('s_ball_switch2', 1)
            self.advance_time_and_run(10)

            self.start_game()
            self.assertGameIsRunning()
            self.assertPlayerNumber(1)
            self.assertBallNumber(1)

            wrapped_add_ball.assert_called_with(player_controlled=True)

class TestGameLogic(MpfFakeGameTestCase):

    def testLastGameScore(self):
        # no previous scores
        self.assertFalse(self.machine.variables.is_machine_var("player1_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player2_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player3_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player4_score"))

        # four players
        self.start_game()
        self.add_player()
        self.add_player()
        self.add_player()
        self.machine.game.player.score = 100
        self.assertPlayerNumber(1)
        self.drain_all_balls()
        self.machine.game.player.score = 200
        self.assertPlayerNumber(2)
        self.drain_all_balls()
        self.machine.game.player.score = 0
        self.assertPlayerNumber(3)
        self.drain_all_balls()
        self.machine.game.player.score = 42
        self.assertPlayerNumber(4)

        # still old scores should not be set
        self.assertFalse(self.machine.variables.is_machine_var("player1_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player2_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player3_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player4_score"))

        self.stop_game()

        self.assertMachineVarEqual(100, "player1_score")
        self.assertMachineVarEqual(200, "player2_score")
        self.assertMachineVarEqual(0, "player3_score")
        self.assertMachineVarEqual(42, "player4_score")

        # two players
        self.start_game()
        self.add_player()
        self.machine.game.player.score = 100
        self.assertPlayerNumber(1)
        self.drain_all_balls()
        self.assertPlayerNumber(2)
        self.machine.game.player.score = 200
        self.drain_all_balls()
        # old scores should still be active
        self.assertMachineVarEqual(100, "player1_score")
        self.assertMachineVarEqual(200, "player2_score")
        self.assertMachineVarEqual(0, "player3_score")
        self.assertMachineVarEqual(42, "player4_score")
        self.stop_game()

        self.assertMachineVarEqual(100, "player1_score")
        self.assertMachineVarEqual(200, "player2_score")
        self.assertFalse(self.machine.variables.is_machine_var("player3_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player4_score"))

        # start one player game
        self.start_game()
        self.machine.game.player.score = 1337
        self.drain_all_balls()
        self.drain_all_balls()
        # still the old scores
        self.assertMachineVarEqual(100, "player1_score")
        self.assertMachineVarEqual(200, "player2_score")
        self.assertFalse(self.machine.variables.is_machine_var("player3_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player4_score"))
        self.drain_all_balls()
        self.assertGameIsNotRunning()

        self.assertMachineVarEqual(1337, "player1_score")
        self.assertFalse(self.machine.variables.is_machine_var("player2_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player3_score"))
        self.assertFalse(self.machine.variables.is_machine_var("player4_score"))
