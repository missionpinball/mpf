from mpf.tests.MpfTestCase import MpfTestCase


class TestModesConfigValidation(MpfTestCase):

    def getConfigFile(self):
        return self.config

    def getMachinePath(self):
        return 'tests/machine_files/mode_tests/'

    def setUp(self):
        self.save_and_prepare_sys_path()

    def _early_machine_init(self, machine):
        self.add_to_config_validator(machine, 'unrelated_section',
                                     dict(__valid_in__ = 'mode'))

    def tearDown(self):
        self.restore_sys_path()

    def test_loading_invalid_modes(self):
        self.config = 'test_loading_invalid_modes.yaml'
        with self.assertRaises(ValueError) as context:
            super(TestModesConfigValidation, self).setUp()

        self.loop.close()

        self.assertEqual("No folder found for mode 'invalid'. Is your "
                         "mode folder in your machine's 'modes' folder?",
                         str(context.exception))

    def test_empty_modes_section(self):
        self.config = 'test_empty_modes_section.yaml'
        super(TestModesConfigValidation, self).setUp()
        super().tearDown()

    def test_broken_mode_config(self):
        self.config = 'test_broken_mode_config.yaml'
        with self.assertRaises(AssertionError) as context:
            super(TestModesConfigValidation, self).setUp()

        self.loop.close()

        self.assertEqual('Config File Error in ConfigValidator: Your config contains a value for the setting '
                         '"mode:invalid_key", but this is not a valid setting name. Error Code: CFE-ConfigValidator-2',
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

        self.loop.close()

        self.assertEqual('Did not find any config for mode mode_without_config.',
                         str(context.exception))
