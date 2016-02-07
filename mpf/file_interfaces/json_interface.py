"""Contains the JsonInterface class for reading & writing to JSON files"""

import os
import sys
import version

import json

from mpf.core.file_manager import FileInterface
from mpf.core.utility_functions import Util


class JsonInterface(FileInterface):

    file_types = ['.json']

    def get_config_file_version(self, filename):
        """Checks to see if the filename passed matches the config version MPF
        needs.

        Args:
            filename: The file with path to check.

        Raises:
            exception if the version of the file doesn't match what MPF needs.

        """
        with open(filename) as f:
            file_version = f.readline().split('config_version=')[-1:][0]

            try:
                return int(file_version)
            except ValueError:
                return 0

    def load(self, filename, verify_version=True):
        """Loads a YAML file from disk.

        Args:
            filename: The file to load.
            verify_version: Boolean which specifies whether this method should
                verify whether this file's config_version is compatible with
                this version of MPF. Default is True.

        Returns:
            A dictionary of the settings from this YAML file.

        """

        config = Util.keys_to_lower(self.byteify(json.load(open(filename, 'r'))))

        # if verify_version:
        #     self.check_config_file_version(filename)
        #
        # try:
        #     self.log.debug("Loading configuration file: %s", filename)
        #     config = Util.keys_to_lower(json.loads(open(filename, 'r')))
        # except yaml.YAMLError, exc:
        #     if hasattr(exc, 'problem_mark'):
        #         mark = exc.problem_mark
        #         self.log.critical("Error found in config file %s. Line %s, "
        #                      "Position %s", filename, mark.line+1,
        #                      mark.column+1)
        #         sys.exit()
        # except:
        #     self.log.critical("Couldn't load from file: %s", filename)
        #     raise

        return config

    def byteify(self, input):
        if isinstance(input, dict):
            return {self.byteify(key):self.byteify(value) for key, value in input.items()}
        elif isinstance(input, list):
            return [self.byteify(element) for element in input]
        elif isinstance(input, str):
            return input.encode('utf-8')
        else:
            return input

    def save(self, filename, data):
        pass

file_interface_class = JsonInterface
