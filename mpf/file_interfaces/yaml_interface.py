"""Contains the YamlInterface class for reading & writing YAML files"""

# yaml_interface.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

# yaml fixes for octal and boolean values are from here:
# http://stackoverflow.com/questions/32965846/cant-parse-yaml-correctly/

import logging
import re
import sys

import ruamel.yaml as yaml
from ruamel.yaml.reader import Reader
from ruamel.yaml.resolver import BaseResolver, Resolver
from ruamel.yaml.scanner import Scanner, RoundTripScanner
from ruamel.yaml.parser_ import Parser
from ruamel.yaml.composer import Composer
from ruamel.yaml.constructor import Constructor, RoundTripConstructor
from ruamel.yaml.compat import to_str

from mpf.system.file_manager import FileInterface, FileManager
from mpf.system.utility_functions import Util
import version

log = logging.getLogger('YAML Interface')

class MpfResolver(BaseResolver):
    pass

MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:str',
    re.compile(
        u'''^(?:(0[a-fA-F0-9]{5})|(0[a-fA-F0-9]{2}))$''',
        re.X),
    list(u'0'))

MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:bool',
    re.compile(
        u'''^(?:true|True|TRUE|false|False|FALSE|yes|Yes|YES|no|No|NO)$''',
        re.X),
        list(u'tTfFyYnN'))

MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:float',
    re.compile(u'''^(?:
     [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*(?:[eE][-+]?[0-9]+)?
    |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
    |\\.[0-9_]+(?:[eE][-+][0-9]+)?
    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\\.[0-9_]*
    |[-+]?\\.(?:inf|Inf|INF)
    |\\.(?:nan|NaN|NAN))$''', re.X),
    list(u'-+0123456789.'))

MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:int',
    re.compile(u'''^(?:[-+]?0b[0-1_]+
    |[-+]?[0-9]+
    |[-+]?0o?[0-7_]+
    |[-+]?(?:0|[1-9][0-9_]*)
    |[-+]?0x[0-9a-fA-F_]+
    |[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$''', re.X),
    list(u'-+0123456789'))

MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:merge',
    re.compile(u'^(?:<<)$'),
    [u'<'])

MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:null',
    re.compile(u'''^(?: ~
    |null|Null|NULL
    | )$''', re.X),
    [u'~', u'n', u'N', u''])

MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:timestamp',
    re.compile(u'''^(?:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]
    |[0-9][0-9][0-9][0-9] -[0-9][0-9]? -[0-9][0-9]?
    (?:[Tt]|[ \\t]+)[0-9][0-9]?
    :[0-9][0-9] :[0-9][0-9] (?:\\.[0-9]*)?
    (?:[ \\t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?)$''', re.X),
    list(u'0123456789'))

MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:value',
    re.compile(u'^(?:=)$'),
    [u'='])

# The following resolver is only for documentation purposes. It cannot work
# because plain scalars cannot start with '!', '&', or '*'.
MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:yaml',
    re.compile(u'^(?:!|&|\\*)$'),
    list(u'!&*'))


class MpfRoundTripConstructor(RoundTripConstructor):
    def construct_yaml_int(self, node):
        value = to_str(self.construct_scalar(node))
        value = value.replace('_', '')
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '0':
            return 0
        elif value.startswith('0b'):
            return sign*int(value[2:], 2)
        elif value.startswith('0x'):
            return sign*int(value[2:], 16)
        elif value.startswith('0o'):
            return sign*int(value[2:], 8)
        #elif value[0] == '0':
        #    return sign*int(value, 8)
        elif ':' in value:
            digits = [int(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*int(value)

class MpfConstructor(Constructor):
    def construct_yaml_int(self, node):
        value = to_str(self.construct_scalar(node))
        value = value.replace('_', '')
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '0':
            return 0
        elif value.startswith('0b'):
            return sign*int(value[2:], 2)
        elif value.startswith('0x'):
            return sign*int(value[2:], 16)
        elif value.startswith('0o'):
            return sign*int(value[2:], 8)
        #elif value[0] == '0':
        #    return sign*int(value, 8)
        elif ':' in value:
            digits = [int(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*int(value)

MpfRoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:int',
    MpfRoundTripConstructor.construct_yaml_int)

MpfConstructor.add_constructor(
    u'tag:yaml.org,2002:int',
    MpfConstructor.construct_yaml_int)


class MpfRoundTripLoader(Reader, RoundTripScanner, Parser,
                      Composer, MpfRoundTripConstructor, MpfResolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        RoundTripScanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        MpfRoundTripConstructor.__init__(self)
        MpfResolver.__init__(self)


class MpfLoader(Reader, Scanner, Parser, Composer, MpfConstructor, MpfResolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        MpfConstructor.__init__(self)
        MpfResolver.__init__(self)


for ch in list(u'yYnNoO'):
    del Resolver.yaml_implicit_resolvers[ch]


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

    @staticmethod
    def check_config_file_version(filename):
        """Checks to see if the version of the file name passed matches the
        config version MPF needs.

        Args:
            filename: The file with path to check.

        Raises:
            exception if the version of the file doesn't match what MPF needs.

        """
        filename = FileManager.locate_file(filename)
        file_interface = FileManager.get_file_interface(filename)
        file_version = file_interface.get_config_file_version(filename)

        if file_version != int(version.__config_version__):
            log.error("Config file %s is version %s. MPF %s requires "
                      "version %s", filename, file_version,
                      version.__version__, version.__config_version__)
            log.error("Use the Config File Migrator to automatically "
                      "migrate your config file to the latest version.")
            log.error("Migration tool: "
                       "https://missionpinball.com/docs/tools/config-file-migrator/")
            log.error("More info on config version %s: %s",
                      version.__config_version__,
                      version.__config_version_url__)
            return False
        else:
            return True

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
        if verify_version and not YamlInterface.check_config_file_version(filename):
            raise ValueError("Config file version mismatch: {}".
                            format(filename))

        try:
            self.log.debug("Loading configuration file: %s", filename)

            with open(filename, 'r') as f:
                config = Util.keys_to_lower(
                    yaml.load(f, Loader=MpfLoader))
        except yaml.YAMLError, exc:
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
