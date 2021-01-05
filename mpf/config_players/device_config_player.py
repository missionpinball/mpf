"""Base class for config players which have multiple entries."""
from typing import List

import abc

from mpf.core.utility_functions import Util

from mpf.core.config_player import ConfigPlayer
from mpf.exceptions.base_error import BaseError
from mpf.exceptions.config_file_error import ConfigFileError


class DeviceConfigPlayer(ConfigPlayer, metaclass=abc.ABCMeta):

    """Base class for config players which have multiple entries."""

    __slots__ = []  # type: List[str]

    allow_placeholders_in_keys = False

    def expand_config_entry(self, settings):
        """Expend objects in config entry idempotently."""
        expanded_config = dict()
        for device, device_settings in settings.items():
            device_settings = self._expand_device_config(device_settings)

            devices = self._expand_device(device)

            for this_device in devices:
                expanded_config[this_device] = device_settings

        return expanded_config

    def validate_config_entry(self, settings, name):
        """Validate one entry of this player."""
        validated_config = dict()

        # settings here is the same as a show entry, so we process with
        # that
        if not isinstance(settings, dict):
            if isinstance(settings, (str, int, float)):
                settings = self.get_string_config(settings)
            else:
                raise AssertionError(
                    "Invalid settings for player {}:{} {}".format(
                        name, self.show_section, settings))

        # settings here are dicts of devices/settings
        for device, device_settings in settings.items():
            try:
                validated_config.update(
                    self._validate_config_item(device, device_settings))
            except ConfigFileError as e:
                e.extend("Failed to load config player {}:{} with settings {}".format(
                    name, self.show_section, settings))
                raise e

        return validated_config

    # pylint: disable-msg=no-self-use
    def get_string_config(self, string):
        """Parse string config."""
        return {string: dict()}

    def _validate_config_item(self, device, device_settings):
        """Validate show config."""
        # override if you need a different show processor from config file
        # processor

        # the input values are this section's single step in a show.

        # keys are device names
        # vales are either scalars with express settings, or dicts with full
        # settings

        if device_settings is None:
            device_settings = device

        device_settings = self._parse_config(device_settings, device)
        try:
            device_settings = self._expand_device_config(device_settings)
        except BaseError as e:
            e.extend('Failed to expand entry "{}".'.format(device))
            raise e

        devices = self._expand_device(device)

        return_dict = dict()
        for this_device in devices:
            return_dict[this_device] = device_settings

        return return_dict

    def _expand_device(self, device):
        """Idempotently expand device if it is a placeholder."""
        if not isinstance(device, str):
            return [device]

        device_or_tag_names = Util.string_to_event_list(device)
        if not self.device_collection:
            return device_or_tag_names

        device_list = []
        for device_name in device_or_tag_names:
            try:
                devices = self.device_collection.items_tagged(device_name)
                if not devices:
                    device_list.append(self.device_collection[device_name])
                else:
                    device_list.extend(devices)

            except KeyError:
                if not self.__class__.allow_placeholders_in_keys or "(" not in device_name:
                    # no placeholders
                    return self.raise_config_error(
                        "Could not find a {} device with name or tag {}, from list {}".format(
                            self.device_collection.name, device_name, device_or_tag_names),
                        101)

                # placeholders may be evaluated later
                device_list.append(device_name)
        return device_list

    def _expand_device_config(self, device_settings):
        """Idempotently expand device config."""
        return device_settings

    @abc.abstractmethod
    def play(self, settings, context: str, calling_context: str, priority: int = 0, **kwargs):
        """Directly play player."""
        # **kwargs since this is an event callback
        raise NotImplementedError

    @abc.abstractmethod
    def get_express_config(self, value) -> dict:
        """Parse short config version.

        Implements "express" settings for this config_player which is what
        happens when a config is passed as a string instead of a full config
        dict. (This is detected automatically and this method is only called
        when the config is not a dict.)

        For example, the led_player uses the express config to parse a string
        like 'ff0000-f.5s' and translate it into:

        color: 220000
        fade: 500

        Since every config_player is different, this method raises a
        NotImplementedError and most be configured in the child class.

        Args:
        ----
            value: The single line string value from a config file.

        Returns a dictionary (which will then be passed through the config
        validator)
        """
        raise NotImplementedError(self.config_file_section)
