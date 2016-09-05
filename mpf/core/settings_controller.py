"""Manages operator controllable settings."""
from collections import namedtuple

from mpf.core.mpf_controller import MpfController

SettingEntry = namedtuple("SettingEntry", ["name", "label", "sort", "machine_var", "default", "values"])


class SettingsController(MpfController):

    """Manages operator controllable settings.

    Attributes:
        _settings(dict[str, SettingEntry]): Available settings
    """

    def __init__(self, machine):
        super().__init__(machine)

        # start with default settings
        self._settings = {}

    def add_setting(self, setting: SettingEntry):
        """Add a setting."""
        self._settings[setting.name] = setting

    def get_settings(self) -> {str, SettingEntry}:
        """Return all available settings."""
        sorted = list(self._settings.values())
        sorted.sort(key=lambda x: x.sort)
        return sorted

    def get_setting_value_label(self, setting_name):
        """Return label for value."""
        value = self.get_setting_value(setting_name)
        return self._settings[setting_name].values.get(value, "invalid")

    def get_setting_value(self, setting_name):
        """Return the current value of a setting."""
        if setting_name not in self._settings:
            raise AssertionError("Invalid setting {}".format(setting_name))

        if not self.machine.is_machine_var(self._settings[setting_name].machine_var):
            return self._settings[setting_name].default

        return self.machine.get_machine_var(self._settings[setting_name].machine_var)

    def set_setting_value(self, setting_name, value):
        if setting_name not in self._settings:
            raise AssertionError("Invalid setting {}".format(setting_name))

        if value not in self._settings[setting_name].values:
            raise AssertionError("Invalid value {} for setting {}".format(value, setting_name))

        self.machine.create_machine_var(persist=True, name=self._settings[setting_name].machine_var, value=value)
