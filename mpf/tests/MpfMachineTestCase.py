from mpf.tests.MpfTestCase import MpfTestCase


class MpfMachineTestCase(MpfTestCase):

    def getConfigFile(self):
        return "config.yaml"

    def getMachinePath(self):
        return ""

    def getAbsoluteMachinePath(self):
        # do not use path relative to MPF folder
        return self.getMachinePath()