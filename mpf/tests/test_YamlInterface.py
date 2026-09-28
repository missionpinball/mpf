import unittest
import os
from unittest.mock import patch, mock_open, MagicMock
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

    @patch("mpf.file_interfaces.yaml_interface.open", new_callable=mock_open)
    @patch("os.fsync")
    def test_yaml_save_triggers_fsync(self, mock_os_fsync, mock_file_open):
        """Verify that saving a file forces a flush and an os.fsync call."""
        interface = YamlInterface()
        interface.log = MagicMock()

        mock_file_handle = mock_file_open.return_value
        mock_file_handle.fileno.return_value = 42

        interface.save("test_durability.yaml", {"high_score": 100000}, True)

        mock_file_handle.flush.assert_called()
        mock_os_fsync.assert_called_once_with(42)
        interface.log.error.assert_not_called()

    @patch("mpf.file_interfaces.yaml_interface.open", new_callable=mock_open)
    @patch("os.fsync")
    def test_yaml_save_handles_fsync_os_error_gracefully(self, mock_os_fsync, mock_file_open):
        """Ensure that if the OS throws an error during fsync, it is logged and caught."""
        interface = YamlInterface()
        interface.log = MagicMock()

        mock_file_handle = mock_file_open.return_value
        mock_file_handle.fileno.return_value = 42
        mock_os_fsync.side_effect = OSError(5, "Input/output error")

        interface.save("broken_disk.yaml", {"high_score": 100000}, True)
        interface.log.error.assert_called_once()
