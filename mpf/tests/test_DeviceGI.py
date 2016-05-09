from mpf.tests.MpfTestCase import MpfTestCase


class TestDeviceGI(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/device/'

    def get_platform(self):
        return 'smart_virtual'

    def testBasicOnAndOff(self):
        """Tests setting some GI brightness levels (using default arguments)"""

        # Make sure hardware devices have been configured for tests
        self.assertIn('gi_01', self.machine.gis)
        self.assertIn('gi_02', self.machine.gis)

        self.advance_time_and_run(10)

        # GI should start out on as enable is called during setup (current brightness is 255)
        self.assertEqual(255, self.machine.gis.gi_01.hw_driver.current_brightness)
        self.assertEqual(255, self.machine.gis.gi_02.hw_driver.current_brightness)

        # Turn on GI (different brightness levels)
        self.machine.gis.gi_01.enable(128)
        self.assertEqual(128, self.machine.gis.gi_01.hw_driver.current_brightness)
        self.machine.gis.gi_02.enable(77)
        self.assertEqual(77, self.machine.gis.gi_02.hw_driver.current_brightness)

        # Turn off GI
        self.machine.gis.gi_01.disable()
        self.assertEqual(0, self.machine.gis.gi_01.hw_driver.current_brightness)
        self.machine.gis.gi_02.disable()
        self.assertEqual(0, self.machine.gis.gi_02.hw_driver.current_brightness)
