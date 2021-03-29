"""Yaml interface in roundtrip mode."""
from typing import Any

import ruamel.yaml
import ruamel.yaml.emitter
import ruamel.yaml.serializer
import ruamel.yaml.representer

from ruamel.yaml import StringIO, YAML, VersionedResolver
from ruamel.yaml.reader import Reader
from ruamel.yaml.scanner import RoundTripScanner
from ruamel.yaml.parser import Parser
from ruamel.yaml.composer import Composer
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.dumper import RoundTripDumper

from mpf.file_interfaces.yaml_interface import YamlInterface, MpfResolver, RESOLVERS

# pylint: disable-msg=invalid-name
typ = 'mpf-rt'


class MpfRoundTripResolver(VersionedResolver):

    """Resolver with mentioned fixes."""


class FormattedInt(ruamel.yaml.scalarint.ScalarInt):

    """An integer which preserves the formatting."""

    def __new__(cls, *args, **kw):
        """Preserve raw string representation."""
        # pylint: disable-msg=protected-access
        x = ruamel.yaml.scalarint.ScalarInt.__new__(cls, *args, **kw)
        x.raw = args[0]
        return x


def alt_construct_yaml_int(constructor, node):
    """Parse integers using FormattedInt."""
    value_s = ruamel.yaml.compat.to_str(constructor.construct_scalar(node))
    if value_s.isdigit():
        return constructor.construct_yaml_int(node)
    return FormattedInt(value_s)


ruamel.yaml.constructor.RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:int', alt_construct_yaml_int)


def represent_int(representer, data):
    """Return raw representation for FormattedInt."""
    return representer.represent_scalar(u'tag:yaml.org,2002:int',
                                        str(data.raw))


ruamel.yaml.representer.RoundTripRepresenter.add_representer(FormattedInt, represent_int)


for resolver in RESOLVERS:
    MpfRoundTripResolver.add_implicit_resolver(*resolver)


def init_typ(self):
    """Initialise ruamel RoundTrip."""
    self.Resolver = MpfRoundTripResolver
    self.default_flow_style = False
    # no optimized rt-dumper yet
    self.Emitter = ruamel.yaml.emitter.Emitter  # type: Any
    self.Serializer = ruamel.yaml.serializer.Serializer  # type: Any
    self.Representer = ruamel.yaml.representer.RoundTripRepresenter  # type: Any
    self.Scanner = ruamel.yaml.scanner.RoundTripScanner  # type: Any
    # no optimized rt-parser yet
    self.Parser = ruamel.yaml.parser.RoundTripParser  # type: Any
    self.Composer = ruamel.yaml.composer.Composer  # type: Any
    self.Constructor = ruamel.yaml.constructor.RoundTripConstructor  # type: Any


class MpfRoundTripLoader(Reader, RoundTripScanner, Parser, Composer, RoundTripConstructor, MpfResolver):

    """Config loader which can roundtrip."""

    def __init__(self, stream, version=None, preserve_quotes=None):
        """Initialise loader."""
        del version
        Reader.__init__(self, stream, loader=self)
        RoundTripScanner.__init__(self, loader=self)
        Parser.__init__(self, loader=self)
        Composer.__init__(self, loader=self)
        RoundTripConstructor.__init__(self, preserve_quotes=preserve_quotes, loader=self)
        MpfResolver.__init__(self, loadumper=self)


class YamlRoundtrip(YamlInterface):     # pragma: no cover

    """Round trip yaml interface used for the migrator."""

    @staticmethod
    def process(data_string):
        """Parse yaml from a string."""
        return ruamel.yaml.load(data_string, Loader=MpfRoundTripLoader)

    @staticmethod
    def save_to_str(data):
        """Return yaml string from config."""
        return ruamel.yaml.dump(data, Dumper=RoundTripDumper,
                                default_flow_style=False, indent=4, width=10)

    def save(self, filename, data):
        """Save config to yaml file."""
        with open(filename, 'w', encoding='utf8') as output_file:
            output_file.write(ruamel.yaml.dump(data, Dumper=RoundTripDumper))

    @staticmethod
    def rename_key(old_key, new_key, commented_map, logger=None):
        """Rename a key in YAML file data that was loaded with the RoundTripLoader (e.g. that contains comments).

        Comments are retained for the renamed key. Order of keys is also maintained.

        Args:
        ----
            old_key: The existing key name you want to change.
            new_key: The new key name.
            commented_map: The YAML data CommentMap class (from yaml.load) with
                the key you want to change.
            logger: Optional logger instance which will be used to log this at
                the debug level.

        Returns the updated CommentedMap YAML dict. (Note that this method does not
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
        return '\r' + ruamel.yaml.dump(dic, Dumper=RoundTripDumper, indent=4)

    @classmethod
    def reformat_file(cls, filename, show_file=False) -> bool:
        """Reformat a yaml config file.

        Returns true if the file was changed.
        """
        with open(filename) as f:
            content = f.read()

        formatted_yaml_string = cls.reformat_yaml(content, show_file=show_file)
        if content != formatted_yaml_string:
            with open(filename, "w") as f:
                f.write(formatted_yaml_string)
            return True

        # nothing changed
        return False

    @staticmethod
    def reformat_yaml(yaml_string, show_file=False):
        """Reformat a yaml config string."""
        yaml_obj = YAML(typ="mpf-rt", plug_ins=["mpf.file_interfaces.yaml_roundtrip"])
        if show_file:
            yaml_obj.indent(mapping=2, sequence=2, offset=0)
        else:
            yaml_obj.indent(mapping=2, sequence=4, offset=2)

        yaml_obj.preserve_quotes = True
        yaml_obj.width = 10000
        data = yaml_obj.load(yaml_string)
        string_stream = StringIO()
        yaml_obj.dump(data, string_stream)
        formatted_yaml_string = string_stream.getvalue()
        # if show_file:
        #    formatted_yaml_string = re.sub(r'^  ', '', formatted_yaml_string, flags=re.MULTILINE)

        return formatted_yaml_string
