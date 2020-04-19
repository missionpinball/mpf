"""Test Switch Position Mixin."""
from unittest import TestCase
from mpf.commands.create_config import Command
from unittest.mock import call, patch, mock_open

class TestCommandCreateConfig(TestCase):

    @patch('os.makedirs')
    def test_get_create_mode(self, os_makedirs):
        with patch("builtins.open", mock_open()) as mock_file:
            Command.create_mode_structure("testmode", "/home/test/modes", "/home/test/")
            mock_file.assert_called_with("/home/test/modes/testmode/config/testmode.yaml", "w")
            expected_calls = [call("/home/test/modes"), call("/home/test/modes/testmode/config")]
            os_makedirs.assert_has_calls(expected_calls)

    @patch('os.makedirs')
    def test_get_create_machine_config(self, os_makedirs):
        with patch("builtins.open", mock_open()) as mock_file:
            Command.create_machine_config_structure("testmachine", "/home/testmachine")

            with open("/home/testmachine/config/config.yaml", "w") as handle_config:
                handle_config.write.assert_any_call("#config_version=5")

            mock_file.assert_any_call("/home/testmachine/config/config.yaml", "w")
            mock_file.assert_any_call("/home/testmachine/tests/test_testmachine.yaml", "w")

            expected_calls = [call("/home/testmachine"), call("/home/testmachine/config"), call("/home/testmachine/tests")]
            os_makedirs.assert_has_calls(expected_calls)

    @patch('os.makedirs')
    def test_get_create_shows(self, os_makedirs):
        with patch("builtins.open", mock_open()) as mock_file:
            Command.create_show_structure("testshow", "/home/test/shows", "/home/test/")
            mock_file.assert_called_with("/home/test/shows/testshow.yaml", "w")
            os_makedirs.assert_called_once_with("/home/test/shows")



