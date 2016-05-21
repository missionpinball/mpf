from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase


class TestMotors(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/motor/'

    def testMotorizedDropTargetBank(self):
        motor = self.machine.motors.motorized_drop_target_bank
        coil = self.machine.coils.c_motor_run
        coil.enable = MagicMock()
        coil.disable = MagicMock()

        # reset should move it down
        motor.reset()
        self.advance_time_and_run()
        coil.enable.assert_called_with()
        coil.enable = MagicMock()
        assert not coil.disable.called

        # it goes up. nothing should happen
        self.hit_switch_and_run("s_position_up", 1)
        assert not coil.enable.called
        assert not coil.disable.called

        # it leaves up position
        self.release_switch_and_run("s_position_up", 1)
        assert not coil.enable.called
        assert not coil.disable.called

        self.advance_time_and_run(5)
        # it goes down. motor should stop
        self.hit_switch_and_run("s_position_down", 1)
        assert not coil.enable.called
        coil.disable.assert_called_with()
        coil.disable = MagicMock()

        # should not start motor
        self.post_event("go_down2")
        self.advance_time_and_run()
        assert not coil.enable.called
        coil.disable.assert_called_with()
        coil.disable = MagicMock()

        # go up
        self.post_event("go_up")
        self.advance_time_and_run()
        coil.enable.assert_called_with()
        coil.enable = MagicMock()
        assert not coil.disable.called

        # it leaves down position
        self.release_switch_and_run("s_position_down", 0)
        assert not coil.enable.called
        assert not coil.disable.called

        self.advance_time_and_run(5)
        # it goes up. motor should stop
        self.hit_switch_and_run("s_position_up", 1)
        assert not coil.enable.called
        coil.disable.assert_called_with()
        coil.disable = MagicMock()
