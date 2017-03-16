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
        self.assertIn('gi_01', self.machine.lights)
        self.assertIn('gi_02', self.machine.lights)

        self.advance_time_and_run(10)

        # GI should start out disabled like any light
        self.assertLightChannel("gi_01", 0)
        self.assertLightChannel("gi_02", 0)

        # Turn on GI (different brightness levels)
        self.machine.lights.gi_01.color([128, 128, 128])
        self.advance_time_and_run(.1)
        self.assertLightChannel("gi_01", 128)
        self.machine.lights.gi_02.color([77, 77, 77])
        self.advance_time_and_run(.1)
        self.assertLightChannel("gi_02", 77)

        # Turn off GI
        self.machine.lights.gi_01.off()
        self.advance_time_and_run(.1)
        self.assertLightChannel("gi_01", 0)
        self.machine.lights.gi_02.off()
        self.advance_time_and_run(.1)
        self.assertLightChannel("gi_02", 0)
