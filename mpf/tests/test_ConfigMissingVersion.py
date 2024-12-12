from mpf.tests.MpfTestCase import MpfTestCase


class TestConfigMissingVersion(MpfTestCase):
    def get_config_file(self):
        return 'test_config_interface_missing_version.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/config_interface/'

    def setUp(self):
        self.save_and_prepare_sys_path()

    def tearDown(self):
        self.restore_sys_path()

    def test_config_file_with_missing_version(self):
        self.assertRaises(ValueError, super().setUp)
        self.loop.close()
