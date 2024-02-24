"""Contains the YamlInterface class for reading & writing YAML files."""
import copy
from typing import Any, Iterable, List, Dict

from ruamel import yaml
from ruamel.yaml.error import MarkedYAMLError

from mpf.core.file_interface import FileInterface

_yaml = yaml.YAML(typ='safe')
_yaml.default_flow_style = False

class YamlInterface(FileInterface):

    """File interface for yaml files."""

    file_types = ['.yaml', '.yml']
    cache = False
    file_cache = dict()     # type: Dict[str, Any]

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
                config = self.to_plain_dict(config)
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
    def to_plain_dict(data):
        """Recursively convert CommentedMap and CommentedSeq to Python dict and list respectively."""
        if isinstance(data, dict):
            return {key: YamlInterface.to_plain_dict(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [YamlInterface.to_plain_dict(item) for item in data]
        else:
            return data

    @staticmethod
    def process(data_string: Iterable[str]) -> dict:
        """Parse yaml from a string."""
        return _yaml.load(data_string)

    def save(self, filename: str, data: dict) -> None:   # pragma: no cover
        """Save config to yaml file."""
        with open(filename, 'w', encoding='utf8') as output_file:
            _yaml.default_flow_style = False
            _yaml.line_break = ''
            _yaml.dump(data, output_file)
