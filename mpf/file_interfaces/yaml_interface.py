"""Contains the YamlInterface class for reading & writing YAML files.

Fixes for octal and boolean values are from here:
http://stackoverflow.com/questions/32965846/cant-parse-yaml-correctly/
"""
import copy
import re
from typing import Any, Iterable, List
from typing import Dict

from collections.abc import Hashable

from ruamel import yaml
from ruamel.yaml import MappingNode
from ruamel.yaml.error import MarkedYAMLError
from ruamel.yaml.reader import Reader
from ruamel.yaml.resolver import BaseResolver
from ruamel.yaml.scanner import Scanner
from ruamel.yaml.parser import Parser
from ruamel.yaml.composer import Composer
from ruamel.yaml.constructor import Constructor, ConstructorError

from mpf.core.file_interface import FileInterface

_yaml = yaml.YAML()

# RESOLVERS = [
#     (
#         # Process any item beginning with a plus sign (+) as a string
#         u'tag:yaml.org,2002:str',
#         re.compile(
#             u'''^(\+([0-9a-zA-Z .]+))$''',
#             re.X),
#         list(u'+')),

#     (
#         # Process any 3+ digit number with a leading zero as a string
#         u'tag:yaml.org,2002:str',
#         re.compile(
#             u'''^(?:(0[0-9]{2,}))$''',
#             re.X),
#         list(u'0')),

#     (
#         u'tag:yaml.org,2002:bool',
#         re.compile(
#             u'''^(?:true|True|TRUE|false|False|FALSE|yes|Yes|YES|no|No|NO)$''',
#             re.X), list(u'tTfFyYnN')),

#     (
#         u'tag:yaml.org,2002:float',
#         re.compile(u'''^(?:
#      [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*
#     |\\.[0-9_]+)$''', re.X),
#         list(u'-+0123456789.')),
# ]

# for resolver in RESOLVERS:
#     _yaml.resolver.add_implicit_resolver(*resolver)


class YamlInterface(FileInterface):

    """File interface for yaml files."""

    file_types = ['.yaml', '.yml']
    cache = False
    file_cache = dict()     # type: Dict[str, Any]

    # __slots__ = []  # type: List[str]

    def load(self, filename, expected_version_str=None, halt_on_error=True) -> dict:
        """Load a YAML file from disk.

        Args:
        ----
            filename: The file to load.
            expected_version_str: Version string to expect or None for no check.
            halt_on_error: Boolean which controls what happens if the file
                can't be loaded. (Not found, invalid format, etc. If True, MPF
                will raise an error and exit. If False, an empty config
                dictionary will be returned.

        Returns a dictionary of the settings from this YAML file.
        """
        if self.cache and filename in self.file_cache:
            return copy.deepcopy(self.file_cache[filename])

        config = dict()     # type: dict

        try:
            self.log.debug("Loading file: %s", filename)

            with open(filename, encoding='utf8') as f:
                if expected_version_str:
                    version_str = f.readline().strip()
                    if version_str != expected_version_str:
                        raise AssertionError("Version mismatch. Expected: {} Actual: {} Files: {}".format(
                            expected_version_str, version_str, filename))
                config = self.process(f)
        except MarkedYAMLError as e:
            mark = e.problem_mark
            msg = "YAML error found in file {}. Line {}, " \
                  "Position {}: {}".format(filename, mark.line + 1 if mark else None,
                                           mark.column + 1 if mark else None, e)

            if halt_on_error:
                raise ValueError(msg)

            self.log.warning(msg)
        except Exception as e:   # pylint: disable-msg=broad-except
            msg = "Error found in file {}: {}".format(filename, e)

            if halt_on_error:
                raise ValueError(msg)
            self.log.warning(msg)

        if self.cache and config:
            self.file_cache[filename] = copy.deepcopy(config)

        return config

    @staticmethod
    def process(data_string: Iterable[str]) -> dict:
        """Parse yaml from a string."""
        p = _yaml.load(data_string)  # todo instantiate only once
        return p

    def save(self, filename: str, data: dict) -> None:   # pragma: no cover
        """Save config to yaml file."""
        data_str = _yaml.dump(data, default_flow_style=False)
        if not data_str:
            raise AssertionError("Failed to serialize data.")
        with open(filename, 'w', encoding='utf8') as output_file:
            output_file.write(data_str)
