import unittest
from ruamel.yaml.constructor import DuplicateKeyError
from mpf.file_interfaces.yaml_interface import YamlInterface


class TestYamlInterface(unittest.TestCase):

    def test_duplicate_key(self):
        yaml_str = '''
a: 1
b: 2
a: 3
'''
        with self.assertRaises(DuplicateKeyError):
            YamlInterface.process(yaml_str)

    def test_yaml_interface(self):

        config = """

str_1: "+1"
str_2: "032"
str_3: on
str_4: off
str_5: "123e45"
str_6: hi
str_7: 2:10
str_8: 2:10.1
bool_3: true
bool_4: false
bool_5: True
bool_6: False
int_1: 123

        """

        values = {
            "str_1": "+1",
            "str_2": "032",
            "str_3": "on",
            "str_4": "off",
            "str_5": "123e45",
            "str_6": "hi",
            "str_7": "2:10",
            "str_8": "2:10.1",
            "bool_3": True,
            "bool_4": False,
            "bool_5": True,
            "bool_6": False,
            "int_1": 123,
        }

        parsed_config = YamlInterface.process(config)

        for k, v in parsed_config.items():
            if not type(v) is eval(k.split('_')[0]):
                raise AssertionError('YAML value "{}" is {}, not {}'.format(v,
                    type(v), eval(k.split('_')[0])))
            self.assertEqual(values[k], v)
