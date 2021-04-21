"""Contains the ConfigProcessor."""

import errno
import hashlib
import logging
import os
import pickle   # nosec
import tempfile

from typing import List, Tuple, Any, Optional
from difflib import SequenceMatcher
from pkg_resources import iter_entry_points

from mpf.file_interfaces.yaml_interface import YamlInterface
import mpf
from mpf.core.file_manager import FileManager
from mpf.core.utility_functions import Util
from mpf._version import __show_version__, __config_version__
from mpf.exceptions.config_file_error import ConfigFileError


class ConfigProcessor:

    """Config processor which loads the config."""

    __slots__ = ["log", "_load_cache", "_store_cache"]

    def __init__(self, load_cache, store_cache):
        """Initialise config processor."""
        self.log = logging.getLogger("ConfigProcessor")
        self._load_cache = load_cache
        self._store_cache = store_cache

    @staticmethod
    def get_cache_dir():
        """Return cache dir."""
        return tempfile.gettempdir()

    def get_cache_filename(self, filenames: List[str]) -> str:   # pragma: no cover
        """Return cache file name."""
        cache_dir = self.get_cache_dir()
        filestring = ""
        for configfile in filenames:
            filestring += str(os.path.abspath(configfile))
        path_hash = hashlib.md5(bytes(filestring, 'UTF-8')).hexdigest()     # nosec
        return os.path.join(cache_dir, path_hash + ".mpf_cache")

    def _load_config_from_cache(self, cache_file) -> Tuple[Any, Optional[List[str]]]:     # nosec
        """Return config from cache."""
        self.log.info("Loading config from cache: %s", cache_file)
        with open(cache_file, 'rb') as f:
            try:
                data = pickle.load(f)   # type: Tuple[Any, List[str]]
            # unfortunately pickle can raise all kinds of exceptions and we dont want to crash on corrupted cache
            # pylint: disable-msg=broad-except
            except Exception:   # pragma: no cover
                self.log.warning("Could not load cache file: %s", cache_file)
                return None, None

        if not isinstance(data, tuple) or len(data) != 2:
            return None, None
        return data

    def _get_mtime_or_negative(self, filename) -> float:
        """Return mtime or -1 if file could not be found."""
        try:
            return os.path.getmtime(filename)
        except OSError as exception:
            if exception.errno != errno.ENOENT:
                raise  # some unknown error?

            self.log.debug('Cache file not found: %s', filename)
            return -1

    # pylint: disable-msg=too-many-arguments
    def load_config_files_with_cache(self, filenames: List[str], config_type: str,
                                     ignore_unknown_sections=False, config_spec=None) -> dict:   # pragma: no cover
        """Load multiple configs with a combined cache."""
        config = dict()     # type: Any
        # Step 1: Check timestamps of the filelist vs cache
        cache_file = self.get_cache_filename(filenames)
        load_from_cache = self._load_cache
        if load_from_cache:
            cache_time = self._get_mtime_or_negative(cache_file)
            if cache_time < 0:
                load_from_cache = False
            else:
                for configfile in filenames:
                    if not os.path.isfile(configfile) or os.path.getmtime(configfile) > cache_time:
                        load_from_cache = False
                        self.log.warning('Config file in cache changed: %s', configfile)
                        break

        # Step 2: Get cache content
        if load_from_cache:
            config, loaded_files = self._load_config_from_cache(cache_file)
            if not config:
                load_from_cache = False
        else:
            loaded_files = []

        # Step 3: Check timestamps of included files vs cache
        if loaded_files:
            for configfile in loaded_files:
                if not os.path.isfile(configfile) or os.path.getmtime(configfile) > cache_time:
                    load_from_cache = False
                    self.log.warning('Config file in cache changed: %s', configfile)
                    break

        # Step 4: Return cache
        if load_from_cache:
            return config

        config = dict()
        loaded_files = []
        for configfile in filenames:
            self.log.info('Loading config from file %s.', configfile)
            file_config, file_subfiles = self._load_config_file_and_return_loaded_files(configfile, config_type,
                                                                                        ignore_unknown_sections,
                                                                                        config_spec=config_spec)
            loaded_files.extend(file_subfiles)
            config = Util.dict_merge(config, file_config)

        # Step 5: Store to cache
        if self._store_cache:
            with open(cache_file, 'wb') as f:
                pickle.dump((config, loaded_files), f, protocol=4)
                self.log.info('Config file cache created: %s', cache_file)

        return config

    @staticmethod
    def _find_similar_key(key, config_spec, config_type):
        """Find the most similar key in config_spec."""
        best_similarity = 0
        best_key = ""
        for existing_key, config in config_spec.items():
            if '__valid_in__' not in config or config_type not in config['__valid_in__']:
                continue
            similarity = SequenceMatcher(None, existing_key, key).ratio()
            if similarity > best_similarity:
                best_key = existing_key
                best_similarity = similarity

        return best_key

    def _check_sections(self, config_spec, config, config_type, filename, ignore_unknown_sections):
        if not isinstance(config, dict):
            raise ConfigFileError("Config should be a dict: {}".format(config), 1, self.log.name, filename)
        for k in config.keys():
            if k in config_spec:
                if config_type not in config_spec[k]['__valid_in__']:
                    raise ConfigFileError('Found a "{}:" section in config file {}, '
                                          'but that section is not valid in {} config '
                                          'files (only in {}).'.format(k, filename, config_type,
                                                                       config_spec[k]['__valid_in__']),
                                          2, self.log.name, filename)
            elif not ignore_unknown_sections:
                suggestion = self._find_similar_key(k, config_spec, config_type)

                raise ConfigFileError('Found a "{}:" section in config file {}, '
                                      'but that section name is unknown. Did you mean "{}:" '
                                      'instead?.'.format(k, filename, suggestion), 3, self.log.name,
                                      filename)

    def _load_config_file_and_return_loaded_files(
            self, filename, config_type: str,
            ignore_unknown_sections=False, config_spec=None) -> Tuple[dict, List[str]]:   # pragma: no cover
        """Load a config file and return loaded files."""
        # config_type is str 'machine' or 'mode', which specifies whether this
        # file being loaded is a machine config or a mode config file
        expected_version_str = ConfigProcessor.get_expected_version(config_type)

        config = FileManager.load(filename, expected_version_str, True)
        subfiles = []

        if not config:
            return dict(), []

        self.log.info('Loading config: %s', filename)

        if config_type in ("machine", "mode"):
            self._check_sections(config_spec, config, config_type, filename, ignore_unknown_sections)

        try:
            if 'config' in config:
                path = os.path.split(filename)[0]

                for file in Util.string_to_event_list(config['config']):
                    full_file = os.path.join(path, file)
                    subfiles.append(full_file)
                    subconfig, subsubfiles = self._load_config_file_and_return_loaded_files(full_file, config_type,
                                                                                            config_spec=config_spec)
                    subfiles.extend(subsubfiles)
                    config = Util.dict_merge(config, subconfig)
            return config, subfiles
        except TypeError:
            return dict(), []

    def load_config_spec(self):
        """Load config spec."""
        cache_file = os.path.join(self.get_cache_dir(), "config_spec.mpf_cache")
        config_spec_file = os.path.abspath(os.path.join(mpf.core.__path__[0], os.pardir, "config_spec.yaml"))
        stats_config_spec_file = os.stat(config_spec_file)
        if self._load_cache and os.path.isfile(cache_file) and \
                os.path.getmtime(cache_file) == stats_config_spec_file.st_mtime:
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)   # nosec
            except Exception:   # noqa
                pass

        config = FileManager.load(config_spec_file, False, True)
        config = self._process_config_spec(config, "root")

        config = self.load_external_platform_config_specs(config)

        if self._store_cache:
            with open(cache_file, 'wb') as f:
                pickle.dump(config, f, protocol=4)
                os.utime(cache_file, ns=(stats_config_spec_file.st_atime_ns, stats_config_spec_file.st_mtime_ns))
                self.log.info('Config spec file cache created: %s', cache_file)

        return config

    def load_external_platform_config_specs(self, config):
        """Load config spec for external platforms."""
        for platform_entry in iter_entry_points(group='mpf.platforms'):
            config_spec = platform_entry.load().get_config_spec()

            if config_spec:
                # add specific config spec if platform has any
                config[config_spec[1]] = self._process_config_spec(YamlInterface.process(config_spec[0]),
                                                                   config_spec[1])
        return config

    def load_device_config_specs(self, config_spec, machine_config):
        """Load device config specs."""
        for device_type in machine_config['mpf']['device_modules'].values():
            device_cls = Util.string_to_class(device_type)
            if device_cls.get_config_spec():
                # add specific config spec if device has any
                config_spec[device_cls.config_section] = self._process_config_spec(
                    YamlInterface.process(device_cls.get_config_spec()),
                    device_cls.config_section)

        return config_spec

    def _process_config_spec(self, spec, path):
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
                spec[element] = self._process_config_spec(value, path + ":" + element)

        return spec

    @staticmethod
    def get_expected_version(config_type: str) -> str:
        """Return the expected config or show version tag, e.g. #config_version=5."""
        if config_type in ("machine", "mode"):
            return "#config_version={}".format(__config_version__)
        if config_type == "show":
            return "#show_version={}".format(__show_version__)

        raise AssertionError("Invalid config_type {}".format(config_type))
