from mpf.tests.MpfGameTestCase import MpfGameTestCase
from unittest.mock import MagicMock, call


class TestGame(MpfGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/game/'

    def get_platform(self):
        return 'smart_virtual'

    def testSinglePlayerGame(self):
        # setup event callbacks
        self._events = MagicMock()
        self.machine.events.add_handler('game_start', self._events, event_name='game_start')
        self.machine.events.add_handler('game_starting', self._events, event_name='game_starting')
        self.machine.events.add_handler('player_add_request', self._events, event_name='player_add_request')
        self.machine.events.add_handler('player_add_success', self._events, event_name='player_add_success')
        self.machine.events.add_handler('player_turn_start', self._events, event_name='player_turn_start')
        self.machine.events.add_handler('game_started', self._events, event_name='game_started')
        self.machine.events.add_handler('ball_starting', self._events, event_name='ball_starting')
        self.machine.events.add_handler('ball_started', self._events, event_name='ball_started')
        self.machine.events.add_handler('ball_ending', self._events, event_name='ball_ending')
        self.machine.events.add_handler('ball_ended', self._events, event_name='ball_ended')
        self.machine.events.add_handler('game_ending', self._events, event_name='game_ending')
        self.machine.events.add_handler('game_ended', self._events, event_name='game_ended')

        # prepare game
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        # start game (single player)
        self.start_game()
        self.assertGameIsRunning()
        self.assertPlayerNumber(1)
        self.assertBallNumber(1)

        self.assertEqual(3, self.machine.modes.game.balls_per_game)

        # Assert game startup sequence
        self.assertEqual(7, self._events.call_count)
        self.assertEqual('game_start', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('game_starting', self._events.call_args_list[1][1]['event_name'])
        # self.assertEqual('player_add_request', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('player_add_success', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[2][1]['num'])
        self.assertEqual('player_turn_start', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[3][1]['number'])
        self.assertEqual('game_started', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[5][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[5][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[6][1]['ball'])
        self.assertEqual(1, self._events.call_args_list[6][1]['player'])
        self._events.reset_mock()

        # Drain the first ball
        self.drain_ball()
        self.advance_time_and_run()
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)

        # Assert ball drain, next ball start sequence
        self.assertEqual(5, self._events.call_count)
        self.assertEqual('ball_ending', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('player_turn_start', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[2][1]['number'])
        self.assertEqual('ball_starting', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[3][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[3][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[4][1]['ball'])
        self._events.reset_mock()

        # Drain the second ball
        self.drain_ball()
        self.advance_time_and_run()
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)

        # Assert ball drain, next ball start sequence
        self.assertEqual(5, self._events.call_count)
        self.assertEqual('ball_ending', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('player_turn_start', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[2][1]['number'])
        self.assertEqual('ball_starting', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual(0, self._events.call_args_list[3][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[3][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual(3, self._events.call_args_list[4][1]['ball'])
        self._events.reset_mock()

        # Drain the third (and last) ball
        self.drain_ball()
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        # Assert ball drain, game ending sequence
        self.assertEqual(4, self._events.call_count)
        self.assertEqual('ball_ending', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('game_ending', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('game_ended', self._events.call_args_list[3][1]['event_name'])

    def testMultiplePlayerGame(self):
        # setup event callbacks
        self._events = MagicMock()
        self.machine.events.add_handler('game_start', self._events, event_name='game_start')
        self.machine.events.add_handler('game_starting', self._events, event_name='game_starting')
        self.machine.events.add_handler('player_add_request', self._events, event_name='player_add_request')
        self.machine.events.add_handler('player_add_success', self._events, event_name='player_add_success')
        self.machine.events.add_handler('player_turn_start', self._events, event_name='player_turn_start')
        self.machine.events.add_handler('game_started', self._events, event_name='game_started')
        self.machine.events.add_handler('ball_starting', self._events, event_name='ball_starting')
        self.machine.events.add_handler('ball_started', self._events, event_name='ball_started')
        self.machine.events.add_handler('ball_ending', self._events, event_name='ball_ending')
        self.machine.events.add_handler('ball_ended', self._events, event_name='ball_ended')
        self.machine.events.add_handler('game_ending', self._events, event_name='game_ending')
        self.machine.events.add_handler('game_ended', self._events, event_name='game_ended')

        # prepare game
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        # start game (first player)
        self.start_game()
        self.advance_time_and_run(5)
        self.assertGameIsRunning()
        self.assertPlayerNumber(1)
        self.assertBallNumber(1)

        self.assertEqual(3, self.machine.modes.game.balls_per_game)

        # Assert game startup sequence
        self.assertEqual(7, self._events.call_count)
        self.assertEqual('game_start', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('game_starting', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('player_add_success', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[2][1]['num'])
        self.assertEqual('player_turn_start', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[3][1]['number'])
        self.assertEqual('game_started', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[5][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[5][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[5][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[6][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[6][1]['ball'])
        self.assertEqual(1, self._events.call_args_list[6][1]['player'])
        self._events.reset_mock()

        # add another player (player 2)
        self.add_player()

        # Assert game startup sequence
        self.assertEqual(2, self._events.call_count)
        self.assertEqual('player_add_request', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('player_add_success', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[1][1]['num'])
        self._events.reset_mock()

        # Drain the first ball (player 1)
        self.drain_ball()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(2)
        self.assertBallNumber(1)

        # Assert ball drain, next ball start sequence
        self.assertEqual(5, self._events.call_count)
        self.assertEqual('ball_ending', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('player_turn_start', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[2][1]['number'])
        self.assertEqual('ball_starting', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[3][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[3][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[4][1]['ball'])
        self._events.reset_mock()

        # Drain the first ball (player 2)
        self.drain_ball()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(1)
        self.assertBallNumber(2)

        # Assert ball drain, next ball start sequence
        self.assertEqual(5, self._events.call_count)
        self.assertEqual('ball_ending', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('player_turn_start', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[2][1]['number'])
        self.assertEqual('ball_starting', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[3][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[3][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[4][1]['ball'])
        self._events.reset_mock()

        # Drain the second ball (player 1)
        self.drain_ball()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(2)
        self.assertBallNumber(2)

        # Assert ball drain, next ball start sequence
        self.assertEqual(5, self._events.call_count)
        self.assertEqual('ball_ending', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('player_turn_start', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[2][1]['number'])
        self.assertEqual('ball_starting', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[3][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[3][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[4][1]['ball'])
        self._events.reset_mock()

        # Player 2 earns extra ball before draining
        self.machine.game.player.extra_balls += 1

        # Drain the ball (player 2 has earned an extra ball so it should still be
        # player 2's turn)
        self.drain_ball()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(2)
        self.assertBallNumber(2)

        # Assert ball drain, next ball sequence
        self.assertEqual(4, self._events.call_count)
        self.assertEqual('ball_ending', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('ball_starting', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[2][1]['balls_remaining'])
        self.assertTrue(self._events.call_args_list[2][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[3][1]['ball'])
        self._events.reset_mock()

        # Drain the second ball (player 2)
        self.drain_ball()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(1)
        self.assertBallNumber(3)

        # Assert ball drain, next ball start sequence
        self.assertEqual(5, self._events.call_count)
        self.assertEqual('ball_ending', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('player_turn_start', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual(1, self._events.call_args_list[2][1]['number'])
        self.assertEqual('ball_starting', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual(0, self._events.call_args_list[3][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[3][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual(3, self._events.call_args_list[4][1]['ball'])
        self._events.reset_mock()

        # Drain the third ball (player 1)
        self.drain_ball()
        self.advance_time_and_run(5)
        self.assertPlayerNumber(2)
        self.assertBallNumber(3)

        # Assert ball drain, next ball start sequence
        self.assertEqual(5, self._events.call_count)
        self.assertEqual('ball_ending', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('player_turn_start', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual(2, self._events.call_args_list[2][1]['number'])
        self.assertEqual('ball_starting', self._events.call_args_list[3][1]['event_name'])
        self.assertEqual(0, self._events.call_args_list[3][1]['balls_remaining'])
        self.assertFalse(self._events.call_args_list[3][1]['is_extra_ball'])
        self.assertEqual('ball_started', self._events.call_args_list[4][1]['event_name'])
        self.assertEqual(3, self._events.call_args_list[4][1]['ball'])
        self._events.reset_mock()

        # Drain the third (and last) ball for player 2
        self.drain_ball()
        self.advance_time_and_run()
        self.assertGameIsNotRunning()

        # Assert ball drain, game ending sequence
        self.assertEqual(4, self._events.call_count)
        self.assertEqual('ball_ending', self._events.call_args_list[0][1]['event_name'])
        self.assertEqual('ball_ended', self._events.call_args_list[1][1]['event_name'])
        self.assertEqual('game_ending', self._events.call_args_list[2][1]['event_name'])
        self.assertEqual('game_ended', self._events.call_args_list[3][1]['event_name'])
