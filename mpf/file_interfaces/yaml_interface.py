"""Contains the YamlInterface class for reading & writing YAML files"""

# yaml_interface.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import sys
import yaml
from mpf.system.config import Config
from mpf.system.file_manager import FileInterface
from mpf.system.utility_functions import Util


class YamlInterface(FileInterface):

    file_types = ['.yaml', '.yml']

    @staticmethod
    def get_config_file_version(filename):

        with open(filename) as f:
            file_version = f.readline().split('config_version=')[-1:][0]

        try:
            return int(file_version)
        except ValueError:
            return 0

    def load(self, filename, verify_version=True, halt_on_error=False):
        """Loads a YAML file from disk.

        Args:
            filename: The file to load.
            verify_version: Boolean which specifies whether this method should
                verify whether this file's config_version is compatible with
                this version of MPF. Default is True.
            halt_on_error: Boolean which controls what happens if the file
                can't be loaded. (Not found, invalid format, etc. If True, MPF
                will raise an error and exit. If False, an empty config
                dictionary will be returned.

        Returns:
            A dictionary of the settings from this YAML file.

        """
        if verify_version and not Config.check_config_file_version(filename):
            raise Exception("Config file version mismatch: {}".
                            format(filename))

        try:
            self.log.debug("Loading configuration file: %s", filename)

            with open(filename, 'r') as f:
                config = Util.keys_to_lower(yaml.load(f))
        except yaml.YAMLError as exc:
            if hasattr(exc, 'problem_mark'):
                mark = exc.problem_mark
                self.log.critical("Error found in config file %s. Line %s, "
                             "Position %s", filename, mark.line+1,
                             mark.column+1)

            if halt_on_error:
                sys.exit()
            else:
                config = dict()

        except:
            self.log.critical("Couldn't load from file: %s", filename)

            if halt_on_error:
                sys.exit()
            else:
                config = dict()

        return config

    def save(self, filename, data):
        with open(filename, 'w') as output_file:
            output_file.write(yaml.dump(data, default_flow_style=False))

file_interface_class = YamlInterface


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
