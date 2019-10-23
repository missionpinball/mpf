from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestTooLongExitCountDelay(MpfTestCase):

    def get_config_file(self):
        return 'test_too_long_exit_count_delay.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def _ball_drained(self, **kwargs):
        del kwargs
        self._num_balls_drained += 1

    def put_four_balls_in_trough(self):
        self.machine.switch_controller.process_switch('s_trough_1', 1)
        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.playfield.balls)

        self.trough_coil = self.machine.coils["trough_eject"]
        self.plunger_coil = self.machine.coils["plunger_eject"]

        self.trough_coil.pulse = MagicMock()
        self.plunger_coil.pulse = MagicMock()

        self._num_balls_drained = 0
        self.machine.events.add_handler('ball_drained', self._ball_drained)

    def test_eject_to_plunger(self):
        # tests eject from trough to plunger where the ball enters the plunger
        # before the exit_count_delay of the trough

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # default pulse
        self.assertTrue(self.trough_coil.pulse.called)
        self.trough_coil.pulse = MagicMock()

        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.machine.switch_controller.process_switch('s_trough_2', 0)
        self.machine.switch_controller.process_switch('s_trough_3', 0)
        self.machine.switch_controller.process_switch('s_trough_4', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(.1)

        # ball goes into plunger
        self.machine.switch_controller.process_switch('s_plunger', 1)
        self.advance_time_and_run(1)

        self.assertEqual(self.machine.ball_devices["trough"].balls, 3)
        self.assertEqual(self.machine.ball_devices["plunger"].balls, 1)
        assert not self.plunger_coil.pulse.called
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("ejecting", self.machine.ball_devices["plunger"]._state)

        # player hits the launch button
        self.machine.switch_controller.process_switch('s_launch', 1)
        self.machine.switch_controller.process_switch('s_launch', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_plunger', 0)
        self.advance_time_and_run(1)

        # ball moves from plunger lane to playfield
        self.machine.switch_controller.process_switch('s_playfield', 1)
        self.machine.switch_controller.process_switch('s_playfield', 0)
        self.advance_time_and_run(.1)

        self.assertTrue(self.plunger_coil.pulse.called)
        self.assertEqual(self.machine.ball_devices["trough"].balls, 3)
        self.assertEqual(self.machine.ball_devices["plunger"].balls, 0)
        self.assertEqual(self.machine.ball_devices["playfield"].balls, 1)
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("idle", self.machine.ball_devices["plunger"]._state)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

    def test_ball_fell_back_in_trough_before_exit_count_delay(self):
        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # default pulse
        self.assertTrue(self.trough_coil.pulse.called)
        self.trough_coil.pulse = MagicMock()

        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.machine.switch_controller.process_switch('s_trough_2', 0)
        self.machine.switch_controller.process_switch('s_trough_3', 0)
        self.machine.switch_controller.process_switch('s_trough_4', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(.2)

        # ball falls back in trough
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.advance_time_and_run(2)

        self.assertEqual(self.machine.ball_devices["trough"].balls, 3)
        self.assertEqual(self.machine.ball_devices["plunger"].balls, 0)
        self.assertEqual(self.machine.ball_devices["playfield"].balls, 0)

        # after the eject timeout, the trough will realize it has a ball
        self.advance_time_and_run(10)
        self.assertEqual(self.machine.ball_devices["trough"].balls, 4)
