from mpf.tests.MpfGameTestCase import MpfGameTestCase
from mpf.tests.MpfTestCase import test_config, test_config_directory


class TestTilt(MpfGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/tilt/'

    def get_platform(self):
        return 'smart_virtual'

    def _tilted(self, **kwargs):
        del kwargs
        self._is_tilted = True

    def _prepare_trough(self):
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(2)
        self.assertEqual(2, self.machine.ball_devices["bd_trough"].balls)

    def _add_tilt_handler(self):
        self._is_tilted = False
        self.machine.events.add_handler("tilt", self._tilted)

    @test_config("config_system_11_trough.yaml")
    def test_tilt_in_outhole(self):
        """Test that the ball does not stay in the outhole."""
        self._add_tilt_handler()

        self._prepare_trough()
        self.start_game(2)
        self.advance_time_and_run(10)

        self.assertBallsOnPlayfield(0)
        self.assertAvailableBallsOnPlayfield(1)
        self.assertEqual(1, self.machine.ball_devices["bd_plunger"].balls)

        # ball ejects and ends up on playfield
        self.release_switch_and_run("s_plunger", 10)
        self.assertBallsOnPlayfield(1)
        self.assertAvailableBallsOnPlayfield(1)

        # machine tilts
        self.assertFalse(self._is_tilted)
        self.hit_and_release_switch("s_tilt")
        self.advance_time_and_run(10)
        self.assertTrue(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(True, self.machine.game.tilted)
        self.assertEqual(0, self.machine.ball_devices["bd_outhole"].balls)
        self.assertEqual(0, self.machine.ball_devices["bd_plunger"].balls)
        self.assertBallsOnPlayfield(1)
        self.assertAvailableBallsOnPlayfield(1)

        # ball drains and gets kicked to trough
        self.machine.switch_controller.process_switch('s_outhole', 1)
        self.advance_time_and_run(20)
        self.assertEqual(0, self.machine.ball_devices["bd_outhole"].balls)

        self.assertEqual(False, self.machine.game.tilted)

    @test_config("config_mechanical_eject.yaml")
    def test_mechanical_eject(self):
        """Test that tilt triggers auto launch."""
        self._add_tilt_handler()

        self._prepare_trough()
        self.start_game(2)

        self.assertBallsOnPlayfield(0)
        self.assertAvailableBallsOnPlayfield(1)
        self.assertEqual(1, self.machine.ball_devices["bd_launcher"].balls)

        self.assertFalse(self._is_tilted)
        self.machine.switch_controller.process_switch('s_tilt', 1)
        self.machine.switch_controller.process_switch('s_tilt', 0)
        self.advance_time_and_run(10)
        self.assertTrue(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(True, self.machine.game.tilted)

        # ball ejects
        self.assertBallsOnPlayfield(1)
        self.assertAvailableBallsOnPlayfield(1)
        self.assertEqual(0, self.machine.ball_devices["bd_launcher"].balls)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        self.assertEqual(False, self.machine.game.tilted)

    def test_simple_tilt(self):
        self._add_tilt_handler()

        self._prepare_trough()
        self.start_game(2)

        # flipper actived
        self.assertTrue(self.machine.flippers["f_test"]._enabled)

        self.assertTrue(self.machine.mode_controller.is_active('tilt'))
        self.assertNotEqual(None, self.machine.game)

        # scoring should work
        self.post_event("test_scoring")
        self.assertPlayerVarEqual(100, "score")

        self.assertFalse(self._is_tilted)
        self.machine.switch_controller.process_switch('s_tilt', 1)
        self.machine.switch_controller.process_switch('s_tilt', 0)
        self.advance_time_and_run(1)
        self.assertTrue(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(True, self.machine.game.tilted)

        # flipper deactived
        self.assertFalse(self.machine.flippers["f_test"]._enabled)

        # scoring should no longer work
        self.assertPlayerVarEqual(100, "score")
        self.post_event("test_scoring")
        self.assertPlayerVarEqual(100, "score")

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        self.assertEqual(False, self.machine.game.tilted)

    def test_tilt_event(self):
        self._add_tilt_handler()

        self._prepare_trough()
        self.start_game(2)

        self.assertTrue(self.machine.mode_controller.is_active('tilt'))

        self.assertFalse(self._is_tilted)
        self.machine.events.post("tilt_event")
        self.advance_time_and_run(1)
        self.machine.events.post("tilt_event")
        self.advance_time_and_run(1)
        self.machine.events.post("tilt_event")
        self.advance_time_and_run(1)

        self.assertTrue(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(True, self.machine.game.tilted)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        self.assertEqual(False, self.machine.game.tilted)

    def test_simple_tilt_ball_not_on_pf_yet(self):
        self._add_tilt_handler()

        self._prepare_trough()
        self.start_game(2)

        self.assertTrue(self.machine.mode_controller.is_active('tilt'))
        self.assertNotEqual(None, self.machine.game)

        self.assertFalse(self._is_tilted)
        self.machine.switch_controller.process_switch('s_tilt', 1)
        self.machine.switch_controller.process_switch('s_tilt', 0)
        self.advance_time_and_run(.1)
        self.assertTrue(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(True, self.machine.game.tilted)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        self.assertEqual(False, self.machine.game.tilted)

    def test_tilt_warning(self):
        self._add_tilt_handler()

        self._prepare_trough()
        self.start_game(2)

        self.assertTrue(self.machine.mode_controller.is_active('tilt'))

        self.assertFalse(self._is_tilted)
        self.assertPlaceholderEvaluates(3, "mode.tilt.tilt_warnings_remaining")

        # multiple hits in 300ms window
        self.machine.switch_controller.process_switch('s_tilt_warning', 1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 0)
        self.advance_time_and_run(1)
        self.assertFalse(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)
        self.assertPlaceholderEvaluates(2, "mode.tilt.tilt_warnings_remaining")

        self.machine.switch_controller.process_switch('s_tilt_warning', 1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 0)
        self.advance_time_and_run(1)
        self.assertFalse(self._is_tilted)
        self.assertNotEqual(None, self.machine.game)
        self.assertPlaceholderEvaluates(1, "mode.tilt.tilt_warnings_remaining")

        self.machine.switch_controller.process_switch('s_tilt_warning', 1)
        self.machine.switch_controller.process_switch('s_tilt_warning', 0)
        self.advance_time_and_run(1)
        self.assertTrue(self._is_tilted)
        self.assertPlaceholderEvaluates(0, "mode.tilt.tilt_warnings_remaining")
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(True, self.machine.game.tilted)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)
        self.assertPlaceholderEvaluates(3000.0, "mode.tilt.tilt_settle_ms_remaining")

        # wait for settle time (5s) since last s_tilt_warning hit
        self.advance_time_and_run(3.5)
        self.assertEqual(False, self.machine.game.tilted)

    def test_slam_tilt(self):
        self._add_tilt_handler()

        self._prepare_trough()

        self.assertEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices["bd_trough"].balls)
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.advance_time_and_run(10)

        # flipper actived
        self.assertTrue(self.machine.flippers["f_test"]._enabled)

        self.assertTrue(self.machine.mode_controller.is_active('tilt'))
        self.assertNotEqual(None, self.machine.game)

        self.assertFalse(self._is_tilted)
        self.machine.switch_controller.process_switch('s_slam_tilt', 1)
        self.machine.switch_controller.process_switch('s_slam_tilt', 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)

        # flipper deactived
        self.assertFalse(self.machine.flippers["f_test"]._enabled)

        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        self.assertEqual(None, self.machine.game)

        # test that it does not crash outside the game
        self.post_event("tilt_reset_warnings")
        self.advance_time_and_run()

    def test_carry_over_multiple_player(self):
        self._add_tilt_handler()
        self._prepare_trough()
        self.start_two_player_game()

        self.advance_time_and_run(10)
        self.assertBallsOnPlayfield(1)
        self.assertPlayerVarEqual(0, "tilt_warnings")

        # tilt machine
        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertFalse(self._is_tilted)
        self.assertPlayerVarEqual(1, "tilt_warnings")
        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertFalse(self._is_tilted)
        self.assertPlayerVarEqual(2, "tilt_warnings")

        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertTrue(self._is_tilted)
        self.assertPlayerVarEqual(3, "tilt_warnings")

        # tilt_warnings player var no longer increases because machine is tilted
        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertPlayerVarEqual(3, "tilt_warnings")
        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertPlayerVarEqual(3, "tilt_warnings")
        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertPlayerVarEqual(3, "tilt_warnings")
        self.assertPlayerNumber(1)

        self.drain_one_ball()
        self.advance_time_and_run(10)
        self.assertPlayerNumber(2)
        self.assertPlayerVarEqual(0, "tilt_warnings")
        self._is_tilted = False

        self.assertBallsOnPlayfield(1)

        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertPlayerVarEqual(1, "tilt_warnings")
        self.assertFalse(self._is_tilted)

    @test_config_directory("tests/machine_files/tilt_defaults/")
    def test_carry_over_single_player(self):
        self._add_tilt_handler()
        self._prepare_trough()
        self.start_game()

        self.advance_time_and_run(10)
        self.assertBallsOnPlayfield(1)
        self.assertPlayerVarEqual(0, "tilt_warnings")

        # tilt machine
        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertFalse(self._is_tilted)
        self.assertPlayerVarEqual(1, "tilt_warnings")
        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertFalse(self._is_tilted)
        self.assertPlayerVarEqual(2, "tilt_warnings")

        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertTrue(self._is_tilted)
        self.assertPlayerVarEqual(0, "tilt_warnings")

        # tilt_warnings player var no longer increases because machine is tilted
        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertPlayerVarEqual(0, "tilt_warnings")

        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertPlayerVarEqual(0, "tilt_warnings")
        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertPlayerVarEqual(0, "tilt_warnings")
        self.assertPlayerNumber(1)

        # advance to ball 2
        self.drain_one_ball()
        self.advance_time_and_run(10)
        self.assertPlayerNumber(1)

        self._is_tilted = False

        self.assertBallNumber(2)
        self.assertBallsOnPlayfield(1)
        self.assertPlayerVarEqual(0, "tilt_warnings")

        # generate tilt warning and ensure no carry over from previous ball
        self.hit_and_release_switch("s_tilt_warning")
        self.advance_time_and_run(2)
        self.assertPlayerVarEqual(1, "tilt_warnings")
        self.assertFalse(self._is_tilted)
