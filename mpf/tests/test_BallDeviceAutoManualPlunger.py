from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallDeviceAutoManualPlunger(MpfTestCase):

    def get_config_file(self):
        return 'test_ball_device_auto_manual_plunger.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def test_mechanical_eject_to_pf(self):

        plunger = self.machine.ball_devices['plunger']
        playfield = self.machine.ball_devices['playfield']
        trough_coil = self.machine.coils['trough_eject']
        plunger_coil = self.machine.coils['plunger_eject']
        trough_coil.pulse = MagicMock()
        plunger_coil.pulse = MagicMock()

        # add ball to trough
        self.machine.switch_controller.process_switch('s_trough_1', 1)

        self.advance_time_and_run(1)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, plunger.balls)
        assert not plunger_coil.pulse.called
        assert not trough_coil.pulse.called

        # Request player eject to pf
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        self.assertTrue(trough_coil.pulse.called)
        assert not plunger_coil.pulse.called

        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.advance_time_and_run(1)

        # plunger gets ball
        self.machine.switch_controller.process_switch('s_plunger', 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, plunger.balls)
        assert not plunger_coil.pulse.called

        # player waits, then mechanically plunges
        self.advance_time_and_run(5)
        self.machine.switch_controller.process_switch('s_plunger', 0)

        # ball lands on pf
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch('s_playfield', 1)
        self.machine.switch_controller.process_switch('s_playfield', 0)
        self.advance_time_and_run(.1)

        assert not plunger_coil.pulse.called
        self.assertEqual(0, plunger.balls)
        self.assertEqual(1, playfield.balls)

    def test_powered_eject_to_pf(self):

        plunger = self.machine.ball_devices['plunger']
        playfield = self.machine.ball_devices['playfield']
        trough_coil = self.machine.coils['trough_eject']
        plunger_coil = self.machine.coils['plunger_eject']
        trough_coil.pulse = MagicMock()
        plunger_coil.pulse = MagicMock()

        # add ball to trough
        self.machine.switch_controller.process_switch('s_trough_1', 1)

        self.advance_time_and_run(1)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, plunger.balls)
        assert not plunger_coil.pulse.called
        assert not trough_coil.pulse.called

        # Request player eject to pf
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        self.assertTrue(trough_coil.pulse.called)
        assert not plunger_coil.pulse.called

        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.advance_time_and_run(1)

        # plunger gets ball
        self.machine.switch_controller.process_switch('s_plunger', 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, plunger.balls)
        assert not plunger_coil.pulse.called

        # player waits, then hits launch button
        self.advance_time_and_run(5)
        self.machine.switch_controller.process_switch('s_launch', 1)
        self.machine.switch_controller.process_switch('s_launch', 0)

        self.advance_time_and_run(1)
        self.assertTrue(plunger_coil.pulse.called)

        self.machine.switch_controller.process_switch('s_plunger', 0)

        # ball lands on pf
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch('s_playfield', 1)
        self.machine.switch_controller.process_switch('s_playfield', 0)
        self.advance_time_and_run(.1)

        self.assertEqual(0, plunger.balls)
        self.assertEqual(1, playfield.balls)

    def test_returned_ball_with_missing_ball(self):
        plunger = self.machine.ball_devices['plunger']
        trough = self.machine.ball_devices['trough']
        playfield = self.machine.ball_devices['playfield']
        trough_coil = self.machine.coils['trough_eject']
        plunger_coil = self.machine.coils['plunger_eject']
        trough_coil.pulse = MagicMock()
        plunger_coil.pulse = MagicMock()

        # add ball to trough
        self.machine.switch_controller.process_switch('s_trough_1', 1)
        self.machine.switch_controller.process_switch('s_trough_2', 1)

        self.advance_time_and_run(1)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, plunger.balls)
        assert not plunger_coil.pulse.called
        assert not trough_coil.pulse.called

        # Request player eject to pf
        playfield.add_ball(player_controlled=False)
        self.advance_time_and_run(1)

        self.assertTrue(trough_coil.pulse.called)
        assert not plunger_coil.pulse.called

        self.machine.switch_controller.process_switch('s_trough_1', 0)
        self.advance_time_and_run(1)

        # plunger gets ball
        self.machine.switch_controller.process_switch('s_plunger', 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, plunger.balls)
        self.assertTrue(plunger_coil.pulse.called)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch('s_plunger', 0)
        self.advance_time_and_run(1)

        # ball returns
        self.machine.switch_controller.process_switch('s_plunger', 1)
        self.advance_time_and_run(9)
        # but then disappears
        self.machine.switch_controller.process_switch('s_plunger', 0)
        self.advance_time_and_run(20)

        self.assertEqual(0, plunger.balls)
        self.assertFalse(plunger.outgoing_balls_handler._eject_queue.qsize())
        self.assertEqual("idle", plunger.state)
        self.assertEqual(1, playfield.balls)
        self.assertFalse(trough.outgoing_balls_handler._eject_queue.qsize())
        self.assertEqual("idle", trough.state)
        self.assertBallsOnPlayfield(1)
