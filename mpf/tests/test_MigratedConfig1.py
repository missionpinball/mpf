# Verifies that the v4 target migrated file actually works with the current
# version of MPF

from mpf.tests.MpfTestCase import MpfTestCase


class TestMigratedV4(MpfTestCase):

    def getConfigFile(self):
        return 'test_config1_v4.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/migrator/'

    def test_migrated_file(self):
        pass

        # Really we just need to make sure it loads. If any sections are
        # broken, their own validators should pick them up.

        # print(self.machine.shows)
