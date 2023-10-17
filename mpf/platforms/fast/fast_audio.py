from math import ceil
from mpf.core.utility_functions import Util
from mpf.core.logging import LogMixin


class FASTAudioInterface(LogMixin):

    """Hardware sound system using the FAST Audio board."""

    # __slots__ = []

    def __init__(self, platform, communicator):
        self.platform = platform
        self.communicator = communicator

        self.volume_steps = communicator.config['volume_steps']
        self.volume_scale = communicator.config['volume_scale']
        self.sub_percent_of_main = communicator.config['sub_percent_of_main']

        self.current_volume = 0
        self.main_volume = 0
        self.sub_volume = 0
        self.phones_volume = 0

        # TODO set amp enable settings
        self.communicator.set_phones_level(communicator.config['headphones_level'], False)
        self.communicator.set_phones_behavior(communicator.config['mute_speakers_with_headphones'], False)
        self.communicator.send_config_to_board()

        # TODO send initial volumes

        # TODO register for master volume machine variable changes

    def increase_volume(self, steps=1):
        """Increase the volume of both main and sub via the
        ratio specified."""

        # steps are normalized to the config settings

    def decrease_volume(self, steps=1):
        """Decrease the volume of both main and sub via the
        ratio specified."""

    def increase_main_volume(self, steps=1):
        """Increase the volume of the main channel."""

    def decrease_main_volume(self, steps=1):
        """Decrease the volume of the main channel."""

    def set_main_volume(self, volume=0):
        """Set the volume of the main channel."""

    def increase_sub_volume(self, steps=1):
        """Increase the volume of the sub channel."""

    def decrease_sub_volume(self, steps=1):
        """Decrease the volume of the sub channel."""

    def set_sub_volume(self, volume=0):
        """Set the volume of the sub channel."""

    def increase_headphones_volume(self, steps=1):
        """Increase the volume of the headphones channel."""

    def decrease_headphones_volume(self, steps=1):
        """Decrease the volume of the headphones channel."""

    def set_headphones_volume(self, volume=0):
        """Set the volume of the headphones channel."""

    def temp_duck_volume(self):
        """Restore the main volume to the saved value."""

    def temp_duck_main_volume(self, steps=1):
        """Temporarily duck the main volume."""

    def temp_duck_sub_volume(self, steps=1):
        """Temporarily duck the sub volume."""

    def temp_duck_headphones_volume(self, steps=1):
        """Temporarily duck the headphones volume."""

    def restore_volume(self):
        """Restore the main/sub blended volume to the saved value."""

    def restore_main_volume(self):
        """Restore the main volume to the saved value."""

    def restore_sub_volume(self):
        """Restore the sub volume to the saved value."""

    def restore_headphones_volume(self):
        """Restore the headphones volume to the saved value."""

    def pulse_lcd_pin(self, pin, ms=100):
        """Pulse the LCD pin."""
