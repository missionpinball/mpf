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
        self.assertIn('flasher_01', self.machine.lights)

        # Setup platform function mock to test coil
        self.machine.coils.flasher_01.hw_driver.disable = MagicMock()
        self.machine.coils.flasher_01.hw_driver.enable = MagicMock()
        self.machine.coils.flasher_01.hw_driver.pulse = MagicMock()

        # Flash
        self.post_event("flash")
        self.advance_time_and_run(.05)
        self.assertTrue(self.machine.coils.flasher_01.hw_driver.enable.called)
        self.assertFalse(self.machine.coils.flasher_01.hw_driver.disable.called)
        self.advance_time_and_run(.1)
        self.assertTrue(self.machine.coils.flasher_01.hw_driver.disable.called)

        # Flash with placeholder
        self.machine.coils.flasher_01.hw_driver.disable = MagicMock()
        self.machine.coils.flasher_01.hw_driver.enable = MagicMock()
        self.machine.coils.flasher_01.hw_driver.pulse = MagicMock()
        self.machine.coils.flasher_02.hw_driver.disable = MagicMock()
        self.machine.coils.flasher_02.hw_driver.enable = MagicMock()
        self.machine.coils.flasher_02.hw_driver.pulse = MagicMock()

        self.post_event("flash2")
        self.advance_time_and_run(.05)
        self.assertTrue(self.machine.coils.flasher_01.hw_driver.enable.called)
        self.assertFalse(self.machine.coils.flasher_01.hw_driver.disable.called)
        self.assertTrue(self.machine.coils.flasher_02.hw_driver.enable.called)
        self.assertFalse(self.machine.coils.flasher_02.hw_driver.disable.called)
        self.advance_time_and_run(.1)
        self.assertTrue(self.machine.coils.flasher_01.hw_driver.disable.called)
        self.assertTrue(self.machine.coils.flasher_02.hw_driver.disable.called)
