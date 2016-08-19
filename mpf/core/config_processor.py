"""Contains the Config and CaseInsensitiveDict base classes."""

import os

from mpf.core.file_manager import FileManager
from mpf.core.utility_functions import Util
from mpf.core.config_validator import ConfigValidator


class ConfigProcessor(object):

    """Config processor which loads the config."""

    def __init__(self, machine):
        """Initialise config processor."""
        pass

    @staticmethod
    def load_config_file(filename, config_type, verify_version=True, halt_on_error=True):   # pragma: no cover
        """Load a config file."""
        # config_type is str 'machine' or 'mode', which specifies whether this
        # file being loaded is a machine config or a mode config file
        config = FileManager.load(filename, verify_version, halt_on_error)

        if not ConfigValidator.config_spec:
            ConfigValidator.load_config_spec()

        for k in config.keys():
            try:
                if config_type not in ConfigValidator.config_spec[k][
                        '__valid_in__']:
                    raise ValueError('Found a "{}:" section in config file {}, '
                                     'but that section is not valid in {} config '
                                     'files.'.format(k, filename, config_type))
            except KeyError:
                raise ValueError('Found a "{}:" section in config file {}, '
                                 'but that section is not valid in {} config '
                                 'files.'.format(k, filename, config_type))

        try:
            if 'config' in config:
                path = os.path.split(filename)[0]

                for file in Util.string_to_list(config['config']):
                    full_file = os.path.join(path, file)
                    config = Util.dict_merge(config,
                                             ConfigProcessor.load_config_file(
                                                 full_file, config_type))
            return config
        except TypeError:
            return dict()
