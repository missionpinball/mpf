from mpf.tests.MpfTestCase import MpfTestCase


class TestPlayfield(MpfTestCase):

    def getConfigFile(self):
        return 'test_playfield.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/playfield/'

    # nothing to test currently
