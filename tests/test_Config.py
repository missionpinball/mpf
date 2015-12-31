from tests.MpfTestCase import MpfTestCase

class TestConfig(MpfTestCase):

    def getConfigFile(self):
        return 'test_config_interface.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/config_interface/'

    def test_config_file(self):
        # true, True, yes, Yes values should be True
        self.assertIs(True, self.machine.config['test_section']['true_key1'])
        self.assertIs(True, self.machine.config['test_section']['true_key2'])
        self.assertIs(True, self.machine.config['test_section']['true_key3'])
        self.assertIs(True, self.machine.config['test_section']['true_key4'])

        # false, False, no, No values should be False
        self.assertIs(False, self.machine.config['test_section']['false_key1'])
        self.assertIs(False, self.machine.config['test_section']['false_key2'])
        self.assertIs(False, self.machine.config['test_section']['false_key3'])
        self.assertIs(False, self.machine.config['test_section']['false_key4'])

        # on, off values should be strings
        self.assertEqual('on', self.machine.config['test_section']['on_string'])
        self.assertEqual('off', self.machine.config['test_section']['off_string'])

        # 6400, 003200, 6, 07 should be ints
        self.assertEqual(6400, self.machine.config['test_section']['int_6400'])
        self.assertEqual(3200, self.machine.config['test_section']['int_3200'])
        self.assertEqual(6, self.machine.config['test_section']['int_6'])
        self.assertEqual(7, self.machine.config['test_section']['int_7'])

        # 00ff00 should be string
        self.assertEqual('00ff00', self.machine.config['test_section']['str_00ff00'])

        # keys should be all lowercase
        self.assertIn('case_sensitive_1', self.machine.config['test_section'])
        self.assertIn('case_sensitive_2', self.machine.config['test_section'])
        self.assertIn('case_sensitive_3', self.machine.config['test_section'])

        # values should be case sensitive
        self.assertEqual(self.machine.config['test_section']['case_sensitive_1'], 'test')
        self.assertEqual(self.machine.config['test_section']['case_sensitive_2'], 'test')
        self.assertEqual(self.machine.config['test_section']['case_sensitive_3'], 'Test')

        # key should be lowercase even though it's uppercase in the config
        self.assertIn('test_section_1', self.machine.config)

    def test_config_validator(self):
        # test config spec syntax error
        self.assertRaises(ValueError,
                          self.machine.config_processor.validate_config_item2,
                          'single|int', None, None)

        # test default required, source is int
        validation_string = 'single|int|'
        results = self.machine.config_processor.validate_config_item2(
                validation_string, 'test_failure_info', 0)
        self.assertEqual(results, 0)

        # test default provided, source overrides default
        validation_string = 'single|int|0'
        results = self.machine.config_processor.validate_config_item2(
                validation_string, 'test_failure_info', 1)
        self.assertEqual(results, 1)

        # test source type is converted to int
        validation_string = 'single|int|0'
        results = self.machine.config_processor.validate_config_item2(
                validation_string, 'test_failure_info', '1')
        self.assertEqual(results, 1)

        # test default when no source is present
        validation_string = 'single|int|1'
        results = self.machine.config_processor.validate_config_item2(
                validation_string, 'test_failure_info')  # no item in config
        self.assertEqual(results, 1)

        # test default required with source missing raises error
        validation_string = 'single|int|'  # default required
        self.assertRaises(ValueError,
                          self.machine.config_processor.validate_config_item2,
                          validation_string, 'test_failure_info')  # no item

        # test str validations

        validation_string = 'single|str|'
        results = self.machine.config_processor.validate_config_item2(
            validation_string, 'test_failure_info', 'hello')
        self.assertEqual(results, 'hello')

        validation_string = 'single|str|'
        results = self.machine.config_processor.validate_config_item2(
            validation_string, 'test_failure_info', 1)
        self.assertEqual(results, '1')

        # test float validations

        validation_string = 'single|float|'
        results = self.machine.config_processor.validate_config_item2(
            validation_string, 'test_failure_info', 1)
        self.assertAlmostEqual(results, 1.0, .01)

        validation_string = 'single|float|'
        results = self.machine.config_processor.validate_config_item2(
            validation_string, 'test_failure_info', '1')
        self.assertAlmostEqual(results, 1.0, .01)

        validation_string = 'single|float|'
        results = self.machine.config_processor.validate_config_item2(
            validation_string, 'test_failure_info', 1.0)
        self.assertAlmostEqual(results, 1.0, .01)

        # test bool validations

        validation_string = 'single|bool|'
        results = self.machine.config_processor.validate_config_item2(
            validation_string, 'test_failure_info', 'f')
        self.assertFalse(results)

        validation_string = 'single|bool|'
        results = self.machine.config_processor.validate_config_item2(
            validation_string, 'test_failure_info', 'false')
        self.assertFalse(results)

        validation_string = 'single|bool|'
        results = self.machine.config_processor.validate_config_item2(
            validation_string, 'test_failure_info', False)
        self.assertFalse(results)