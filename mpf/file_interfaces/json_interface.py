"""Contains the JsonInterface class for reading & writing to YAML files"""

# json_interface.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import os
import sys
import version

import json

from mpf.system.config import FileInterface
from mpf.system.utility_functions import Util


class JsonInterface(FileInterface):

    file_types = ['.json']

    def check_config_file_version(self, filename):
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
            return {self.byteify(key):self.byteify(value) for key, value in input.iteritems()}
        elif isinstance(input, list):
            return [self.byteify(element) for element in input]
        elif isinstance(input, unicode):
            return input.encode('utf-8')
        else:
            return input

    def save(self, filename, data):
        pass

file_interface_class = JsonInterface


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
