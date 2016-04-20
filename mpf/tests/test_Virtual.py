from mpf.tests.MpfTestCase import MpfTestCase
from mock import MagicMock


class TestSmartVirtualPlatform(MpfTestCase):

    def getConfigFile(self):
        return "test_virtual.yaml"

    def getMachinePath(self):
        return 'tests/machine_files/platform/'

    def test_load_config(self):
        # test that we can load the config with coil and switch parameters from platforms
        pass
