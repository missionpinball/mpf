import os
from unittest import TestCase

import mpf
from mpf.core.config_processor import ConfigProcessor

from mpf.core.config_loader import YamlMultifileConfigLoader


class TestConfigLoader(TestCase):

    def test_yaml_multifile_config_loader(self):

        machine_path = os.path.abspath(os.path.join(mpf.core.__path__[0], os.pardir,
                                                    "tests/machine_files/config_loader/"))

        config_file = ["config.yaml"]

        config_loader = YamlMultifileConfigLoader(machine_path, config_file, False, False)
        config = config_loader.load_mpf_config()

        self.assertTrue(config.get_config_spec())
        self.assertTrue(config.get_machine_config())
        self.assertTrue(config.get_mode_config("attract"))
        self.assertTrue(config.get_mode_config("game"))
        self.assertTrue(config.get_mode_config("mode1"))
        self.assertTrue(config.get_mode_config("mode2"))
        self.assertTrue(config.get_show_config("mode1_show"))
        self.assertTrue(config.get_show_config("show1"))
        self.assertCountEqual(
            ['flash', 'on', 'off', 'led_color', 'flash_color', 'test_show', 'show1', 'game_show', 'mode1_show'],
            config.get_shows())
