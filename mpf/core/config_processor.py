"""Contains the Config and CaseInsensitiveDict base classes"""

import logging
import os
import sys

from mpf.core.file_manager import FileManager
from mpf.core.utility_functions import Util
from mpf.core.case_insensitive_dict import CaseInsensitiveDict


class ConfigProcessor(object):
    config_spec = None

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger('ConfigProcessor')
        self.machine_sections = dict()
        '''dict of the methods that will process machine scripts and shows.'''
        self.mode_sections = dict()
        '''dict of the methods that will process mode scripts and shows.'''

    def register_load_methods(self):
        for section in self.mode_sections:
            self.machine.mode_controller.register_load_method(
                    load_method=self.process_mode_config,
                    config_section_name=section, section=section)

    def process_config_file(self, section_dict, config):
        """Called to process a config file (can be a mode or machine config).
        """
        for section in section_dict:
            if section in section_dict and section in config:
                self.process_localized_config_section(config=config[section],
                                                      section=section)

    def process_mode_config(self, config, mode, mode_path, section, **kwargs):
        del mode
        del mode_path
        del kwargs
        self.process_localized_config_section(config, section)

    def process_localized_config_section(self, config, section):
        """Processes a single key within a config file.

        Args:
            config: The subsection of a config dict to process
            section: The name of the section, either 'scripts' or 'shows'.

        """
        self.machine_sections[section](config)

    @staticmethod
    def set_machine_path(machine_path, machine_files_default='machine_files'):
        # If the machine folder value passed starts with a forward or
        # backward slash, then we assume it's from the mpf root. Otherwise we
        # assume it's in the mpf/machine_files folder
        if machine_path.startswith('/') or machine_path.startswith('\\'):
            machine_path = machine_path
        else:
            machine_path = os.path.join(machine_files_default, machine_path)

        machine_path = os.path.abspath(machine_path)
        logging.info("Machine path: %s", machine_path)

        # Add the machine folder to sys.path so we can import modules from it
        sys.path.insert(0, machine_path)
        return machine_path

    @staticmethod
    def load_machine_config(config_file_list, machine_path,
                            config_path='config', existing_config=None):
        machine_config = None
        for num, config_file in enumerate(config_file_list):

            if not existing_config:
                machine_config = CaseInsensitiveDict()
            else:
                machine_config = existing_config

            if not (config_file.startswith('/') or config_file.startswith('\\')):
                config_file = os.path.join(machine_path, config_path,
                                           config_file)

            logging.info("Machine config file #%s: %s", num + 1, config_file)

            machine_config = Util.dict_merge(machine_config,
                                             ConfigProcessor.load_config_file(
                                                 config_file))

        return machine_config

    @staticmethod
    def load_config_file(filename, verify_version=True, halt_on_error=True):
        config = FileManager.load(filename, verify_version, halt_on_error)

        try:
            if 'config' in config:
                path = os.path.split(filename)[0]

                for file in Util.string_to_list(config['config']):
                    full_file = os.path.join(path, file)
                    config = Util.dict_merge(config,
                                             ConfigProcessor.load_config_file(
                                                 full_file))
            return config
        except TypeError:
            return dict()
