from tests.MpfTestCase import MpfTestCase
from mock import MagicMock


class TestDeviceDriver(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/device/'

    def get_platform(self):
        return 'smart_virtual'

    def testBasicFunctions(self):
        # Make sure hardware devices have been configured for tests
        self.assertIn('flasher_01', self.machine.flashers)
        self.assertEqual(self.machine.flashers.flasher_01.config['label'], "Test flasher")
        self.assertEqual(self.machine.flashers.flasher_01.config['number'], "1")
        self.assertEqual(self.machine.flashers.flasher_01.config['flash_ms'], 40)

        # Setup platform function mock to test coil
        self.machine.flashers.flasher_01.hw_driver.disable = MagicMock()
        self.machine.flashers.flasher_01.hw_driver.enable = MagicMock()
        self.machine.flashers.flasher_01.hw_driver.pulse = MagicMock()

        # Flash
        self.machine.flashers.flasher_01.flash(100)
        self.machine.flashers.flasher_01.hw_driver.pulse.assert_called_with(100)
        self.machine.flashers.flasher_01.flash()
        self.machine.flashers.flasher_01.hw_driver.pulse.assert_called_with(40)

        # TODO: Add some more comprehensive tests
