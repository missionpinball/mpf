"""Contains the ConfigProcessor."""

import errno
import hashlib
import logging
import os
import pickle   # nosec
import tempfile

from typing import List, Tuple, Any, Optional, Dict
from difflib import SequenceMatcher

from mpf.core.config_spec_loader import ConfigSpecLoader
import mpf
from mpf.core.file_manager import FileManager
from mpf.core.utility_functions import Util
from mpf._version import __show_version__, __config_version__
from mpf.exceptions.config_file_error import ConfigFileError


class ConfigProcessor:

    """Config processor which loads the config."""

    __slots__ = ["log", "_load_cache", "_store_cache"]

    def __init__(self, load_cache, store_cache):
        """initialize config processor."""
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

    def _load_config_from_cache(self, cache_file) -> Tuple[Any, Optional[Dict[str, Tuple[float, int]]]]:     # nosec
        """Return config from cache."""
        self.log.info("Loading config from cache: %s", cache_file)
        with open(cache_file, 'rb') as f:
            try:
                data = pickle.load(f)   # type: Tuple[Any, Dict[str, Tuple[int, int]]]
            # unfortunately pickle can raise all kinds of exceptions and we dont want to crash on corrupted cache
            # pylint: disable-msg=broad-except
            except Exception:   # pragma: no cover
                self.log.warning("Could not load cache file: %s", cache_file)
                return None, None

        if not isinstance(data, tuple) or len(data) != 2 or not isinstance(data[1], dict):
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

    # pylint: disable-msg=too-many-arguments,too-many-locals
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
            loaded_files = {}

        # Step 3: Check timestamps of included files vs cache
        if loaded_files:
            for configfile, cache_hash in loaded_files.items():
                if not os.path.isfile(configfile) or os.path.getmtime(configfile) != cache_hash[0] or \
                        os.path.getsize(configfile) != cache_hash[1]:
                    load_from_cache = False
                    self.log.warning('Config file in cache changed: %s', configfile)
                    break

        # Step 4: Return cache
        if load_from_cache:
            return config

        config = dict()
        loaded_files = {}
        for configfile in filenames:
            self.log.info('Loading config from file %s.', configfile)
            file_config, file_subfiles = self._load_config_file_and_return_loaded_files(configfile, config_type,
                                                                                        ignore_unknown_sections,
                                                                                        config_spec=config_spec)
            loaded_files.update(file_subfiles)
            config = Util.dict_merge(config, file_config)

        # Step 5: Store to cache
        if self._store_cache:
            config_spec_file = self._get_config_spec_file()
            loaded_files[config_spec_file] = (os.path.getmtime(config_spec_file), os.path.getsize(config_spec_file))
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
            ignore_unknown_sections=False, config_spec=None) -> \
            Tuple[dict, Dict[str, Tuple[float, int]]]:   # pragma: no cover
        """Load a config file and return loaded files."""
        # config_type is str 'machine' or 'mode', which specifies whether this
        # file being loaded is a machine config or a mode config file
        expected_version_str = ConfigProcessor.get_expected_version(config_type)

        config = FileManager.load(filename, expected_version_str, True)
        subfiles = {}

        if not config:
            return {}, {}

        self.log.info('Loading config: %s', filename)

        if config_type in ("machine", "mode"):
            self._check_sections(config_spec, config, config_type, filename, ignore_unknown_sections)

        try:
            if 'config' in config:
                path = os.path.split(filename)[0]

                for file in Util.string_to_event_list(config['config']):
                    full_file = os.path.join(path, file)
                    subfiles[str(full_file)] = (os.path.getmtime(full_file), os.path.getsize(full_file))
                    subconfig, subsubfiles = self._load_config_file_and_return_loaded_files(full_file, config_type,
                                                                                            config_spec=config_spec)
                    subfiles.update(subsubfiles)
                    config = Util.dict_merge(config, subconfig)
            return config, subfiles
        except TypeError:
            return {}, {}

    @staticmethod
    def _get_config_spec_file():
        """Return path of config_spec.yaml."""
        return os.path.abspath(os.path.join(mpf.core.__path__[0], os.pardir, "config_spec.yaml"))

    def load_config_spec(self):
        """Load config spec."""
        cache_file = os.path.join(self.get_cache_dir(), "config_spec.mpf_cache")
        config_spec_file = self._get_config_spec_file()
        stats_config_spec_file = os.stat(config_spec_file)
        if self._load_cache and os.path.isfile(cache_file) and \
                os.path.getmtime(cache_file) == stats_config_spec_file.st_mtime:
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)   # nosec
            except Exception:   # noqa
                pass

        config = FileManager.load(config_spec_file, False, True)
        config = ConfigSpecLoader.process_config_spec(config, "root")

        config = ConfigSpecLoader.load_external_platform_config_specs(config)

        if self._store_cache:
            with open(cache_file, 'wb') as f:
                pickle.dump(config, f, protocol=4)
                os.utime(cache_file, ns=(stats_config_spec_file.st_atime_ns, stats_config_spec_file.st_mtime_ns))
                self.log.info('Config spec file cache created: %s', cache_file)

        return config

    @staticmethod
    def get_expected_version(config_type: str) -> str:
        """Return the expected config or show version tag, e.g. #config_version=6."""
        if config_type in ("machine", "mode"):
            return "#config_version={}".format(__config_version__)
        if config_type == "show":
            return "#show_version={}".format(__show_version__)

        raise AssertionError("Invalid config_type {}".format(config_type))
