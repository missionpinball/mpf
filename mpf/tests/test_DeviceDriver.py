"""Test coils."""
from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestDeviceDriver(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/device/'

    def get_platform(self):
        return 'smart_virtual'

    def testBasicFunctions(self):
        # Make sure hardware devices have been configured for tests
        self.assertIn('coil_01', self.machine.coils)
        self.assertIn('coil_02', self.machine.coils)

        # Setup platform function mock to test coil
        self.machine.coils.coil_01.hw_driver.disable = MagicMock()
        self.machine.coils.coil_01.hw_driver.enable = MagicMock()
        self.machine.coils.coil_01.hw_driver.pulse = MagicMock(return_value=45)

        self.machine.coils.coil_01.enable()
        self.machine.coils.coil_01.hw_driver.enable.assert_called_with(self.machine.coils.coil_01)
        self.machine.coils.coil_01.pulse(100)
        self.machine.coils.coil_01.hw_driver.pulse.assert_called_with(self.machine.coils.coil_01, 100)
        self.machine.coils.coil_01.disable()
        self.machine.coils.coil_01.hw_driver.disable.assert_called_with(self.machine.coils.coil_01)

        self.machine.coils.coil_03.hw_driver.disable = MagicMock()
        self.machine.coils.coil_03.hw_driver.enable = MagicMock()
        self.machine.coils.coil_03.hw_driver.pulse = MagicMock(return_value=10)

        # test default pulse_ms
        self.machine.config['mpf']['default_pulse_ms'] = 23
        self.machine.coils.coil_03.pulse()
        self.machine.coils.coil_03.hw_driver.pulse.assert_called_with(self.machine.coils.coil_03, 23)

        # test power
        self.machine.config['mpf']['default_pulse_ms'] = 40
        self.machine.coils.coil_03.pulse(power=1.0)
        self.machine.coils.coil_03.hw_driver.pulse.assert_called_with(self.machine.coils.coil_03, 40)

        self.machine.coils.coil_03.pulse(power=0.5)
        self.machine.coils.coil_03.hw_driver.pulse.assert_called_with(self.machine.coils.coil_03, 20)
