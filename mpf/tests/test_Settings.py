from mpf.tests.MpfTestCase import MpfTestCase


class TestSettings(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/settings/'

    def get_platform(self):
        return 'smart_virtual'

    def _tilted(self, **kwargs):
        del kwargs
        self._is_tilted = True

    def test_settings_values(self):
        self.assertEqual(0, self.machine.settings.custom_setting_int)
        self.machine.settings.set_setting_value("custom_setting_int", 2)
        self.assertEqual(2, self.machine.settings.custom_setting_int)

        self.assertEqual("one", self.machine.settings.custom_setting_str)
        self.machine.settings.set_setting_value("custom_setting_str", "zero")
        self.assertEqual("zero", self.machine.settings.custom_setting_str)
