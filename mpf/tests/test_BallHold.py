from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallHold(MpfTestCase):

    def getConfigFile(self):
        return 'test_ball_holds.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_holds/'

    def _missing_ball(self, **kwargs):
        del kwargs
        self._missing += 1

    def _ball_enter(self, new_balls, unclaimed_balls, **kwargs):
        del unclaimed_balls
        del kwargs
        self._enter += new_balls

    def _captured_from_pf(self, balls, **kwargs):
        del kwargs
        self._captured += balls

    def _collecting_balls_complete_handler(self, **kwargs):
        del kwargs
        self._collecting_balls_complete = 1

    def test_ball_hold_in_mode(self):
        # start mode
        self.post_event("start_mode1")

        # mode loaded. ball_hold2 should be enabled
        self.assertTrue(self.machine.ball_holds.hold_test2.enabled)

        # stop mode
        self.post_event("stop_mode1")

        # mode stopped. should ball_hold be disabled
        self.assertFalse(self.machine.ball_holds.hold_test2.enabled)

        # start mode (again)
        self.post_event("start_mode1")

        # mode loaded. ball_hold2 should be enabled
        self.assertTrue(self.machine.ball_holds.hold_test2.enabled)

        # stop mode
        self.post_event("stop_mode1")

        # mode stopped. should ball_hold be disabled
        self.assertFalse(self.machine.ball_holds.hold_test2.enabled)

    def test_hold_and_release_at_game_end(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        trough = self.machine.ball_devices['test_trough']
        launcher = self.machine.ball_devices['test_launcher']
        hold = self.machine.ball_devices['test_hold']
        hold_logic = self.machine.ball_holds['hold_test']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing', self._missing_ball)

        self._enter = 0
        self._captured = 0
        self._missing = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEqual(2, trough.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # start a game
        self.machine.switch_controller.process_switch("s_start", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)

        # trough ejects
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, trough.balls)

        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, launcher.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, launcher.balls)

        self.machine.switch_controller.process_switch("s_playfield_active", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield_active", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        self.mock_event("yes")
        self.mock_event("no")
        self.post_event("test_conditional_event")
        self.assertEventCalled("no")
        self.assertEventNotCalled("yes")

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        # ball enters hold
        self.machine.switch_controller.process_switch("s_ball_switch_hold1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, hold.balls)

        self.mock_event("yes")
        self.mock_event("no")
        self.post_event("test_conditional_event")
        self.assertEventNotCalled("no")
        self.assertEventCalled("yes")

        # request another ball
        self.machine.playfield.add_ball(1)
        self.advance_time_and_run()

        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)
        self.assertEqual(1, hold_logic.balls_held)
        self._captured = 0

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, trough.balls)

        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, launcher.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, launcher.balls)

        self.machine.switch_controller.process_switch("s_playfield_active", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield_active", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        # ball drains
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)
        self._captured = 0
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # hold should eject all balls
        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        self.assertTrue(coil3.pulse.called)

        self.machine.switch_controller.process_switch("s_ball_switch_hold1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, hold.balls)
        self.assertEqual(0, hold_logic.balls_held)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)
        # game did not end because ball has not drained
        self.assertIsNotNone(self.machine.game)

        # ball also drains
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        # game ends
        self.assertIsNone(self.machine.game)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)

        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        self.advance_time_and_run(100)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)

        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

    def test_hold_full_and_release(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        trough = self.machine.ball_devices['test_trough']
        hold = self.machine.ball_devices['test_hold']
        hold_logic = self.machine.ball_holds['hold_test']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing', self._missing_ball)
        self.machine.events.add_handler('collecting_balls_complete', self._collecting_balls_complete_handler)

        hold_logic.enable()

        self._enter = 0
        self._captured = 0
        self._missing = 0
        self._collecting_balls_complete = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEqual(2, trough.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        self.assertFalse(hold_logic.is_full())
        self.assertEqual(2, trough.available_balls)

        # hold captures a first random ball
        self.machine.switch_controller.process_switch("s_ball_switch_hold1", 1)
        self.advance_time_and_run(1)
        assert not coil3.pulse.called
        self.assertFalse(hold_logic.is_full())

        # self.assertEqual(1, trough.available_balls)
        self.assertEqual(1, hold.available_balls)

        # hold captures a second random ball
        self.machine.switch_controller.process_switch("s_ball_switch_hold2", 1)
        self.advance_time_and_run(1)
        assert not coil3.pulse.called
        self.assertTrue(hold_logic.is_full())
        # self.assertEqual(0, trough.available_balls)
        self.assertEqual(2, hold.available_balls)

        # hold captures a third random ball
        self.machine.switch_controller.process_switch("s_ball_switch_hold3", 1)
        self.advance_time_and_run(1)

        # it should eject it right away
        self.assertTrue(coil3.pulse.called)
        coil3.pulse = MagicMock()
        self.assertTrue(hold_logic.is_full())
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_ball_switch_hold3", 0)
        self.advance_time_and_run(11)
        self.assertTrue(hold_logic.is_full())
        self.assertEqual(2, hold.available_balls)

        hold_logic.release_all()
        self.advance_time_and_run(1)
        self.assertEqual(0, hold.available_balls)
        self.assertTrue(coil3.pulse.called)
        coil3.pulse = MagicMock()
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("s_ball_switch_hold2", 0)
        self.advance_time_and_run(1)
        self.assertFalse(hold_logic.is_full())

        self.advance_time_and_run(11)
        self.assertTrue(coil3.pulse.called)
        coil3.pulse = MagicMock()
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("s_ball_switch_hold1", 0)
        self.advance_time_and_run(11)
        assert not coil3.pulse.called

    def test_eject_to_hold(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        trough = self.machine.ball_devices['test_trough']
        launcher = self.machine.ball_devices['test_launcher']
        hold = self.machine.ball_devices['test_hold']
        hold_logic = self.machine.ball_holds['hold_test']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing', self._missing_ball)
        self.machine.events.add_handler('collecting_balls_complete', self._collecting_balls_complete_handler)

        self._enter = 0
        self._captured = 0
        self._missing = 0
        self._collecting_balls_complete = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEqual(2, trough.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # start a game
        self.machine.switch_controller.process_switch("s_start", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)

        # trough ejects
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, trough.balls)

        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, launcher.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, launcher.balls)

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        # ball directly enters the hold
        self.machine.switch_controller.process_switch("s_ball_switch_hold1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, hold.balls)

        # request another ball
        self.machine.playfield.add_ball(1)
        self.advance_time_and_run()

        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)
        self.assertEqual(1, hold_logic.balls_held)
        self._captured = 0

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, trough.balls)

        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, launcher.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, launcher.balls)

        self.machine.switch_controller.process_switch("s_playfield_active", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield_active", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)
        self.assertEqual(1, hold.available_balls)

        # request a release of one ball from hold via event
        self.machine.events.post("release_test")
        # since we are not using a multi ball increase the balls_in_play manually
        self.assertEqual(1, self.machine.game.balls_in_play)
        self.machine.game.balls_in_play += 1
        self.advance_time_and_run(1)

        # hold should eject a ball
        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        self.assertTrue(coil3.pulse.called)

        self.machine.switch_controller.process_switch("s_ball_switch_hold1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, hold.balls)
        self.assertEqual(0, hold_logic.balls_held)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        # ball drains instantly. one left on pf
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.game.balls_in_play)

        # other ball hits some pf switches
        self.machine.switch_controller.process_switch("s_playfield_active", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield_active", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)
        self._captured = 0
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        self.assertEqual(0, self._collecting_balls_complete)
        self.assertEqual(1, self.machine.game.balls_in_play)

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        # we add another ball
        self.machine.game.balls_in_play += 1
        playfield.add_ball()
        self.advance_time_and_run(1)
        self.assertEqual(2, self.machine.game.balls_in_play)

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, trough.balls)

        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, launcher.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, launcher.balls)

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        # ball directly enters the hold (again)
        self.machine.switch_controller.process_switch("s_ball_switch_hold1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, hold.balls)

        # playfield count goes to 0
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)
        self._captured = 0

        # wait for eject confirm for hold
        self.advance_time_and_run(10)

        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        self.advance_time_and_run(100)
        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

    def test_auto_capacity(self):
        self.assertEqual(self.machine.ball_holds.hold_test3.config['balls_to_hold'], 2)

class TestBallHoldSmart(MpfTestCase):

    def getConfigFile(self):
        return 'test_ball_holds.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_holds/'

    def get_platform(self):
        return 'smart_virtual'

    def test_ball_end(self):
        self.machine.config['game']['balls_per_game'] = self.machine.placeholder_manager.build_int_template(3)
        # add an initial ball to trough
        self.hit_switch_and_run("s_ball_switch1", 1)
        self.hit_switch_and_run("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.playfield.balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # press start
        self.hit_and_release_switch("s_start")

        # wait until ball is on pf
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.game.player.ball)
        self.assertEqual(1, self.machine.playfield.balls)

        # hold one ball
        self.machine.ball_holds.hold_test.enable()
        self.hit_switch_and_run("s_ball_switch_hold1", 1)

        # still held
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_holds.hold_test.balls_held)
        self.assertEqual(0, self.machine.playfield.balls)

        # request another ball
        self.machine.playfield.add_ball(1)
        self.advance_time_and_run()
        self.hit_and_release_switch('s_playfield_active')
        self.advance_time_and_run()
        self.assertEqual(1, self.machine.playfield.balls)

        # drain ball on pf
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.test_trough)
        self.advance_time_and_run(1)

        # machine waits for the hold
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.game.player.ball)

        # release the hold
        self.post_event('release_test')
        self.assertEqual(0, self.machine.ball_holds.hold_test.balls_held)
        self.assertEqual(1, self.machine.playfield.balls)

        # once the ball drains move on to the ball 2
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.test_trough)
        self.advance_time_and_run(1)
        self.assertEqual(2, self.machine.game.player.ball)

        # next ball
        self.advance_time_and_run(10)
        self.assertBallsOnPlayfield(1)

        # drain again
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.test_trough)
        self.advance_time_and_run(1)

        # there should be no hold this time
        self.assertEqual(3, self.machine.game.player.ball)
