"""Contains the YamlInterface class for reading & writing YAML files.

Fixes for octal and boolean values are from here:
http://stackoverflow.com/questions/32965846/cant-parse-yaml-correctly/
"""
import copy
import logging
import re

import collections
import ruamel.yaml as yaml
from ruamel.yaml.reader import Reader
from ruamel.yaml.resolver import BaseResolver, Resolver
from ruamel.yaml.scanner import Scanner, RoundTripScanner
from ruamel.yaml.parser_ import Parser
from ruamel.yaml.composer import Composer
from ruamel.yaml.constructor import Constructor, RoundTripConstructor, ConstructorError
from ruamel.yaml.compat import to_str
from ruamel.yaml.dumper import RoundTripDumper

from mpf.core.file_manager import FileInterface, FileManager
from mpf.core.utility_functions import Util
from mpf._version import __version__, __config_version__

log = logging.getLogger('YAML Interface')


class MpfResolver(BaseResolver):

    """Resolver with mentioned fixes."""

    def __init__(self):
        """Initialise."""
        super().__init__()

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

    def __init__(self):
        """Initialise."""
        super().__init__()

    def construct_mapping(self, node, deep=False):
        """Construct mapping but raise error when a section is defined twice.

        From: http://stackoverflow.com/questions/34358974/how-to-prevent-re-definition-of-keys-in-yaml
        """
        if not isinstance(node, yaml.MappingNode):
            raise ConstructorError(
                None, None,
                "expected a mapping node, but found %s" % node.id,
                node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            # keys can be list -> deep
            key = self.construct_object(key_node, deep=True)
            # lists are not hashable, but tuples are
            if not isinstance(key, collections.Hashable):
                if isinstance(key, list):
                    key = tuple(key)
            if not isinstance(key, collections.Hashable):
                raise ConstructorError(
                    "while constructing a mapping", node.start_mark,
                    "found unhashable key", key_node.start_mark)

            value = self.construct_object(value_node, deep=deep)
            # next two lines differ from original
            if key in mapping:
                raise KeyError("Key \"{}\" was defined multiple times in config.".format(key))
            mapping[key] = value
        return mapping


class MpfRoundTripLoader(Reader, RoundTripScanner, Parser, Composer, RoundTripConstructor, MpfResolver):

    """Config loader which can roundtrip."""

    def __init__(self, stream):
        """Initialise loader."""
        Reader.__init__(self, stream)
        RoundTripScanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        RoundTripConstructor.__init__(self)
        MpfResolver.__init__(self)


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
    file_cache = dict()

    @staticmethod
    def get_config_file_version(filename):
        """Return config file version."""
        with open(filename, 'r', encoding='utf8') as f:
            file_version = f.readline().split('config_version=')[-1:][0]

        try:
            return int(file_version)
        except ValueError:
            return 0

    @staticmethod
    def get_show_file_version(filename):
        """Return show file version."""
        with open(filename, 'r', encoding='utf8') as f:
            try:
                file_version = f.readline().split('show_version=')[-1:][0]
            except ValueError:
                return 0
        try:
            return int(file_version)
        except ValueError:
            return 0

    @staticmethod
    def check_config_file_version(filename):
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
            log.error("Use the Config File Migrator to automatically "
                      "migrate your config file to the latest version.")
            log.error("Migration tool: https://missionpinball.com/docs/tools/config-file-migrator/")
            log.error("More info on config version %s: "
                      "http://docs.missionpinball.org/docs/configuration-file"
                      "-reference/important-config-file-concepts/config_version/config-version-%s/",
                      __config_version__, __config_version__)
            return False
        else:
            return True

    def load(self, filename, verify_version=True, halt_on_error=True,
             round_trip=False):
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
            round_trip: Boolean with controls if the round trip loader is used
                or if the regular MPFLoader will be used.  Default is False.

        Returns:
            A dictionary of the settings from this YAML file.
        """
        if YamlInterface.cache and filename in YamlInterface.file_cache:
            return copy.deepcopy(YamlInterface.file_cache[filename])

        if verify_version and not YamlInterface.check_config_file_version(filename):
            raise ValueError("Config file version mismatch: {}".format(filename))

        config = dict()

        try:
            self.log.debug("Loading file: %s", filename)

            with open(filename, 'r', encoding='utf8') as f:
                config = YamlInterface.process(f, round_trip)
        except yaml.YAMLError as exc:
            if hasattr(exc, 'problem_mark'):
                mark = exc.problem_mark
                self.log.debug("YAML error found in file %s. Line %s, "
                               "Position %s", filename, mark.line + 1,
                               mark.column + 1)
                if halt_on_error:
                    raise ValueError("YAML error found in file {}. Line {}, "
                                     "Position {}".format(filename, mark.line + 1, mark.column + 1))

            elif halt_on_error:
                raise ValueError("Error found in file %s" % filename)

        except Exception:   # pylint: disable-msg=broad-except
            self.log.debug("Couldn't load from file: %s", filename)

            if halt_on_error:
                raise ValueError("Error found in file %s" % filename)

        if YamlInterface.cache and config:
            YamlInterface.file_cache[filename] = copy.deepcopy(config)

        return config

    @staticmethod
    def process(data_string, round_trip=False):
        """Parse yaml from a string."""
        if round_trip:
            return yaml.load(data_string, Loader=MpfRoundTripLoader)
        else:
            return Util.keys_to_lower(yaml.load(data_string, Loader=MpfLoader))

    def save(self, filename, data, **kwargs):
        """Save config to yaml file."""
        try:
            include_comments = kwargs.pop('include_comments')
        except KeyError:
            include_comments = False

        with open(filename, 'w', encoding='utf8') as output_file:

            if include_comments:
                output_file.write(yaml.dump(data, Dumper=RoundTripDumper,
                                            **kwargs))
            else:
                output_file.write(yaml.dump(data, default_flow_style=False,
                                            **kwargs))

    @staticmethod
    def save_to_str(data):
        """Return yaml string from config."""
        return yaml.dump(data, Dumper=RoundTripDumper,
                         default_flow_style=False, indent=4, width=10)

    @staticmethod
    def rename_key(old_key, new_key, commented_map, logger=None):
        """Used to rename a key in YAML file data that was loaded with the RoundTripLoader (e.g. that contains comments.

        Comments are retained for the renamed key. Order of keys is also maintained.

        Args:
            old_key: The existing key name you want to change.
            new_key: The new key name.
            commented_map: The YAML data CommentMap class (from yaml.load) with
                the key you want to change.
            logger: Optional logger instance which will be used to log this at
                the debug level.

        Returns:
            The updated CommentedMap YAML dict. (Note that this method does not
            change the dict object (e.g. it's changed in place), you you most
            likely don't need to do anything with the returned dict.
        """
        if old_key == new_key or old_key not in commented_map:
            return commented_map

        key_list = list(commented_map.keys())

        for key in key_list:
            if key == old_key:

                if logger:
                    logger.debug('Renaming key: %s: -> %s:', old_key, new_key)

                commented_map[new_key] = commented_map[old_key]

                try:  # if there's no comment, it will not be in ca.items
                    commented_map.ca.items[new_key] = (
                        commented_map.ca.items.pop(old_key))
                except KeyError:
                    pass

                del commented_map[old_key]

            else:
                commented_map.move_to_end(key)

        return commented_map

    # pylint: disable-msg=too-many-arguments
    @staticmethod
    def copy_with_comments(source_dict, source_key, dest_dict, dest_key, delete_source=False, logger=None):
        """Copy dict with comments in config."""
        dest_dict[dest_key] = source_dict[source_key]

        try:
            dest_dict.ca.items[dest_key] = source_dict.ca.items[source_key]

            if logger and not delete_source:
                logger.debug('Copying key: %s -> %s', source_key, dest_key)

        except (KeyError, AttributeError):
            pass

        if delete_source:

            if logger:
                logger.debug('Moving key: %s -> %s', source_key, dest_key)

            del source_dict[source_key]
            source_dict.ca.items.pop(source_key, None)

    @staticmethod
    def del_key_with_comments(dic, key, logger=None):
        """Delete section with comments."""
        if key not in dic:
            return

        if logger:
            logger.debug("Removing key: %s", key)

        del dic[key]
        dic.ca.items.pop(key, None)

    @staticmethod
    def pretty_format(dic):
        """Return pretty printed config."""
        return '\r' + yaml.dump(dic, Dumper=RoundTripDumper, indent=4)

file_interface_class = YamlInterface
