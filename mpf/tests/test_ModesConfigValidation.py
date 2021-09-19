from mpf.tests.MpfTestCase import MpfTestCase
from mpf._version import log_url


class TestModesConfigValidation(MpfTestCase):

    def get_config_file(self):
        return self.config

    def get_machine_path(self):
        return 'tests/machine_files/mode_tests/'

    def setUp(self):
        self.save_and_prepare_sys_path()

    def tearDown(self):
        self.restore_sys_path()

    def test_loading_invalid_modes(self):
        self.config = 'test_loading_invalid_modes.yaml'
        with self.assertRaises(AssertionError) as context:
            super(TestModesConfigValidation, self).setUp()

        self.loop.close()

        self.assertEqual("No config found for mode 'invalid'. MPF expects the config at "
                         "'modes/invalid/config/invalid.yaml' inside your machine folder.",
                         str(context.exception))

    def test_empty_modes_section(self):
        self.config = 'test_empty_modes_section.yaml'
        super(TestModesConfigValidation, self).setUp()
        super().tearDown()

    def test_broken_mode_config(self):
        self.config = 'test_broken_mode_config.yaml'
        with self.assertRaises(AssertionError) as context:
            super(TestModesConfigValidation, self).setUp()

        self.loop.close(ignore_running_tasks=True)

        self.maxDiff = None
        self.assertEqual('Config File Error in ConfigValidator: Your config contains a value for the setting '
                         '"mode:invalid_key", but this is not a valid setting name. Error Code: CFE-ConfigValidator-2 '
                         '({})'.format(log_url.format("CFE-ConfigValidator-2")),
                         str(context.exception))

    def test_missing_mode_section(self):
        self.config = 'test_missing_mode_section.yaml'
        super(TestModesConfigValidation, self).setUp()

        self.assertTrue("broken_mode2" in self.machine.modes)

        super().tearDown()

    def test_mode_without_config(self):
        self.config = 'test_mode_without_config.yaml'
        with self.assertRaises(AssertionError) as context:
            super(TestModesConfigValidation, self).setUp()

        self.loop.close(ignore_running_tasks=True)

        self.assertEqual("No config found for mode 'mode_without_config'. MPF expects the config at "
                         "'modes/mode_without_config/config/mode_without_config.yaml' inside your machine folder.",
                         str(context.exception))
