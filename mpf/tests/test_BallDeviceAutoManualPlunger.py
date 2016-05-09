from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallDeviceAutoManualPlunger(MpfTestCase):

    def getConfigFile(self):
        return 'test_ball_device_auto_manual_plunger.yaml'

    def getMachinePath(self):
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

        trough_coil.pulse.assert_called_once_with()
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

        trough_coil.pulse.assert_called_once_with()
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
        plunger_coil.pulse.assert_called_once_with()

        self.machine.switch_controller.process_switch('s_plunger', 0)

        # ball lands on pf
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch('s_playfield', 1)
        self.machine.switch_controller.process_switch('s_playfield', 0)
        self.advance_time_and_run(.1)

        self.assertEqual(0, plunger.balls)
        self.assertEqual(1, playfield.balls)
