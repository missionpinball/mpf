"""Contains the YamlInterface class for reading & writing to YAML files"""

# yaml_interface.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os
import sys
import version

import yaml

from mpf.system.config import Config


class YamlInterface(object):

    file_types = ['.yaml', '.yml']

    def __init__(self):
        self.log = logging.getLogger('YAML Config Processor')

    def find_file(self, filename):
        """Tests whether the passed file is valid. If the file does not have an
        externsion, this method will test for files with that base name with
        all the extensions it can read.

        Args:
            filename: Full absolute path of a file to check, with or without
                an extension.

        Returns:
            False if a file is not found.
            Tuple of (full file with path, extension) if a file is found

        """
        if not os.path.splitext(filename)[1]:
            # file has no extension

            for extension in YamlInterface.file_types:
                if os.path.isfile(filename + extension):
                    return os.path.abspath(filename + extension), extension
            else:
                return False
        else:
            return filename, os.path.splitext(filename)[1]

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
                file_version = int(file_version)
            except ValueError:
                file_version = 0

            if file_version != int(version.__config_version__):
                self.log.error("Config file %s is version %s. MPF %s requires "
                          "version %s", filename, file_version,
                          version.__version__, version.__config_version__)
                self.log.error("Use the Config File Migrator to automatically "
                          "migrate your config file to the latest version.")
                self.log.error("Migration tool: "
                           "https://missionpinball.com/docs/tools/config-file-migrator/")
                self.log.error("More info on config version %s: %s",
                          version.__config_version__,
                          version.__config_version_url__)
                raise('Config file version mismatch')

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
        if verify_version:
            self.check_config_file_version(filename)

        try:
            self.log.debug("Loading configuration file: %s", filename)
            config = Config.keys_to_lower(yaml.load(open(filename, 'r')))
        except yaml.YAMLError, exc:
            if hasattr(exc, 'problem_mark'):
                mark = exc.problem_mark
                self.log.critical("Error found in config file %s. Line %s, "
                             "Position %s", filename, mark.line+1,
                             mark.column+1)
                sys.exit()
        except:
            self.log.critical("Couldn't load from file: %s", filename)
            raise

        return config

    def save(self, filename, data):
        pass

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
