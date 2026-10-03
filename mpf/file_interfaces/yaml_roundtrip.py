"""YAML interface in round-trip mode."""

import threading

from ruamel import yaml

from mpf.file_interfaces.yaml_interface import YamlInterface

_thread_local = threading.local()


def _get_yaml():
    """Get or create a thread-isolated round-trip YAML instance."""
    if not hasattr(_thread_local, 'yaml'):
        _yaml_instance = yaml.YAML(typ='rt')
        _yaml_instance.default_flow_style = False
        _yaml_instance.preserve_quotes = True
        _yaml_instance.width = 10000
        _thread_local.yaml = _yaml_instance

    return _thread_local.yaml


class YamlRoundtrip(YamlInterface):
    """YAML interface which preserves round-trip information."""

    cache = False

    @staticmethod
    def process(data_string):
        """Parse YAML while preserving comments and line/column information."""
        return _get_yaml().load(data_string)
