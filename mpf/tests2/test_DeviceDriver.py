"""Test coils."""
from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings

from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestDeviceDriver(MpfTestCase):

    def get_config_file(self):
        return 'coils.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/device/'

    def get_platform(self):
        return 'smart_virtual'

    def testBasicFunctions(self):
        # Make sure hardware devices have been configured for tests
        self.assertIn('coil_01', self.machine.coils)
        self.assertIn('coil_02', self.machine.coils)

        # Setup platform function mock to test coil
        self.machine.coils["coil_01"].hw_driver.disable = MagicMock()
        self.machine.coils["coil_01"].hw_driver.enable = MagicMock()
        self.machine.coils["coil_01"].hw_driver.pulse = MagicMock()

        self.machine.coils["coil_01"].enable()
        self.machine.coils["coil_01"].hw_driver.enable.assert_called_with(PulseSettings(power=1.0, duration=30),
                                                                       HoldSettings(power=1.0, duration=None))
        self.machine.coils["coil_01"].pulse(100)
        self.machine.coils["coil_01"].hw_driver.pulse.assert_called_with(PulseSettings(power=1.0, duration=100))
        self.machine.coils["coil_01"].disable()
        self.machine.coils["coil_01"].hw_driver.disable.assert_called_with()

        self.machine.coils["coil_03"].hw_driver.disable = MagicMock()
        self.machine.coils["coil_03"].hw_driver.enable = MagicMock()
        self.machine.coils["coil_03"].hw_driver.pulse = MagicMock()

        # test power
        self.machine.coils["coil_03"].pulse(pulse_power=1.0)
        self.machine.coils["coil_03"].hw_driver.pulse.assert_called_with(PulseSettings(power=1.0, duration=10))

        self.machine.coils["coil_03"].pulse(pulse_power=0.5)
        self.machine.coils["coil_03"].hw_driver.pulse.assert_called_with(PulseSettings(power=0.5, duration=10))

        self.machine.coils["coil_01"].enable(pulse_power=0.7, hold_power=0.3)
        self.machine.coils["coil_01"].hw_driver.enable.assert_called_with(PulseSettings(power=0.7, duration=30),
                                                                       HoldSettings(power=0.3, duration=None))

        # test long pulse with delay
        self.machine.coils["coil_03"].hw_driver.pulse = MagicMock()
        self.machine.coils["coil_03"].hw_driver.enable = MagicMock()
        self.machine.coils["coil_03"].hw_driver.disable = MagicMock()
        self.machine.coils["coil_03"].pulse(pulse_ms=500)
        self.machine.coils["coil_03"].hw_driver.enable.assert_called_with(PulseSettings(power=1.0, duration=0),
                                                                       HoldSettings(power=1.0, duration=None))
        self.machine.coils["coil_03"].hw_driver.pulse.assert_not_called()
        self.advance_time_and_run(.5)

        self.machine.coils["coil_03"].hw_driver.disable.assert_called_with()

    def testMaxHoldDuration(self):
        coil = self.machine.coils["coil_max_hold_duration"]

        # check that coil disables after max_hold_duration (5s)
        coil.enable()
        self.advance_time_and_run(.5)
        self.assertEqual("enabled", coil.hw_driver.state)
        self.advance_time_and_run(4)
        self.assertEqual("enabled", coil.hw_driver.state)
        self.advance_time_and_run(1)
        self.assertEqual("disabled", coil.hw_driver.state)

        # make sure a disable resets the timer
        coil.enable()
        self.advance_time_and_run(3.0)
        self.assertEqual("enabled", coil.hw_driver.state)
        coil.disable()
        self.advance_time_and_run(.5)
        self.assertEqual("disabled", coil.hw_driver.state)
        coil.enable()
        self.advance_time_and_run(3.0)
        self.assertEqual("enabled", coil.hw_driver.state)

    def testPulseWithTimedEnable(self):
        coil = self.machine.coils["coil_pulse_with_timed_enable"]
        coil.hw_driver.timed_enable = MagicMock()
        coil.pulse()
        coil.hw_driver.timed_enable.assert_called_with(
            PulseSettings(power=0.25, duration=60),
            HoldSettings(power=0.5, duration=200))
