"""Base class for config players which have multiple entries."""
import abc

from mpf.core.config_player import ConfigPlayer


class DeviceConfigPlayer(ConfigPlayer, metaclass=abc.ABCMeta):

    """Base class for config players which have multiple entries."""

    def validate_config_entry(self, settings, name):
        """Validate one entry of this player."""
        validated_config = dict()

        # settings here is the same as a show entry, so we process with
        # that
        if not isinstance(settings, dict):
            if isinstance(settings, (str, int, float)):
                settings = {settings: dict()}
            else:
                raise AssertionError("Invalid settings for player {}:{}".format(self.show_section, name))

        # settings here are dicts of devices/settings
        for device, device_settings in settings.items():
            validated_config.update(
                self._validate_config_item(device, device_settings))

        return validated_config

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
            if self.device_collection:
                devices = self.device_collection.items_tagged(device)
                if not devices:
                    devices = [self.device_collection[device]]

            else:
                devices = [device]

        except KeyError:
            devices = [device]

        return_dict = dict()
        for device in devices:
            return_dict[device] = device_settings

        return return_dict

    @abc.abstractmethod
    def play(self, settings, context, priority=0, **kwargs):
        """Directly play player."""
        # **kwargs since this is an event callback
        raise NotImplementedError

    @abc.abstractmethod
    def get_express_config(self, value):
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
            value: The single line string value from a config file.

        Returns:
            A dictionary (which will then be passed through the config
            validator)

        """
        raise NotImplementedError(self.config_file_section)
