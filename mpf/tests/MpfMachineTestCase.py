from mpf.tests.MpfTestCase import MpfTestCase


class MpfMachineTestCase(MpfTestCase):

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)

        # only disable bcp. everything else should run
        self.machine_config_patches = dict()
        self.machine_config_patches['bcp'] = []

        # increase test expected duration
        self.expected_duration = 5.0

    def getConfigFile(self):
        return "config.yaml"

    def getMachinePath(self):
        return ""

    def getAbsoluteMachinePath(self):
        # do not use path relative to MPF folder
        return self.getMachinePath()

    def get_platform(self):
        return 'smart_virtual'
