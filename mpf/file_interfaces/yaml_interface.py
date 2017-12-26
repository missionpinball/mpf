"""Contains the YamlInterface class for reading & writing YAML files.

Fixes for octal and boolean values are from here:
http://stackoverflow.com/questions/32965846/cant-parse-yaml-correctly/
"""
import copy
import logging
import re

from typing import Any, Iterable
from typing import Dict

import collections
import ruamel.yaml as yaml
from ruamel.yaml.reader import Reader
from ruamel.yaml.resolver import BaseResolver, Resolver
from ruamel.yaml.scanner import Scanner
from ruamel.yaml.parser_ import Parser
from ruamel.yaml.composer import Composer
from ruamel.yaml.constructor import Constructor, ConstructorError

from mpf.core.file_manager import FileInterface, FileManager
from mpf.core.utility_functions import Util
from mpf._version import __version__, __config_version__

log = logging.getLogger('YAML Interface')


class MpfResolver(BaseResolver):

    """Resolver with mentioned fixes."""

MpfResolver.add_implicit_resolver(
    # Process any item beginning with a plus sign (+) as a string
    u'tag:yaml.org,2002:str',
    re.compile(
        u'''^(\\+([0-9a-zA-Z .]+))$''',
        re.X),
    list(u'+'))

MpfResolver.add_implicit_resolver(
    # Process any 3+ digit number with a leading zero as a string
    u'tag:yaml.org,2002:str',
    re.compile(
        u'''^(?:(0[0-9]{2,}))$''',
        re.X),
    list(u'0'))

MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:bool',
    re.compile(
        u'''^(?:true|True|TRUE|false|False|FALSE|yes|Yes|YES|no|No|NO)$''',
        re.X), list(u'tTfFyYnN'))

MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:float',
    re.compile(u'''^(?:
     [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*
    |\\.[0-9_]+
    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\\.[0-9_]*)$''', re.X),
    list(u'-+0123456789.'))

MpfResolver.add_implicit_resolver(
    u'tag:yaml.org,2002:int',
    re.compile(u'''^(?:[-+]?0b[0-1_]+
    |[-+]?[0-9]+
    |[-+]?0o?[0-7_]+
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


class MpfConstructor(Constructor):

    """Constructor with fix."""

    def construct_mapping(self, node, deep=False):
        """Construct mapping but raise error when a section is defined twice.

        From: http://stackoverflow.com/questions/34358974/how-to-prevent-re-definition-of-keys-in-yaml
        """
        if not isinstance(node, yaml.MappingNode):  # pragma: no cover
            raise ConstructorError(problem="expected a mapping node, but found %s" % node.id,
                                   problem_mark=node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            # keys can be list -> deep
            key = self.construct_object(key_node, deep=True)
            # lists are not hashable, but tuples are
            if not isinstance(key, collections.Hashable):   # pragma: no cover
                if isinstance(key, list):
                    key = tuple(key)
            if not isinstance(key, collections.Hashable):   # pragma: no cover
                raise ConstructorError(
                    "while constructing a mapping", node.start_mark,
                    "found unhashable key", key_node.start_mark)

            value = self.construct_object(value_node, deep=deep)
            # next two lines differ from original
            if key in mapping:
                raise KeyError("Key \"{}\" was defined multiple times in config {}".
                               format(key, key_node.start_mark))
            mapping[key] = value
        return mapping


class MpfLoader(Reader, Scanner, Parser, Composer, MpfConstructor, MpfResolver):

    """Config loader."""

    def __init__(self, stream):
        """Initialise loader."""
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        MpfConstructor.__init__(self)
        MpfResolver.__init__(self)


for ch in list(u'yYnNoO'):
    del Resolver.yaml_implicit_resolvers[ch]


class YamlInterface(FileInterface):

    """File interface for yaml files."""

    file_types = ['.yaml', '.yml']
    cache = False
    file_cache = dict()     # type: Dict[str, Any]

    @staticmethod
    def get_config_file_version(filename: str) -> int:
        """Return config file version."""
        with open(filename, encoding='utf8') as f:
            file_version = f.readline().split('config_version=')[-1:][0]

        try:
            return int(file_version)
        except ValueError:
            return 0

    @staticmethod
    def get_show_file_version(filename: str) -> int:
        """Return show file version."""
        with open(filename, encoding='utf8') as f:
            try:
                file_version = f.readline().split('show_version=')[-1:][0]
            except ValueError:  # pragma: no cover
                return 0
        try:
            return int(file_version)
        except ValueError:  # pragma: no cover
            return 0

    @staticmethod
    def check_config_file_version(filename: str) -> bool:
        """Check to see if the version of the file name passed matches the config version MPF needs.

        Args:
            filename: The file with path to check.

        Raises:
            exception if the version of the file doesn't match what MPF needs.
        """
        filename = FileManager.locate_file(filename)
        file_interface = FileManager.get_file_interface(filename)
        file_version = file_interface.get_config_file_version(filename)

        if file_version != int(__config_version__):
            log.error("Config file %s is version %s. MPF %s requires "
                      "version %s", filename, file_version,
                      __version__, __config_version__)

            # TODO remove this line when migrator is done

            log.error("We have not created the config file migration tool yet"
                      " for v5. In the meantime, see https://github.com/missionpinball/mpf/issues/897"
                      " for a list of changes between config versions 4 and 5.")

            # TODO uncomment these and update links when migrator is done

            # log.error("Use the Config File Migrator to automatically "
            #           "migrate your config file to the latest version.")
            # log.error("Migration tool: https://missionpinball.com/docs/tools/config-file-migrator/")
            # log.error("More info on config version %s: "
            #           "http://docs.missionpinball.org/docs/configuration-file"
            #           "-reference/important-config-file-concepts/config_version/config-version-%s/",
            #           __config_version__, __config_version__)
            return False
        else:
            return True

    def load(self, filename, verify_version=True, halt_on_error=True) -> dict:
        """Load a YAML file from disk.

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
        if self.cache and filename in self.file_cache:
            return copy.deepcopy(self.file_cache[filename])

        if verify_version and not self.check_config_file_version(filename):
            raise ValueError("Config file version mismatch: {}".format(filename))

        config = dict()     # type: dict

        try:
            self.log.debug("Loading file: %s", filename)

            with open(filename, encoding='utf8') as f:
                config = self.process(f)
        except Exception as e:   # pylint: disable-msg=broad-except
            if hasattr(e, 'problem_mark'):
                mark = e.problem_mark
                msg = "YAML error found in file {}. Line {}," \
                      "Position {}: {}".format(filename, mark.line + 1, mark.column + 1, e)
            else:
                msg = "Error found in file {}: {}".format(filename, e)

            if halt_on_error:
                raise ValueError(msg)
            else:
                self.log.warning(msg)

        if self.cache and config:
            self.file_cache[filename] = copy.deepcopy(config)

        return config

    @staticmethod
    def process(data_string: Iterable[str]) -> dict:
        """Parse yaml from a string."""
        return yaml.load(data_string, Loader=MpfLoader)

    def save(self, filename: str, data: dict) -> None:   # pragma: no cover
        """Save config to yaml file."""
        with open(filename, 'w', encoding='utf8') as output_file:
            output_file.write(yaml.dump(data, default_flow_style=False))

file_interface_class = YamlInterface
