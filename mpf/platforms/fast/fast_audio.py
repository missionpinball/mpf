from math import ceil
from mpf.core.logging import LogMixin


class FASTAudioInterface(LogMixin):

    """Hardware sound system using the FAST Audio board."""

    # __slots__ = []

    def __init__(self, platform, communicator):
        self.platform = platform
        self.communicator = communicator

        self.current_volume = 0
        self.current_headphones_volume = 0
        self.friendly_max_volume = communicator.config['friendly_max_volume']
        self.volume_map = list()

        # Just set everything here. The communicator will update the
        # config on its own as part of its init process
        if communicator.config['main_amp_enabled']:
            communicator.enable_amp('main', send_now=False)
        if communicator.config['sub_amp_enabled']:
            communicator.enable_amp('sub', send_now=False)
        if communicator.config['headphones_amp_enabled']:
            communicator.enable_amp('headphones', send_now=False)

        communicator.set_phones_level(communicator.config['headphones_level'], send_now=False)

        if communicator.config['mute_speakers_with_headphones']:
            phones = 'mute'
        else:
            phones = 'ignore'

        # TODO register for master volume machine variable changes
        # TODO register for headphone volume changes & other control events

        self.volume_map = communicator.config['volume_map']
        if not self.volume_map:
            self.create_volume_map()

        communicator.set_phones_behavior(phones, send_now=False)

        # TODO read in machine vars, fall back to defaults if not set
        self.current_volume = communicator.config['default_volume']
        self.current_headphones_volume = communicator.config['default_headphones_volume']

        self.communicator.set_volume('main', self.volume_map[self.current_volume][0], send_now=False)
        self.communicator.set_volume('sub', self.volume_map[self.current_volume][1], send_now=False)

        # TODO change below to use the headphone steps, create headphone map
        self.communicator.set_volume('headphones', self.current_headphones_volume, send_now=False)

    def create_volume_map(self):
        steps = self.communicator.config['friendly_volume_steps']
        max_volume_main = self.communicator.config['max_volume_main']
        max_volume_sub = self.communicator.config['max_volume_sub']
        sub_percent_of_main = max_volume_sub / max_volume_main
        step_percent = 1 / steps

        # calculate the sub and main volume for each step
        for i in range(steps):
            main_volume = ceil(max_volume_main * (1 - (i * step_percent)))
            sub_volume = ceil(main_volume * sub_percent_of_main)
            self.volume_map.append((main_volume, sub_volume))

        # technically our list is number of volume levels + 1, but that's more logicial
        # for humans. e.g. 20 volume steps of 5% each is 0-100% volume, but
        # it's 21 items in the list.
        self.volume_map.append((0, 0))
        self.volume_map.reverse()

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
