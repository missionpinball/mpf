
from MpfTestCase import MpfTestCase
from mock import MagicMock


class TestBallDeviceJamSwitch(MpfTestCase):

    def getConfigFile(self):
        return 'test_ball_device_jam_switch.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/ball_device/'

    def put_four_balls_in_trough(self):
        self.machine.switch_controller.process_switch('s_trough_1', 1)
        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.advance_time_and_run(1)
        self.assertEqual(self.machine.ball_devices.trough.balls, 4)

        self.trough_coil = self.machine.coils.trough_eject
        self.plunger_coil = self.machine.coils.plunger_eject

        self.trough_coil.pulse = MagicMock()
        self.plunger_coil.pulse = MagicMock()

    def test_eject_with_jam_switch(self):
        # Tests the proper operation of a trough eject with a jam switch

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)

        self.assertEqual(1, self.trough_coil.pulse.called)

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

        self.assertEqual(self.machine.ball_devices.trough.balls, 3)
        self.assertEqual(self.machine.ball_devices.plunger.balls, 1)
        assert not self.plunger_coil.pulse.called
        self.assertEqual("idle", self.machine.ball_devices.trough._state)
        self.assertEqual("ejecting", self.machine.ball_devices.plunger._state)

        # player hits the launch button
        self.machine.switch_controller.process_switch('s_launch', 1)
        self.machine.switch_controller.process_switch('s_launch', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_plunger', 0)
        self.advance_time_and_run(1)

        # ball moves from plunger lane to playfield
        self.machine.switch_controller.process_switch('s_playfield', 1)
        self.machine.switch_controller.process_switch('s_playfield', 0)

        self.assertEqual(1, self.plunger_coil.pulse.called)
        self.assertEqual(self.machine.ball_devices.trough.balls, 3)
        self.assertEqual(self.machine.ball_devices.plunger.balls, 0)
        self.assertEqual(self.machine.ball_devices.playfield.balls, 1)
        self.assertEqual("idle", self.machine.ball_devices.trough._state)
        self.assertEqual("idle", self.machine.ball_devices.plunger._state)

    def test_eject_no_jam_switch_activity(self):
        # Jam switch is configured, but it is not activated when the ball
        # ejects

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)

        self.assertEqual(1, self.trough_coil.pulse.called)

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

        self.assertEqual(self.machine.ball_devices.trough.balls, 3)
        self.assertEqual(self.machine.ball_devices.plunger.balls, 1)
        assert not self.plunger_coil.pulse.called
        self.assertEqual("idle", self.machine.ball_devices.trough._state)
        self.assertEqual("ejecting", self.machine.ball_devices.plunger._state)

        # player hits the launch button
        self.machine.switch_controller.process_switch('s_launch', 1)
        self.machine.switch_controller.process_switch('s_launch', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_plunger', 0)
        self.advance_time_and_run(1)

        # ball moves from plunger lane to playfield
        self.machine.switch_controller.process_switch('s_playfield', 1)
        self.machine.switch_controller.process_switch('s_playfield', 0)

        self.assertEqual(1, self.plunger_coil.pulse.called)
        self.assertEqual(self.machine.ball_devices.trough.balls, 3)
        self.assertEqual(self.machine.ball_devices.plunger.balls, 0)
        self.assertEqual(self.machine.ball_devices.playfield.balls, 1)
        self.assertEqual("idle", self.machine.ball_devices.trough._state)
        self.assertEqual("idle", self.machine.ball_devices.plunger._state)

    def text_eject_with_jam_all_balls_disappear(self):
        # Ball ejects and gets stuck on jam switch. All other balls shift a
        # half position and get stuck between switches, so it's like all the
        # balls just disappeared.

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)

        self.assertEqual(1, self.trough_coil.pulse.called)

        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.machine.switch_controller.process_switch('s_trough_2', 0)
        self.machine.switch_controller.process_switch('s_trough_3', 0)
        self.machine.switch_controller.process_switch('s_trough_4', 0)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.advance_time_and_run(1)

        # todo now what?
        raise NotImplementedError

    def test_eject_ball_stuck_in_jam_switch(self):
        # Ball ejects, gets stuck in jam switch

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)

        self.assertEqual(1, self.trough_coil.pulse.called)

        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.machine.switch_controller.process_switch('s_trough_2', 0)
        self.machine.switch_controller.process_switch('s_trough_3', 0)
        self.machine.switch_controller.process_switch('s_trough_4', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.advance_time_and_run(1)

        self.assertEqual(self.machine.ball_devices.trough.balls, 4)
        self.assertEqual(self.machine.ball_devices.plunger.balls, 0)

        assert not self.plunger_coil.pulse.called
        self.assertEqual("idle", self.machine.ball_devices.trough._state)
        self.assertEqual("idle", self.machine.ball_devices.plunger._state)

        # todo now what?
        raise NotImplementedError

    def test_eject_ball_falls_back_in(self):
        # Ball ejects, ball leaves with proper timeout, but ball falls back in

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)

        self.assertEqual(1, self.trough_coil.pulse.called)

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

        # ball goes into plunger
        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.advance_time_and_run(1)

        self.assertEqual(self.machine.ball_devices.trough.balls, 4)
        self.assertEqual(self.machine.ball_devices.plunger.balls, 0)
        assert not self.plunger_coil.pulse.called

        # todo now what?

    def test_eject_ball_stuck_with_second_ball_enter(self):
        # one ball on playfield, second ball ejects but gets stuck at jam
        # switch right as playfield ball drains

        # launch a ball into the playfield
        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)

        self.assertEqual(1, self.trough_coil.pulse.called)

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

        self.assertEqual(self.machine.ball_devices.trough.balls, 3)
        self.assertEqual(self.machine.ball_devices.plunger.balls, 1)
        assert not self.plunger_coil.pulse.called
        self.assertEqual("idle", self.machine.ball_devices.trough._state)
        self.assertEqual("ejecting", self.machine.ball_devices.plunger._state)

        # player hits the launch button
        self.machine.switch_controller.process_switch('s_launch', 1)
        self.machine.switch_controller.process_switch('s_launch', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_plunger', 0)
        self.advance_time_and_run(1)

        # ball moves from plunger lane to playfield
        self.machine.switch_controller.process_switch('s_playfield', 1)
        self.machine.switch_controller.process_switch('s_playfield', 0)

        self.assertEqual(1, self.plunger_coil.pulse.called)
        self.assertEqual(self.machine.ball_devices.trough.balls, 3)
        self.assertEqual(self.machine.ball_devices.plunger.balls, 0)
        self.assertEqual(self.machine.ball_devices.playfield.balls, 1)
        self.assertEqual("idle", self.machine.ball_devices.trough._state)
        self.assertEqual("idle", self.machine.ball_devices.plunger._state)

        # Playfield requests a second ball
        self.machine.playfield.add_ball()

        self.assertEqual(2, self.trough_coil.pulse.call_count)

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
        self.advance_time_and_run(1)

        # todo now what?

    def test_random_jam_switch_enable(self):
        # Jam switch just enables randomly

        self.put_four_balls_in_trough()

        self.machine.playfield.add_ball(player_controlled=True)

        self.assertEqual(1, self.trough_coil.pulse.called)

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

        self.assertEqual(self.machine.ball_devices.trough.balls, 3)
        self.assertEqual(self.machine.ball_devices.plunger.balls, 1)
        assert not self.plunger_coil.pulse.called
        self.assertEqual("idle", self.machine.ball_devices.trough._state)
        self.assertEqual("ejecting", self.machine.ball_devices.plunger._state)

        # player hits the launch button
        self.machine.switch_controller.process_switch('s_launch', 1)
        self.machine.switch_controller.process_switch('s_launch', 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch('s_plunger', 0)
        self.advance_time_and_run(1)

        # ball moves from plunger lane to playfield
        self.machine.switch_controller.process_switch('s_playfield', 1)
        self.machine.switch_controller.process_switch('s_playfield', 0)

        self.assertEqual(1, self.plunger_coil.pulse.called)
        self.assertEqual(self.machine.ball_devices.trough.balls, 3)
        self.assertEqual(self.machine.ball_devices.plunger.balls, 0)
        self.assertEqual(self.machine.ball_devices.playfield.balls, 1)
        self.assertEqual("idle", self.machine.ball_devices.trough._state)
        self.assertEqual("idle", self.machine.ball_devices.plunger._state)

        # Now the jam switch enables. This should never happen in a game, but
        # we should start to think about dealing with bad switches
        self.machine.switch_controller.process_switch('s_trough_jam', 1)

        # currently this will trigger a ball drain

        raise NotImplementedError

    def test_device_starts_with_active_jam_switch(self):
        # MPF boots with jam switch active

        self.machine.switch_controller.process_switch('s_trough_jam', 1)
        self.machine.switch_controller.process_switch('s_trough_2', 1)
        self.machine.switch_controller.process_switch('s_trough_3', 1)
        self.machine.switch_controller.process_switch('s_trough_4', 1)
        self.advance_time_and_run(1)
        self.assertEqual(self.machine.ball_devices.trough.balls, 4)

        self.trough_coil = self.machine.coils.trough_eject
        self.plunger_coil = self.machine.coils.plunger_eject

        self.trough_coil.pulse = MagicMock()
        self.plunger_coil.pulse = MagicMock()

        # todo have to decide what to do here?

        raise NotImplementedError
