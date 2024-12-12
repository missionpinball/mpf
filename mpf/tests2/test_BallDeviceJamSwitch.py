from mpf.tests.MpfTestCase import MpfTestCase, test_config
from unittest.mock import MagicMock


class TestBallDeviceJamSwitch(MpfTestCase):

    max_wait_ms = 200

    def get_config_file(self):
        return 'test_ball_device_jam_switch.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def _captured_from_pf(self, balls, **kwargs):
        del kwargs
        self._captured += balls

    def put_four_balls_in_trough(self):
        self._captured = 0
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.switch_controller.process_switch('s_trough_1', 1)
        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_devices["trough"].balls)
        self.assertEqual(4, self._captured)
        self._captured = 0

        self.trough_coil = self.machine.coils["trough_eject"]
        self.plunger_coil = self.machine.coils["plunger_eject"]

        self.trough_coil.pulse = MagicMock()
        self.plunger_coil.pulse = MagicMock()

    @test_config("test_ball_device_jam_switch_initial.yaml")
    def test_reorder_on_startup(self):
        # test reorder on startup with a jammed trough with no ball switches active
        self.assertEqual("pulsed_2", self.machine.coils["trough_eject"].hw_driver.state)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.advance_time_and_run(1)
        self.assertEqual(4, self.machine.ball_devices["trough"].balls)

    @test_config("test_jam_and_ball_left.yaml")
    def test_jam_and_ball_left(self):
        """Test that we properly track an eject when balls are jammed.

        This is a regression test for a bug we had.
        """
        # put a ball on the jam switch
        self.machine.switch_controller.process_switch('s_trough1', 1)
        self.advance_time_and_run(10)
        self.assertNumBallsKnown(1)

        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)

        self.advance_time_and_run(5)
        self.machine.switch_controller.process_switch('s_trough1', 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.advance_time_and_run(10)
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(1)

        # ball goes into plunger
        self.machine.switch_controller.process_switch('s_plunger_lane', 1)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch('s_plunger_lane', 0)
        self.advance_time_and_run(1)

        # ball moves from plunger lane to playfield
        self.machine.switch_controller.process_switch('s_playfield', 1)
        self.machine.switch_controller.process_switch('s_playfield', 0)
        self.advance_time_and_run(.1)
        self.assertBallsOnPlayfield(1)
        self.advance_time_and_run(10)
        self.assertEqual("idle", self.machine.ball_devices["bd_trough"]._state)
        self.assertEqual("idle", self.machine.ball_devices["bd_plunger"]._state)
        self.assertNumBallsKnown(1)
        self.assertBallsOnPlayfield(1)
        self.assertEqual("idle", self.machine.ball_devices["bd_trough"]._state)
        self.assertEqual("idle", self.machine.ball_devices["bd_plunger"]._state)

    @test_config("test_jam_and_ball_left.yaml")
    def test_jam_and_ball_return(self):
        """Test that we properly track an eject and return when balls are jammed.

        This is a regression test for a bug we had.
        """
        # put a ball on the jam switch
        self.machine.switch_controller.process_switch('s_trough1', 1)
        self.advance_time_and_run(10)
        self.assertNumBallsKnown(1)

        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)

        self.advance_time_and_run(5)
        self.machine.switch_controller.process_switch('s_trough1', 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.machine.switch_controller.process_switch('s_trough1', 1)
        self.advance_time_and_run(5.3)
        # ball goes into plunger
        self.machine.switch_controller.process_switch('s_plunger_lane', 1)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch('s_trough1', 0)
        self.advance_time_and_run(2)
        self.machine.switch_controller.process_switch('s_trough1', 1)
        self.advance_time_and_run(5)
        self.machine.switch_controller.process_switch('s_trough1', 0)
        self.advance_time_and_run(10)

        # the machine will be at an odd state here but it should not crash

    def test_eject_with_jam_switch(self):
        """Test the proper operation of a trough eject with a jam switch."""
        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # default pulse
        self.trough_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
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

        self.plunger_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
        self.assertEqual(self.machine.ball_devices["trough"].balls, 3)
        self.assertEqual(self.machine.ball_devices["plunger"].balls, 0)
        self.assertEqual(self.machine.ball_devices["playfield"].balls, 1)
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("idle", self.machine.ball_devices["plunger"]._state)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, self._captured)

    def test_eject_no_jam_switch_activity(self):
        # Jam switch is configured, but it is not activated when the ball
        # ejects

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # default pulse
        self.trough_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)

        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.machine.switch_controller.process_switch('s_trough_2', 0)
        self.machine.switch_controller.process_switch('s_trough_3', 0)
        self.machine.switch_controller.process_switch('s_trough_4', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        # self.machine.switch_controller.process_switch('s_trough_jam', 1)
        # self.machine.switch_controller.process_switch('s_trough_jam', 0)
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

        self.assertEqual(1, self.plunger_coil.pulse.called)
        self.assertEqual(self.machine.ball_devices["trough"].balls, 3)
        self.assertEqual(self.machine.ball_devices["plunger"].balls, 0)
        self.assertEqual(self.machine.ball_devices["playfield"].balls, 1)
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("idle", self.machine.ball_devices["plunger"]._state)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, self._captured)

    def test_eject_with_jam_all_balls_disappear(self):
        # Ball ejects and gets stuck on jam switch. All other balls shift a
        # half position and get stuck between switches, so it's like all the
        # balls just disappeared.

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # default pulse
        self.trough_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
        self.trough_coil.pulse = MagicMock(return_value=100)

        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.machine.switch_controller.process_switch('s_trough_2', 0)
        self.machine.switch_controller.process_switch('s_trough_3', 0)
        self.machine.switch_controller.process_switch('s_trough_4', 0)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.advance_time_and_run(11)

        # reorder balls
        self.trough_coil.pulse.assert_called_once_with(2, max_wait_ms=self.max_wait_ms)
        self.trough_coil.pulse = MagicMock(return_value=100)
        self.advance_time_and_run(.5)
        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.advance_time_and_run(2)

        # soft pulse to eject only the jammed ball
        self.trough_coil.pulse.assert_called_once_with(5, max_wait_ms=self.max_wait_ms)

        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 0)

        # ball goes into plunger
        self.machine.switch_controller.process_switch('s_plunger', 1)
        self.advance_time_and_run(1)

        self.advance_time_and_run(100)
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("ejecting", self.machine.ball_devices["plunger"]._state)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, self._captured)

    def test_eject_ball_stuck_in_jam_switch(self):
        # Ball ejects, gets stuck in jam switch

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # default pulse
        self.trough_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
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
        self.advance_time_and_run(.1)

        # wait for timeout
        self.advance_time_and_run(10)

        self.assertEqual(self.machine.ball_devices["trough"].balls, 4)
        self.assertEqual(self.machine.ball_devices["plunger"].balls, 0)

        # trough should retry softly
        self.trough_coil.pulse.assert_called_once_with(5, max_wait_ms=self.max_wait_ms)
        assert not self.plunger_coil.pulse.called
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(1)

        # ball goes into plunger
        self.machine.switch_controller.process_switch('s_plunger', 1)
        self.advance_time_and_run(1)

        self.advance_time_and_run(100)
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("ejecting", self.machine.ball_devices["plunger"]._state)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, self._captured)

    def test_eject_ball_falls_back_in(self):
        # Ball ejects, ball leaves with proper timeout, but ball falls back in

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        self.trough_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
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
        self.advance_time_and_run(1)

        # ball goes into plunger and comes back
        self.machine.switch_controller.process_switch('s_trough_jam', 1)

        # wait for timeout
        self.advance_time_and_run(10)
        self.assertEqual(self.machine.ball_devices["trough"].balls, 4)
        self.assertEqual(self.machine.ball_devices["plunger"].balls, 0)
        assert not self.plunger_coil.pulse.called

        # trough should pulse softly
        self.trough_coil.pulse.assert_called_once_with(5, max_wait_ms=self.max_wait_ms)
        self.trough_coil.pulse = MagicMock()

        # ball leaves and comes back again
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)

        # wait for timeout
        self.advance_time_and_run(10)
        self.assertEqual(self.machine.ball_devices["trough"].balls, 4)
        assert not self.plunger_coil.pulse.called

        self.assertEqual(self.machine.ball_devices["plunger"].balls, 0)

        # trough should pulse softly again
        self.trough_coil.pulse.assert_called_once_with(5, max_wait_ms=self.max_wait_ms)
        self.trough_coil.pulse = MagicMock()

        # ball leaves and comes back again
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)

        # wait for timeout
        self.advance_time_and_run(10)
        self.assertEqual(self.machine.ball_devices["trough"].balls, 4)
        assert not self.plunger_coil.pulse.called

        self.assertEqual(self.machine.ball_devices["plunger"].balls, 0)

        # trough should pulse normally
        self.trough_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
        self.trough_coil.pulse = MagicMock()

        # ball leaves and comes back again
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)

        # wait for timeout
        self.advance_time_and_run(10)
        self.assertEqual(self.machine.ball_devices["trough"].balls, 4)
        assert not self.plunger_coil.pulse.called

        self.assertEqual(self.machine.ball_devices["plunger"].balls, 0)

        # trough should pulse hard
        self.trough_coil.pulse.assert_called_once_with(15, max_wait_ms=self.max_wait_ms)
        self.trough_coil.pulse = MagicMock()

        # ball leaves
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(1)

        # ball goes into plunger
        self.machine.switch_controller.process_switch('s_plunger', 1)
        self.advance_time_and_run(1)

        self.advance_time_and_run(100)
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("ejecting", self.machine.ball_devices["plunger"]._state)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, self._captured)

    def test_eject_ball_stuck_with_second_ball_enter(self):
        # one ball on playfield, second ball ejects but gets stuck at jam
        # switch right as playfield ball drains

        # launch a ball into the playfield
        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        self.trough_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
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

        self.assertEqual(1, self.plunger_coil.pulse.called)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(1, self.machine.ball_devices["playfield"].balls)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("idle", self.machine.ball_devices["plunger"]._state)

        # Playfield requests a second ball
        self.machine.playfield.add_ball()
        self.advance_time_and_run(1)

        self.trough_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
        self.trough_coil.pulse = MagicMock()

        # ball gets stuck in jam switch while ball drains from pf
        self.machine.switch_controller.process_switch('s_trough_2', 0)
        self.machine.switch_controller.process_switch('s_trough_3', 0)
        self.machine.switch_controller.process_switch('s_trough_4', 0)
        self.advance_time_and_run(.1)

        self.machine.switch_controller.process_switch('s_trough_1', 1)
        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.advance_time_and_run(.1)

        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.advance_time_and_run(10)

        # trough retries softly
        self.trough_coil.pulse.assert_called_once_with(5, max_wait_ms=self.max_wait_ms)
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch('s_plunger', 1)
        self.advance_time_and_run(1)

        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("ejecting", self.machine.ball_devices["plunger"]._state)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
        self.assertEqual(1, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.playfield.balls)
        self.assertEqual(1, self._captured)

    def test_eject_while_second_ball_enter(self):
        # one ball on playfield, second ball ejects and the other drains at the
        # same time. jam switch stays open

        # launch a ball into the playfield
        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        self.trough_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
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

        self.assertEqual(1, self.plunger_coil.pulse.called)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(1, self.machine.ball_devices["playfield"].balls)
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("idle", self.machine.ball_devices["plunger"]._state)

        # Playfield requests a second ball
        self.machine.playfield.add_ball()
        self.advance_time_and_run(1)

        self.trough_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
        self.trough_coil.pulse = MagicMock()

        # ball gets stuck in jam switch while ball drains from pf
        self.machine.switch_controller.process_switch('s_trough_2', 0)
        self.machine.switch_controller.process_switch('s_trough_3', 0)
        self.machine.switch_controller.process_switch('s_trough_4', 0)
        self.advance_time_and_run(.1)

        self.machine.switch_controller.process_switch('s_trough_1', 1)
        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.advance_time_and_run(.1)

        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(6)

        # ball goes into plunger
        self.machine.switch_controller.process_switch('s_plunger', 1)
        self.advance_time_and_run(1)

        self.assertEqual(self.machine.ball_devices["trough"].balls, 3)
        self.assertEqual(self.machine.ball_devices["plunger"].balls, 1)
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("ejecting", self.machine.ball_devices["plunger"]._state)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
        self.assertEqual(1, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(1, self._captured)

    def test_random_jam_switch_enable(self):
        return
        # Jam switch just enables randomly

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # default pulse
        self.trough_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
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
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_launch', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_plunger', 0)
        self.advance_time_and_run(1)

        # ball moves from plunger lane to playfield
        self.machine.switch_controller.process_switch('s_playfield', 1)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_playfield', 0)
        self.advance_time_and_run(1)

        self.plunger_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(1, self.machine.ball_devices["playfield"].balls)
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("idle", self.machine.ball_devices["plunger"]._state)

        # Now the jam switch enables. This should never happen in a game, but
        # we should start to think about dealing with bad switches
        self.machine.switch_controller.process_switch('s_trough_jam', 1)

        # currently this will trigger a ball drain

        raise NotImplementedError

    def test_device_starts_with_active_jam_switch(self):
        # MPF boots with jam switch active. During eject a ball always stays
        # on the jam switch

        self.put_four_balls_in_trough()
        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.advance_time_and_run(1)

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # soft pulse
        self.trough_coil.pulse.assert_called_once_with(5, max_wait_ms=self.max_wait_ms)
        self.trough_coil.pulse = MagicMock()

        self.machine.switch_controller.process_switch('s_trough_2', 0)
        self.machine.switch_controller.process_switch('s_trough_3', 0)
        self.machine.switch_controller.process_switch('s_trough_4', 0)
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
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

        self.plunger_coil.pulse.assert_called_once_with(max_wait_ms=self.max_wait_ms)
        self.assertEqual(self.machine.ball_devices["trough"].balls, 3)
        self.assertEqual(self.machine.ball_devices["plunger"].balls, 0)
        self.assertEqual(self.machine.ball_devices["playfield"].balls, 1)
        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("idle", self.machine.ball_devices["plunger"]._state)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, self._captured)

        # request second ball
        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # soft pulse
        self.trough_coil.pulse.assert_called_once_with(5, max_wait_ms=self.max_wait_ms)
        self.trough_coil.pulse = MagicMock()

        self.machine.switch_controller.process_switch('s_trough_3', 0)
        self.machine.switch_controller.process_switch('s_trough_4', 0)
        self.machine.switch_controller.process_switch('s_trough_jam', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.advance_time_and_run(.1)

        # ball goes missing for some time
        self.advance_time_and_run(10)

        # ball goes into plunger
        self.machine.switch_controller.process_switch('s_plunger', 1)
        self.advance_time_and_run(1)

        self.assertEqual("idle", self.machine.ball_devices["trough"]._state)
        self.assertEqual("ejecting", self.machine.ball_devices["plunger"]._state)
        self.assertEqual(self.machine.ball_devices["trough"].balls, 2)
        self.assertEqual(self.machine.ball_devices["plunger"].balls, 1)
        self.assertEqual(self.machine.ball_devices["playfield"].balls, 1)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, self._captured)
