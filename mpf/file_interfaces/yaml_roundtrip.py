"""Yaml interface in roundtrip mode."""
import ruamel.yaml as yaml  # pylint: disable-msg=useless-import-alias
from ruamel.yaml.reader import Reader
from ruamel.yaml.scanner import RoundTripScanner
from ruamel.yaml.parser import Parser
from ruamel.yaml.composer import Composer
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.dumper import RoundTripDumper
from mpf.file_interfaces.yaml_interface import YamlInterface, MpfResolver


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
        return yaml.load(data_string, Loader=MpfRoundTripLoader)

    @staticmethod
    def save_to_str(data):
        """Return yaml string from config."""
        return yaml.dump(data, Dumper=RoundTripDumper,
                         default_flow_style=False, indent=4, width=10)

    def save(self, filename, data):
        """Save config to yaml file."""
        with open(filename, 'w', encoding='utf8') as output_file:
            output_file.write(yaml.dump(data, Dumper=RoundTripDumper))

    @staticmethod
    def rename_key(old_key, new_key, commented_map, logger=None):
        """Rename a key in YAML file data that was loaded with the RoundTripLoader (e.g. that contains comments).

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
