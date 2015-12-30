from tests.MpfTestCase import MpfTestCase

class TestModes(MpfTestCase):

    def getConfigFile(self):
        return 'test_modes.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/mode_tests/'

    def test_loading_modes(self):
        self.assertIn('mode1', [x.name for x in self.machine.modes])

        # This mode is Mode2 in the config, so make sure it's mode2 here
        self.assertIn('mode2', [x.name for x in self.machine.modes])