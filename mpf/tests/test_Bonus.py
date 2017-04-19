"""Test the bonus mode."""
from mpf.tests.MpfTestCase import MpfTestCase, MagicMock


class TestBonusMode(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/bonus/'

    def _start_game(self):
        self.machine.playfield.add_ball = MagicMock()
        self.machine.ball_controller.num_balls_known = 3
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertIsNotNone(self.machine.game)

    def _stop_game(self):
        # stop game
        self.assertIsNotNone(self.machine.game)
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertIsNone(self.machine.game)

    def testBonus(self):
        self.mock_event("bonus_ramps")
        self.mock_event("bonus_modes")
        self.mock_event("bonus_subtotal")
        self.mock_event("bonus_multiplier")
        self.mock_event("bonus_total")
        # start game
        self._start_game()

        self.post_event("start_mode1")
        self.advance_time_and_run()
        self.assertTrue(self.machine.mode_controller.is_active('mode1'))

        # player gets some score
        self.post_event("hit_target")

        # score 3 ramp shots
        self.post_event("score_ramps")
        self.post_event("score_ramps")
        self.post_event("score_ramps")

        # score 2 modes
        self.post_event("score_modes")
        self.post_event("score_modes")

        # increase multiplier to 5 (by hitting it 4 times)
        self.post_event("add_multiplier")
        self.post_event("add_multiplier")
        self.post_event("add_multiplier")
        self.post_event("add_multiplier")
        self.advance_time_and_run()

        # drain a ball
        self.machine.game.balls_in_play = 0
        self.advance_time_and_run(1)

        # check that bonus mode is loaded
        self.assertModeRunning('bonus')
        self.advance_time_and_run(29)
        self.assertEqual(3000, self._last_event_kwargs["bonus_ramps"]["score"])
        self.assertEqual(3, self._last_event_kwargs["bonus_ramps"]["hits"])
        self.assertEqual(10000, self._last_event_kwargs["bonus_modes"]["score"])
        self.assertEqual(2, self._last_event_kwargs["bonus_modes"]["hits"])
        self.assertEqual(13000, self._last_event_kwargs["bonus_subtotal"]["score"])
        self.assertEqual(5, self._last_event_kwargs["bonus_multiplier"]["multiplier"])
        self.assertEqual(65000, self._last_event_kwargs["bonus_total"]["score"])
        self.assertEqual(66337, self.machine.game.player.score)

        # check resets
        self.assertEqual(0, self.machine.game.player.ramps)
        self.assertEqual(2, self.machine.game.player.modes)
        self.assertEqual(5, self.machine.game.player.bonus_multiplier)

        # make some changes for the next test
        self.machine.modes.bonus.config['mode_settings']['keep_multiplier'] = False

        # drain a ball
        self.machine.game.balls_in_play = 0
        self.advance_time_and_run(30)

        self.assertEqual(0, self._last_event_kwargs["bonus_ramps"]["score"])
        self.assertEqual(0, self._last_event_kwargs["bonus_ramps"]["hits"])
        self.assertEqual(10000, self._last_event_kwargs["bonus_modes"]["score"])
        self.assertEqual(2, self._last_event_kwargs["bonus_modes"]["hits"])
        self.assertEqual(10000, self._last_event_kwargs["bonus_subtotal"]["score"])
        self.assertEqual(5, self._last_event_kwargs["bonus_multiplier"]["multiplier"])
        self.assertEqual(50000, self._last_event_kwargs["bonus_total"]["score"])
        self.assertEqual(116337, self.machine.game.player.score)

        # multiplier should reset
        self.assertEqual(0, self.machine.game.player.ramps)
        self.assertEqual(2, self.machine.game.player.modes)
        self.assertEqual(1, self.machine.game.player.bonus_multiplier)

        # make some changes for the next test
        self.machine.modes.bonus.bonus_entries[0]['skip_if_zero'] = True
        self._last_event_kwargs = dict()

        # drain a ball
        self.machine.game.balls_in_play = 0
        self.advance_time_and_run(30)

        # this entry event should be skipped since player.ramps == 0
        self.assertNotIn('bonus_ramps', self._last_event_kwargs)

        # make some changes for the next test
        self.machine.game.player.ramps = 1
        self.machine.game.player.bonus_multiplier = 2

        # test the hurry up
        self.mock_event("bonus_start")
        self.mock_event("bonus_ramps")
        self.mock_event("bonus_modes")
        self.mock_event("bonus_subtotal")
        self.mock_event("bonus_multiplier")
        self.mock_event("bonus_total")

        # drain a ball
        self.machine.game.balls_in_play = 0
        self.advance_time_and_run(1)

        self.assertEventCalled('bonus_start')
        self.assertEventNotCalled('bonus_ramps')
        self.assertEventNotCalled('bonus_modes')
        self.assertEventNotCalled('bonus_subtotal')
        self.assertEventNotCalled('bonus_multiplier')
        self.assertEventNotCalled('bonus_total')

        self.advance_time_and_run(2)

        self.assertEventCalled('bonus_ramps')
        self.assertEventNotCalled('bonus_modes')
        self.assertEventNotCalled('bonus_subtotal')
        self.assertEventNotCalled('bonus_multiplier')
        self.assertEventNotCalled('bonus_total')

        self.post_event('flipper_cancel', .1)
        self.assertEventCalled('bonus_modes')
        self.assertEventNotCalled('bonus_subtotal')
        self.assertEventNotCalled('bonus_multiplier')
        self.assertEventNotCalled('bonus_total')

        self.advance_time_and_run(.5)
        self.assertEventCalled('bonus_subtotal')
        self.assertEventNotCalled('bonus_multiplier')
        self.assertEventNotCalled('bonus_total')

        self.advance_time_and_run(.5)
        self.assertEventCalled('bonus_multiplier')
        self.assertEventNotCalled('bonus_total')

        self.advance_time_and_run(.5)
        self.assertEventCalled('bonus_total')

        # test multiplier screens are skipped if multiplier is 1
        self.advance_time_and_run(30)
        self.machine.game.player.bonus_multiplier = 1
        self.machine.game.player.ramps = 1

        # test the hurry up
        self.mock_event("bonus_start")
        self.mock_event("bonus_ramps")
        self.mock_event("bonus_modes")
        self.mock_event("bonus_subtotal")
        self.mock_event("bonus_multiplier")
        self.mock_event("bonus_total")

        # drain a ball
        self.machine.game.balls_in_play = 0
        self.advance_time_and_run(30)

        self.assertEventCalled('bonus_start')
        self.assertEventCalled('bonus_ramps')
        self.assertEventCalled('bonus_modes')
        self.assertEventNotCalled('bonus_subtotal')
        self.assertEventNotCalled('bonus_multiplier')
        self.assertEventCalled('bonus_total')

    def testBonusTilted(self):
        self.mock_event("bonus_ramps")
        self.mock_event("bonus_modes")
        self.mock_event("bonus_subtotal")
        self.mock_event("bonus_multiplier")
        self.mock_event("bonus_total")
        # start game
        self._start_game()

        self.post_event("start_mode1")
        self.advance_time_and_run()

        # player gets some score
        self.post_event("hit_target")

        # score 3 ramp shots
        self.post_event("score_ramps")
        self.post_event("score_ramps")
        self.post_event("score_ramps")

        # score 2 modes
        self.post_event("score_modes")
        self.post_event("score_modes")

        # increase multiplier to 5 (by hitting it 4 times)
        self.post_event("add_multiplier")
        self.post_event("add_multiplier")
        self.post_event("add_multiplier")
        self.post_event("add_multiplier")
        self.advance_time_and_run()

        # tilt the game
        self.machine.game.tilted = True

        # drain a ball
        self.machine.game.balls_in_play = 0
        self.advance_time_and_run(30)
        self.assertEqual(1337, self.machine.game.player.score)

        # check resets
        self.assertEqual(0, self.machine.game.player.ramps)
        self.assertEqual(2, self.machine.game.player.modes)
        self.assertEqual(5, self.machine.game.player.bonus_multiplier)
