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
        """Initialise settings controller."""
        super().__init__(machine)

        # start with default settings
        self._settings = {}

        self._add_entries_from_config()

    def _add_entries_from_config(self):
        # add entries from config
        self.config = self.machine.config.get('settings', {})
        for name, settings in self.config.items():
            settings = self.machine.config_validator.validate_config("settings", settings)
            if not settings['machine_var']:
                settings['machine_var'] = name
            values = {}
            for key, value in settings['values'].items():
                if settings['key_type'] == "int":
                    key = int(key)
                elif settings['key_type'] == "float":
                    key = float(key)
                values[key] = value
            if settings['key_type'] == "int":
                settings['default'] = int(settings['default'])
            elif settings['key_type'] == "float":
                settings['default'] = float(settings['default'])

            self.add_setting(SettingEntry(name, settings['label'], settings['sort'], settings['machine_var'],
                                          settings['default'], values))

    def add_setting(self, setting: SettingEntry):
        """Add a setting."""
        self._settings[setting.name] = setting

    def get_settings(self) -> {str, SettingEntry}:
        """Return all available settings."""
        sorted_list = list(self._settings.values())
        sorted_list.sort(key=lambda x: x.sort)
        return sorted_list

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
        """Set the value of a setting."""
        if setting_name not in self._settings:
            raise AssertionError("Invalid setting {}".format(setting_name))

        if value not in self._settings[setting_name].values:
            raise AssertionError("Invalid value {} for setting {}".format(value, setting_name))

        self.machine.create_machine_var(persist=True, name=self._settings[setting_name].machine_var, value=value)
