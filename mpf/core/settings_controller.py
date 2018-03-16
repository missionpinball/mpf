"""Manages operator controllable settings."""
from collections import namedtuple

from typing import Dict, List

from mpf.core.utility_functions import Util

from mpf.core.mpf_controller import MpfController

SettingEntry = namedtuple("SettingEntry", ["name", "label", "sort", "machine_var", "default", "values"])


class SettingsController(MpfController):

    """Manages operator controllable settings."""

    # needed here so the auto-detection of child classes works
    module_name = 'SettingsController'
    config_name = 'settings_controller'

    def __init__(self, machine):
        """Initialise settings controller."""
        super().__init__(machine)

        # start with default settings
        self._settings = {}     # type: Dict[str, SettingEntry]
        """Dictionary of available settings."""

        self._add_entries_from_config()

    def _add_entries_from_config(self):
        # add entries from config
        self.config = self.machine.config.get('settings', {})
        for name, settings in self.config.items():
            settings = self.machine.config_validator.validate_config("settings", settings)
            if not settings['machine_var']:
                settings['machine_var'] = name
            values = {}
            # convert types
            for key, value in settings['values'].items():
                values[Util.convert_to_type(key, settings['key_type'])] = value

            # convert default key
            settings['default'] = Util.convert_to_type(settings['default'], settings['key_type'])

            self.add_setting(SettingEntry(name, settings['label'], settings['sort'], settings['machine_var'],
                                          settings['default'], values))

    def add_setting(self, setting: SettingEntry):
        """Add a setting."""
        self._settings[setting.name] = setting

    def get_settings(self) -> List[SettingEntry]:
        """Return all available settings."""
        sorted_list = list(self._settings.values())
        sorted_list.sort(key=lambda x: x.sort)
        return sorted_list

    def get_setting_value_label(self, setting_name):
        """Return label for value."""
        value = self.get_setting_value(setting_name)
        return self._settings[setting_name].values.get(value, "invalid")

    def __getattr__(self, item):
        """Return setting."""
        if "_settings" not in self.__dict__ or item not in self.__dict__['settings']:
            raise AttributeError()
        return self.get_setting_value(item)

    def get_setting_machine_var(self, setting_name):
        """Return machine var name."""
        return self._settings[setting_name].machine_var

    def get_setting_value(self, setting_name):
        """Return the current value of a setting."""
        if setting_name not in self._settings:
            raise AssertionError("Invalid setting {}".format(setting_name))

        if not self.machine.is_machine_var(self._settings[setting_name].machine_var):
            value = self._settings[setting_name].default
        else:
            value = self.machine.get_machine_var(self._settings[setting_name].machine_var)

        self.debug_log("Retrieving value: {}={}".format(setting_name, value))

        return value

    def set_setting_value(self, setting_name, value):
        """Set the value of a setting."""
        self.debug_log("New value: {}={}".format(setting_name, value))

        if setting_name not in self._settings:
            raise AssertionError("Invalid setting {}".format(setting_name))

        if value not in self._settings[setting_name].values:
            raise AssertionError("Invalid value {} for setting {}".format(value, setting_name))

        self.machine.configure_machine_var(name=self._settings[setting_name].machine_var, persist=True)
        self.machine.set_machine_var(name=self._settings[setting_name].machine_var, value=value)
