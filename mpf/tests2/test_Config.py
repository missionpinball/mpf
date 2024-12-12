from mpf.core.config_validator import ValidationPath

from mpf.core.utility_functions import Util
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.tests.MpfTestCase import MpfTestCase
from mpf._version import log_url


class TestConfig(MpfTestCase):

    def get_config_file(self):
        return 'test_config_interface.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/config_interface/'

    def setUp(self):
        self.machine_spec_patches['test_section'] = dict(__valid_in__='machine')
        super().setUp()

    def test_config_file(self):
        # true, True, yes, Yes values should be True
        self.assertIs(True, self.machine.config['test_section']['true_key1'])
        self.assertIs(True, self.machine.config['test_section']['true_key2'])

        # false, False, no, No values should be False
        self.assertIs(False, self.machine.config['test_section']['false_key1'])
        self.assertIs(False, self.machine.config['test_section']['false_key2'])

        # on, off values should be strings
        self.assertEqual('on', self.machine.config['test_section']['on_string'])
        self.assertEqual('off', self.machine.config['test_section']['off_string'])

        # 6400, 6, 07 should be ints
        self.assertEqual(6400, self.machine.config['test_section']['int_6400'])
        self.assertEqual(6, self.machine.config['test_section']['int_6'])
        self.assertEqual(7, self.machine.config['test_section']['int_7'])

        # 00ff00, 003200 should be strings
        self.assertEqual('00ff00', self.machine.config['test_section']['str_00ff00'])
        self.assertEqual('003200', self.machine.config['test_section']['str_003200'])

        # +5, +0.5 should be strings
        self.assertEqual('+5', self.machine.config['test_section']['str_plus5'])
        self.assertEqual('+0.5', self.machine.config['test_section']['str_plus0point5'])

        # keys should keep case
        self.assertIn('case_sensitive_1', self.machine.config['test_section'])
        self.assertIn('Case_sensitive_2', self.machine.config['test_section'])
        self.assertIn('case_sensitive_3', self.machine.config['test_section'])

        # values should be case sensitive
        self.assertEqual(self.machine.config['test_section']['case_sensitive_1'], 'test')
        self.assertEqual(self.machine.config['test_section']['Case_sensitive_2'], 'test')
        self.assertEqual(self.machine.config['test_section']['case_sensitive_3'], 'Test')

    def test_config_validator(self):
        validation_failure_info = ValidationPath(ValidationPath(ValidationPath(None, "key"), "entry"), "subkey")
        # test config spec syntax error
        self.assertRaises(ValueError,
                          self.machine.config_validator.validate_config_item,
                          'single|int'.split("|"), None, None)

        # test default required, source is int
        validation_string = 'single|int|'.split("|")
        results = self.machine.config_validator.validate_config_item(
                validation_string, 'test_failure_info', 0)
        self.assertEqual(results, 0)

        # test default provided, source overrides default
        validation_string = 'single|int|0'.split("|")
        results = self.machine.config_validator.validate_config_item(
                validation_string, 'test_failure_info', 1)
        self.assertEqual(results, 1)

        # test source type is converted to int
        validation_string = 'single|int|0'.split("|")
        results = self.machine.config_validator.validate_config_item(
                validation_string, 'test_failure_info', '1')
        self.assertEqual(results, 1)

        # test default when no source is present
        validation_string = 'single|int|1'.split("|")
        results = self.machine.config_validator.validate_config_item(
                validation_string, 'test_failure_info')  # no item in config
        self.assertEqual(results, 1)

        # test default required with source missing raises error
        validation_string = 'single|int|'.split("|")  # default required
        self.assertRaises(ConfigFileError,
                          self.machine.config_validator.validate_config_item,
                          validation_string, ValidationPath(None, "test"))  # no item

        # test broken int
        validation_string = 'single|int|'.split("|")  # default required
        with self.assertRaises(AssertionError) as e:
            results = self.machine.config_validator.validate_config_item(
                validation_string, validation_failure_info, '1s')

        # test int with range
        validation_string = 'single|int(0,10)|'.split("|")

        results = self.machine.config_validator.validate_config_item(
            validation_string, validation_failure_info, '0')
        self.assertEqual(results, 0)

        results = self.machine.config_validator.validate_config_item(
            validation_string, validation_failure_info, '7')
        self.assertEqual(results, 7)

        results = self.machine.config_validator.validate_config_item(
            validation_string, validation_failure_info, '10')
        self.assertEqual(results, 10)

        with self.assertRaises(AssertionError) as e:
            results = self.machine.config_validator.validate_config_item(
                validation_string, validation_failure_info, '-1')

        with self.assertRaises(AssertionError) as e:
            results = self.machine.config_validator.validate_config_item(
                validation_string, validation_failure_info, 11)

        # int with open end
        validation_string = 'single|int(0,NONE)|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, validation_failure_info, 999)
        self.assertEqual(results, 999)

        with self.assertRaises(AssertionError) as e:
            results = self.machine.config_validator.validate_config_item(
                validation_string, validation_failure_info, -1)

        # test str validations

        validation_string = 'single|str|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'hello')
        self.assertEqual(results, 'hello')
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 1)
        self.assertEqual(results, '1')
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', "none")
        self.assertEqual(results, None)

        # test lstr
        validation_string = 'single|lstr|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'HellO')
        self.assertEqual(results, 'hello')
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'hello')
        self.assertEqual(results, 'hello')
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'H1')
        self.assertEqual(results, 'h1')
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'none')
        self.assertEqual(results, None)

        # test float validations

        validation_string = 'single|float|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 1)
        self.assertAlmostEqual(results, 1.0, .01)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '1')
        self.assertAlmostEqual(results, 1.0, .01)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 1.0)
        self.assertAlmostEqual(results, 1.0, .01)

        # test num validations

        validation_string = 'single|num|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 1.0)
        self.assertAlmostEqual(results, 1.0, .01)
        self.assertEqual(type(results), float)
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '1.0')
        self.assertAlmostEqual(results, 1.0, .01)
        self.assertEqual(type(results), float)
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 1)
        self.assertEqual(results, 1)
        self.assertIs(type(results), int)
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '1')
        self.assertEqual(results, 1)
        self.assertIs(type(results), int)

        # test int_from_hex
        validation_string = 'single|int_from_hex|ff'.split("|")
        results = self.machine.config_validator.validate_config_item(
                validation_string, 'test_failure_info')  # no item in config
        self.assertEqual(results, 255)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '0a')
        self.assertEqual(results, 10)

        with self.assertRaises(AssertionError):
            self.machine.config_validator.validate_config_item(
                validation_string, validation_failure_info, 'white')

        # test bool validations
        validation_string = 'single|bool|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'f')
        self.assertFalse(results)

        validation_string = 'single|boolean|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'f')
        self.assertFalse(results)

        validation_string = 'single|bool|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'false')
        self.assertFalse(results)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', False)
        self.assertFalse(results)

        # test bools that are YAML strings but MPF bools
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'no')
        self.assertFalse(results)
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'off')
        self.assertFalse(results)
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'yes')
        self.assertTrue(results)
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'on')
        self.assertTrue(results)

        # test bool_int validations
        validation_string = 'single|bool_int|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'f')
        self.assertEqual(0, results)
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 't')
        self.assertEqual(1, results)
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'false')
        self.assertEqual(0, results)
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', False)
        self.assertEqual(0, results)
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', "True")
        self.assertEqual(1, results)

        # test ms conversions
        validation_string = 'single|ms|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 100)
        self.assertEqual(results, 100)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 100.0)
        self.assertEqual(results, 100)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '100')
        self.assertEqual(results, 100)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '100ms')
        self.assertEqual(results, 100)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '1s')
        self.assertEqual(results, 1000)

        # test sec conversions
        validation_string = 'single|secs|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 100)
        self.assertEqual(results, 100)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 100.0)
        self.assertEqual(results, 100)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '100')
        self.assertEqual(results, 100)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '100s')
        self.assertEqual(results, 100)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '100ms')
        self.assertEqual(results, .1)

        # test single list conversions
        # (this just test it gets converted to a list since string_to_list
        # is tested earlier)
        validation_string = 'single|list|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'hi')
        self.assertEqual(results, ['hi'])

        # Test lists
        validation_string = 'list|int|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '1, 2, 3')
        self.assertEqual(results, [1, 2, 3])

        # Test set
        validation_string = 'set|int|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '1, 2, 3')
        self.assertEqual(results, {1, 2, 3})

        # Test dict
        validation_string = 'dict|str:int|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', dict(hello='1'))
        self.assertEqual(results, dict(hello=1))

        # Test color
        validation_string = 'single|color|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'red')
        self.assertEqual(results, (255, 0, 0))

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'ff0000')
        self.assertEqual(results, (255, 0, 0))

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '255, 0, 0')
        self.assertEqual(results, (255, 0, 0))

        # Test kivycolor
        validation_string = 'single|kivycolor|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'red')
        self.assertEqual(results, [1, 0, 0, 1])

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'ff0000')
        self.assertEqual(results, [1, 0, 0, 1])

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '255, 0, 0')
        self.assertEqual(results, [1, 0, 0, 1])

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 'ff000000')
        self.assertEqual(results, [1, 0, 0, 0])

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '255, 0, 0, 255')
        self.assertEqual(results, [1, 0, 0, 1])

        # Test gain
        validation_string = 'single|gain|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '0.0')
        self.assertEqual(results, 0.0)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '1.0')
        self.assertEqual(results, 1.0)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '2.0')
        self.assertEqual(results, 1.0)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '-3')
        self.assertEqual(results, 0.0)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '0 db')
        self.assertEqual(results, 1.0)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '-inf')
        self.assertEqual(results, 0.0)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '-3 DB')
        self.assertAlmostEqual(results, 0.707945784)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '-6db')
        self.assertAlmostEqual(results, 0.501187233)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '-17.5db')
        self.assertAlmostEqual(results, 0.133352143)

        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '3db')
        self.assertEqual(results, 1.0)

        # test pow2
        validation_string = 'single|pow2|'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', 128)
        self.assertEqual(results, 128)
        results = self.machine.config_validator.validate_config_item(
            validation_string, 'test_failure_info', '128')
        self.assertEqual(results, '128')

        with self.assertRaises(AssertionError):
            self.machine.config_validator.validate_config_item(
                validation_string, validation_failure_info, '127')

        # test enum
        validation_string = 'single|enum(None,test)|None'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, validation_failure_info, None)
        self.assertEqual(None, results)

        results = self.machine.config_validator.validate_config_item(
            validation_string, validation_failure_info, "None")
        self.assertEqual(None, results)

        results = self.machine.config_validator.validate_config_item(
            validation_string, validation_failure_info, "test")
        self.assertEqual("test", results)

        self.maxDiff = None
        with self.assertRaises(AssertionError) as e:
            self.machine.config_validator.validate_config_item(
                validation_string, validation_failure_info, 'something else')
        self.assertEqual('Config File Error in ConfigValidator: Config validation error: Entry '
                         'key:entry:subkey = "something else" is not valid. Entry "something else" is not valid for enum. '
                         'Valid values are: None,test Error Code: CFE-ConfigValidator-5 '
                         '({})'.format(log_url.format("CFE-ConfigValidator-5")), str(e.exception))

        # test enum with 'NO' setting
        validation_string = 'single|enum(nc,no)|no'.split("|")
        results = self.machine.config_validator.validate_config_item(
            validation_string, validation_failure_info, False)
        self.assertEqual('no', results)

    def test_config_merge(self):
        a = {"test": {"a": [1], "b": [2, 3]}, "test2": 2}
        b = {"test": {"a": [3], "c": 7}}
        c = Util.dict_merge(a, b)
        self.assertEqual({'test': {'a': [1, 3], 'b': [2, 3], 'c': 7}, 'test2': 2}, c)

        b2 = {"test": {"_overwrite": True, "a": [3], "c": 7}}
        c = Util.dict_merge(a, b2)
        self.assertEqual({'test': {'a': [3], 'c': 7}, 'test2': 2}, c)

        b3 = {"test": {"_delete": True}}
        c = Util.dict_merge(a, b3)
        self.assertEqual({'test2': 2}, c)
