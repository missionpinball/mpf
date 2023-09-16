"""Test Switch Position Mixin."""
import os
from unittest import TestCase
from mpf.commands.create_config import Command
from unittest.mock import call, patch, mock_open

class TestCommandCreateConfig(TestCase):

    @patch('os.makedirs')
    def test_get_create_mode(self, os_makedirs):
        with patch("builtins.open", mock_open()) as mock_file:
            Command.create_mode_structure("testmode", os.path.normpath("/home/test/modes"), os.path.normpath("/home/test/"))
            mock_file.assert_called_with(os.path.normpath("/home/test/modes/testmode/config/testmode.yaml"), "w")
            expected_calls = [call(os.path.normpath("/home/test/modes")), call(os.path.normpath("/home/test/modes/testmode/config"))]
            os_makedirs.assert_has_calls(expected_calls)

    @patch('os.makedirs')
    def test_get_create_machine_config(self, os_makedirs):
        with patch("builtins.open", mock_open()) as mock_file:
            Command.create_machine_config_structure("testmachine", os.path.normpath("/home/testmachine"))

            with open(os.path.normpath("/home/testmachine/config/config.yaml"), "w") as handle_config:
                handle_config.write.assert_any_call("#config_version=6")

            mock_file.assert_any_call(os.path.normpath("/home/testmachine/config/config.yaml"), "w")

            mock_file.assert_any_call(os.path.normpath("/home/testmachine/tests/test_testmachine.yaml"), "w")

            expected_calls = [call(os.path.normpath("/home/testmachine")), call(os.path.normpath("/home/testmachine/config")), call(os.path.normpath("/home/testmachine/tests"))]
            os_makedirs.assert_has_calls(expected_calls)

    @patch('os.makedirs')
    def test_get_create_shows(self, os_makedirs):
        with patch("builtins.open", mock_open()) as mock_file:
            Command.create_show_structure("testshow", os.path.normpath("/home/test/shows"), os.path.normpath("/home/test/"))
            mock_file.assert_called_with(os.path.normpath("/home/test/shows/testshow.yaml"), "w")
            os_makedirs.assert_called_once_with(os.path.normpath("/home/test/shows"))
