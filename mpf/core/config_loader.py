"""Loads MPF configs."""
from typing import List, NoReturn

import logging
import os
import pickle
import sys

from pathlib import PurePath

from mpf.core.config_processor import ConfigProcessor
from mpf.core.config_spec_loader import ConfigSpecLoader


def _raise_mode_not_found_exception(mode_name) -> NoReturn:
    raise AssertionError("No config found for mode '{mode_name}'. MPF expects the config at "
                         "'modes/{mode_name}/config/{mode_name}.yaml' inside your machine "
                         "folder.".format(mode_name=mode_name))


class MpfConfig:

    """Contains a MPF config."""

    __slots__ = ["_config_spec", "_machine_config", "_mode_config", "_show_config", "_machine_path", "_mpf_path"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, config_spec, machine_config, modes, shows, machine_path, mpf_path):
        """Initialize config."""
        self._config_spec = config_spec
        self._machine_config = machine_config
        self._mode_config = modes
        self._show_config = shows
        self._machine_path = machine_path
        self._mpf_path = mpf_path

    def get_mpf_path(self):
        """Return mpf path."""
        return self._mpf_path

    def get_machine_path(self):
        """Return machine path."""
        return self._machine_path

    def set_machine_path(self, value):
        """Set a new machine path."""
        self._machine_path = value

    def get_config_spec(self):
        """Return config spec."""
        return self._config_spec

    def get_machine_config(self):
        """Return machine wide config."""
        return self._machine_config

    def get_mode_config(self, mode_name):
        """Return config for a mode."""
        try:
            return self._mode_config[mode_name]
        except KeyError:
            _raise_mode_not_found_exception(mode_name)

    def get_modes(self):
        """Return a list of mode names."""
        return self._mode_config.keys()

    def get_show_config(self, show_name):
        """Return a show."""
        try:
            return self._show_config[show_name]
        except KeyError:
            raise AssertionError("No config found for show '{}'.".format(show_name))

    def get_shows(self):
        """Return a list of all shows names."""
        return self._show_config.keys()


class MpfMcConfig:

    """Contains a MPF-MC config."""

    __slots__ = ["_config_spec", "_machine_config", "_mode_config", "_machine_path"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, config_spec, machine_config, modes, machine_path):
        """Initialize config."""
        self._config_spec = config_spec
        self._machine_config = machine_config
        self._mode_config = modes
        self._machine_path = machine_path

    def get_machine_path(self):
        """Return machine path."""
        return self._machine_path

    def set_machine_path(self, value):
        """Set a new machine path."""
        self._machine_path = value

    def get_config_spec(self):
        """Return config spec."""
        return self._config_spec

    def get_machine_config(self):
        """Return machine wide config."""
        return self._machine_config

    def get_mode_config(self, mode_name):
        """Return config for a mode."""
        try:
            return self._mode_config[mode_name]
        except KeyError:
            _raise_mode_not_found_exception(mode_name)

    def get_modes(self):
        """Return a list of mode names."""
        return self._mode_config.keys()


class ConfigLoader:

    """Generic loader for MPF and MC configs."""

    __slots__ = []  # type: List[str]

    def load_mpf_config(self) -> MpfConfig:
        """Load and return a MPF config."""

    def load_mc_config(self) -> MpfMcConfig:
        """Load and return a MC config."""


class YamlMultifileConfigLoader(ConfigLoader):

    """Loads MPF configs from machine folder with config and modes."""

    __slots__ = ["configfile", "machine_path", "config_processor", "log", "mpf_path", "mc_path"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, machine_path, configfile, load_cache, store_cache):
        """Initialize yaml multifile config loader."""
        self.configfile = configfile
        self.machine_path = machine_path
        self.config_processor = ConfigProcessor(load_cache, store_cache)
        self.log = logging.getLogger("YamlMultifileConfigLoader")
        try:
            # pylint: disable-msg=import-outside-toplevel
            import mpf.core
            self.mpf_path = os.path.abspath(os.path.join(mpf.core.__path__[0], os.pardir))
        except ImportError:
            self.mpf_path = None
        try:
            # pylint: disable-msg=import-outside-toplevel
            import mpfmc.core
            self.mc_path = os.path.abspath(os.path.join(mpfmc.core.__path__[0], os.pardir))
        except ImportError:
            self.mc_path = None

    def load_mpf_config(self) -> MpfConfig:
        """Load and return a MPF config."""
        config_spec = self._load_config_spec()
        machine_config = self._load_mpf_machine_config(config_spec)
        config_spec = self._load_additional_config_spec(config_spec, machine_config)
        mode_config = self._load_modes(config_spec, machine_config)
        show_config = self._load_shows(config_spec, machine_config, mode_config)
        return MpfConfig(config_spec, machine_config, mode_config, show_config, self.machine_path, self.mpf_path)

    def load_mc_config(self) -> MpfMcConfig:
        """Load and return a MC config."""
        config_spec = self._load_config_spec()
        machine_config = self._load_mc_machine_config(config_spec)
        mode_config = self._load_modes(config_spec, machine_config, ignore_unknown_sections=True)
        return MpfMcConfig(config_spec, machine_config, mode_config, self.machine_path)

    def _load_config_spec(self):
        return self.config_processor.load_config_spec()

    def _load_mpf_machine_config(self, config_spec):
        config_files = [os.path.join(self.mpf_path, "mpfconfig.yaml")]

        for num, config_file in enumerate(self.configfile):
            config_files.append(os.path.join(self.machine_path, "config", config_file))

            self.log.info("Machine config file #%s: %s", num + 1, config_file)

        return self.config_processor.load_config_files_with_cache(config_files, "machine", config_spec=config_spec)

    def _load_mc_machine_config(self, config_spec):
        if not self.mc_path:
            raise AssertionError("Could not import MPF-MC.")
        config_files = [os.path.join(self.mc_path, "mcconfig.yaml")]

        for num, config_file in enumerate(self.configfile):
            config_files.append(os.path.join(self.machine_path, "config", config_file))

            self.log.info("Machine config file #%s: %s", num + 1, config_file)

        return self.config_processor.load_config_files_with_cache(config_files, "machine", config_spec=config_spec)

    def _load_additional_config_spec(self, config_spec, machine_config):
        """Load additional config specs from devices."""
        sys.path.insert(0, self.machine_path)
        config_spec = ConfigSpecLoader.load_device_config_specs(config_spec, machine_config)
        sys.path.remove(self.machine_path)
        return config_spec

    def _load_modes(self, config_spec, machine_config, ignore_unknown_sections=False):
        mode_config = {}
        for mode in machine_config.get("modes", {}):
            mpf_config_path = os.path.join(self.mpf_path, "modes", mode, 'config', mode + '.yaml')
            machine_config_path = os.path.join(self.machine_path, "modes", mode, 'config', mode + '.yaml')
            mode_config_files = []
            if os.path.isfile(mpf_config_path):
                self.log.debug("Loading mode %s from %s", mode, mpf_config_path)
                mode_config_files.append(mpf_config_path)
            if os.path.isfile(machine_config_path):
                self.log.debug("Loading mode %s from %s", mode, mpf_config_path)
                mode_config_files.append(machine_config_path)

            if not mode_config_files:
                _raise_mode_not_found_exception(mode)

            config = self.config_processor.load_config_files_with_cache(mode_config_files, "mode",
                                                                        config_spec=config_spec,
                                                                        ignore_unknown_sections=ignore_unknown_sections)

            if "mode" not in config:
                config["mode"] = dict()

            mode_path, asset_paths = self._find_mode_path(mode)
            config["mode"]["path"] = mode_path
            config["mode"]["asset_paths"] = asset_paths

            mode_config[mode] = config
        return mode_config

    def _find_mode_path(self, mode_string):
        asset_paths = []
        mode_path = None

        mpf_mode_path = os.path.join(self.mpf_path, "modes", mode_string)
        if os.path.exists(mpf_mode_path):
            asset_paths.append(mpf_mode_path)
            mode_path = mpf_mode_path

        machine_mode_path = os.path.join(self.machine_path, "modes", mode_string)
        if os.path.exists(machine_mode_path):
            asset_paths.append(machine_mode_path)
            mode_path = machine_mode_path

        if not mode_path:
            raise ValueError("No folder found for mode '{}'. Is your mode "
                             "folder in your machine's 'modes' folder? Tried {} and {}."
                             .format(mode_string, mpf_mode_path, machine_mode_path))

        return mode_path, asset_paths

    def _load_shows_in_folder(self, folder, show_configs, config_spec):
        if not os.path.isdir(folder):
            return show_configs
        # ignore temporary files
        ignore_prefixes = (".", "~")
        # do not get fooled by windows or mac garbage
        ignore_files = ("desktop.ini", "Thumbs.db")

        for this_path, _, files in os.walk(folder, followlinks=True):
            relative_path = PurePath(this_path).relative_to(folder)
            for show_file_name in [f for f in files if f.endswith(".yaml") and not f.startswith(ignore_prefixes) and
                                   f != ignore_files]:
                show_name = show_file_name[:-5]
                if show_name in show_configs:
                    raise AssertionError("Duplicate show {}".format(show_name))
                show_config = self.config_processor.load_config_files_with_cache(
                    [os.path.join(folder, str(relative_path), show_file_name)], "show", config_spec=config_spec)
                show_configs[show_name] = show_config
        return show_configs

    def _load_shows(self, config_spec, machine_config, mode_config):
        show_configs = {}
        shows = machine_config.get("shows", {})
        if not isinstance(shows, dict):
            raise AssertionError("Show section needs to be a dictionary but it {}.".format(shows.__class__))

        for show_name, show_config in shows.items():
            show_configs[show_name] = show_config

        show_configs = self._load_shows_in_folder(os.path.join(self.machine_path, "shows"), show_configs, config_spec)

        for mode_name, config in mode_config.items():
            for show_name, show_config in config.get("shows", {}).items():
                if show_name in show_configs:
                    raise AssertionError("Duplicate show {}".format(show_name))
                show_configs[show_name] = show_config

            show_configs = self._load_shows_in_folder(os.path.join(self.mpf_path, "modes", mode_name, 'shows'),
                                                      show_configs, config_spec)
            show_configs = self._load_shows_in_folder(os.path.join(self.machine_path, "modes", mode_name, 'shows'),
                                                      show_configs, config_spec)

        return show_configs


class ProductionConfigLoader(ConfigLoader):

    """Loads a single pickled production config each for MPF and MPF-MC."""

    __slots__ = ["machine_path"]

    def __init__(self, machine_path):
        """Initialize production config loader."""
        self.machine_path = machine_path

    @staticmethod
    def get_mpf_bundle_path(machine_path):
        """Return the path for the MPF bundle."""
        return os.path.join(machine_path, "mpf_config.bundle")

    @staticmethod
    def get_mpf_mc_bundle_path(machine_path):
        """Return the path for the MPF bundle."""
        return os.path.join(machine_path, "mpf_mc_config.bundle")

    def load_mpf_config(self) -> MpfConfig:
        """Load and return a MPF config."""
        with open(self.get_mpf_bundle_path(self.machine_path), "rb") as f:
            return pickle.load(f)

    def load_mc_config(self) -> MpfMcConfig:
        """Load and return a MC config."""
        with open(self.get_mpf_mc_bundle_path(self.machine_path), "rb") as f:
            return pickle.load(f)
