import os
import unittest

from mpf._version import log_url

from mpf.core.config_processor import ConfigProcessor

from mpf.core.placeholder_manager import PlaceholderManager
from mpf.exceptions.config_file_error import ConfigFileError


class FakeMachine:

    def __init__(self):
        self.config = {
            "logging": {"console": {"placeholder_manager": "basic"}, "file": {"placeholder_manager": "basic"}}
        }
        self.options = {"production": False}
        self.placeholder_manager = PlaceholderManager(self)


class TestConfigProcessor(unittest.TestCase):

    def setUp(self):
        self.machine = FakeMachine()
        self.config_processor = ConfigProcessor(False, False)
        self.config_spec = self.config_processor.load_config_spec()
        self.maxDiff = None

    def test_load_with_subconfig(self):
        """Test successful load with subconfig."""
        config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   "machine_files/config_processor/working.yaml")
        config = self.config_processor.load_config_files_with_cache([config_file], "machine",
                                                                    config_spec=self.config_spec)

        self.assertEqual(
            {'config': ['working_subconfig.yaml'], 'lights': {'light1': {'number': 1}, 'light2': {'number': 2}},
             'switches': {'switch1': {'number': 1}}},
            config
        )

    def test_typo(self):
        """Test suggestion on typo."""
        config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   "machine_files/config_processor/typo.yaml")
        with self.assertRaises(ConfigFileError) as e:
            config = self.config_processor.load_config_files_with_cache([config_file], "machine",
                                                                        config_spec=self.config_spec)

        self.assertEqual('Config File Error in ConfigProcessor: Found a "light:" section in config '
                         'file {config_file}, '
                         'but that section name is unknown. Did you mean "lights:" instead?. Context: '
                         '{config_file} '
                         'Error Code: CFE-ConfigProcessor-3 ({})'.format(log_url.format("CFE-ConfigProcessor-3"),
                                                                         config_file=config_file),
                         str(e.exception))
