"""Parse config_spec."""
from typing import TYPE_CHECKING
import importlib.metadata

from mpf.core.utility_functions import Util
from mpf.file_interfaces.yaml_interface import YamlInterface


if TYPE_CHECKING:
    from mpf.core.device import Device  # pylint: disable-msg=cyclic-import,unused-import


class ConfigSpecLoader:

    """Config spec loader."""

    @classmethod
    def process_config_spec(cls, spec, path):
        """Process a config spec dictionary."""
        if not isinstance(spec, dict):
            raise AssertionError("Expected a dict at: {} {}".format(path, spec))

        for element, value in spec.items():
            if element.startswith("__"):
                spec[element] = value
            elif isinstance(value, str):
                if value == "ignore":
                    spec[element] = value
                else:
                    spec[element] = value.split('|')
                    if len(spec[element]) != 3:
                        raise AssertionError("Format incorrect: {}".format(value))
            else:
                spec[element] = cls.process_config_spec(value, path + ":" + element)

        return spec

    @staticmethod
    def load_external_platform_config_specs(config):
        """Load config spec for external platforms."""
        eps = importlib.metadata.entry_points(group='mpf.platforms')
        for platform_entry in eps:
            config_spec = platform_entry.load().get_config_spec()

            if config_spec:
                # add specific config spec if platform has any
                config[config_spec[1]] =\
                    ConfigSpecLoader.process_config_spec(YamlInterface.process(config_spec[0]), config_spec[1])
        return config

    @staticmethod
    def load_device_config_specs(config_spec, machine_config):
        """Load device config specs."""
        for device_type in machine_config['mpf']['device_modules'].values():
            device_cls = Util.string_to_class(device_type)      # type: Device
            if device_cls.get_config_spec():
                # add specific config spec if device has any
                config_spec[device_cls.config_section] = ConfigSpecLoader.process_config_spec(
                    YamlInterface.process(device_cls.get_config_spec()),
                    device_cls.config_section)

        return config_spec
