from tests.MpfTestCase import MpfTestCase


class TestConfigMissingVersion(MpfTestCase):
    def getConfigFile(self):
        return 'test_config_interface_missing_version.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/config_interface/'

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_config_file_with_missing_version(self):
        self.assertRaises(ValueError, super().setUp)
