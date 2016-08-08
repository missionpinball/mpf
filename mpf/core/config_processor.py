"""Contains the Config and CaseInsensitiveDict base classes."""

import logging
import os

from mpf.core.file_manager import FileManager
from mpf.core.utility_functions import Util
from mpf.core.config_validator import ConfigValidator


class ConfigProcessor(object):

    """Config processor which loads the config."""

    config_spec = None

    def __init__(self, machine):
        """Initialise config processor."""
        self.machine = machine
        self.log = logging.getLogger('ConfigProcessor')
        self.machine_sections = dict()
        '''dict of the methods that will process machine scripts and shows.'''
        self.mode_sections = dict()
        '''dict of the methods that will process mode scripts and shows.'''

    def register_load_methods(self):
        """Register load method for modes."""
        for section in self.mode_sections:
            self.machine.mode_controller.register_load_method(
                load_method=self.process_mode_config,
                config_section_name=section, section=section)

    def process_config_file(self, section_dict, config):
        """Called to process a config file (can be a mode or machine config)."""
        for section in section_dict:
            if section in section_dict and section in config:
                self.process_localized_config_section(config=config[section],
                                                      section=section)

    def process_mode_config(self, config, mode, mode_path, section, **kwargs):
        """Process a mode config."""
        del mode
        del mode_path
        del kwargs
        self.process_localized_config_section(config, section)

    def process_localized_config_section(self, config, section):
        """Process a single key within a config file.

        Args:
            config: The subsection of a config dict to process
            section: The name of the section, either 'scripts' or 'shows'.

        """
        self.machine_sections[section](config)

    @staticmethod
    def load_config_file(filename, config_type, verify_version=True, halt_on_error=True):
        """Load a config file."""
        # config_type is str 'machine' or 'mode', which specifies whether this
        # file being loaded is a machine config or a mode config file
        config = FileManager.load(filename, verify_version, halt_on_error)

        if not ConfigValidator.config_spec:
            ConfigValidator.load_config_spec()

        for k in config.keys():
            try:
                if config_type not in ConfigValidator.config_spec[k][
                        '__valid_in__']:
                    raise ValueError('Found a "{}:" section in config file {}, '
                                     'but that section is not valid in {} config '
                                     'files.'.format(k, filename, config_type))
            except KeyError:
                raise ValueError('Found a "{}:" section in config file {}, '
                                 'but that section is not valid in {} config '
                                 'files.'.format(k, filename, config_type))

        try:
            if 'config' in config:
                path = os.path.split(filename)[0]

                for file in Util.string_to_list(config['config']):
                    full_file = os.path.join(path, file)
                    config = Util.dict_merge(config,
                                             ConfigProcessor.load_config_file(
                                                 full_file, config_type))
            return config
        except TypeError:
            return dict()
