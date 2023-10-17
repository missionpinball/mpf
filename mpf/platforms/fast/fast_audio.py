from math import ceil
from mpf.core.logging import LogMixin


class FASTAudioInterface(LogMixin):

    """Hardware sound system using the FAST Audio board."""

    __slots__ = ["platform", "communicator", "current_volume", "current_headphones_volume", "temp_ducked_volume_steps",
                 "friendly_max_volume", "friendly_max_headphone_volume", "volume_map", "headphones_map",
                 "link_phones_to_main"]

    def __init__(self, platform, communicator):
        self.platform = platform
        self.communicator = communicator

        self.current_volume = 0
        self.current_headphones_volume = 0
        self.temp_ducked_volume_steps = 0
        self.friendly_max_volume = communicator.config['friendly_max_volume']
        self.friendly_max_headphone_volume = communicator.config['friendly_max_headphone_volume']
        self.volume_map = list()
        self.headphones_map = list()

        # changes phones with main volume, useful for line out, 3rd amp, etc.
        self.link_phones_to_main = communicator.config['link_phones_to_main']

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
            self._create_volume_map()
        else:
            self.friendly_max_volume = len(self.volume_map) - 1

        if not self.headphones_map:
            self._create_headphones_map()
        else:
            self.friendly_max_headphone_volume = len(self.headphones_map) - 1

        communicator.set_phones_behavior(phones, send_now=False)

        # TODO read in machine vars, fall back to defaults if not set
        self.current_volume = communicator.config['default_volume']

        if self.link_phones_to_main:
            self.current_headphones_volume = self.current_volume
        else:
            self.current_headphones_volume = communicator.config['default_headphones_volume']

        self.communicator.set_volume('main', self.volume_map[self.current_volume][0], send_now=False)
        self.communicator.set_volume('sub', self.volume_map[self.current_volume][1], send_now=False)
        self.communicator.set_volume('headphones', self.headphones_map[self.current_headphones_volume], send_now=False)

    def _create_volume_map(self):
        # volume_map is a list of tuples, each tuple is (main_volume, sub_volume)
        # the list index is the friendly volume level, e.g. 0-20
        # volume_map[0] will always be (0,0)
        # the highest will always be (max_volume_main, max_volume_sub)
        # valid values in the map are 0-63. These are the technical hardware
        # volume levels. Users will see the friendly volume levels, e.g. 0-20
        steps = self.communicator.config['friendly_max_volume']
        max_volume_main = self.communicator.config['max_volume_main']
        max_volume_sub = self.communicator.config['max_volume_sub']
        sub_percent_of_main = max_volume_sub / max_volume_main
        step_percent = 1 / steps

        if  max_volume_main > 63:
            raise AssertionError(f"Invalid max_volume_main: {max_volume_main}")
        if max_volume_sub > 63:
            raise AssertionError(f"Invalid max_volume_sub: {max_volume_sub}")

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

    def _create_headphones_map(self):
        steps = self.communicator.config['friendly_max_headphone_volume']
        max_volume = self.communicator.config['max_volume_headphones']
        step_percent = 1 / steps

        if max_volume > 63:
            raise AssertionError(f"Invalid max_volume_headphones: {max_volume}")

        for i in range(steps):
            volume = ceil(max_volume * (1 - (i * step_percent)))
            self.headphones_map.append(volume)

        self.headphones_map.append(0)
        self.headphones_map.reverse()

    def send_volume_to_hw(self):
        self.communicator.set_volume('main', self.volume_map[self.current_volume][0])
        self.communicator.set_volume('sub', self.volume_map[self.current_volume][1])

    def send_headphones_volume_to_hw(self):
        self.communicator.set_volume('headphones', self.headphones_map[self.current_headphones_volume])

    def increase_volume(self, steps=1, **kwargs):
        """Increase the volume by the specified number of steps."""
        self.set_volume(self.current_volume + int(steps))

    def decrease_volume(self, steps=1, **kwargs):
        """Decrease the volume by the specified number of steps."""
        self.set_volume(self.current_volume - int(steps))

    def set_volume(self, volume=0, **kwargs):
        """Set the main/sub volume to the specified level, using the volume map"""
        volume = int(volume)

        if volume > self.friendly_max_volume:
            volume = self.friendly_max_volume
        elif volume < 0:
            volume = 0

        self.current_volume = volume
        self.send_volume_to_hw()

        if self.link_phones_to_main:
            self.set_headphones_volume(volume)

    def increase_headphones_volume(self, steps=1, **kwargs):
        """Increase the headphones volume by the specified number of steps."""
        self.set_headphones_volume(self.current_headphones_volume + int(steps))

    def decrease_headphones_volume(self, steps=1, **kwargs):
        """Decrease the headphones volume by the specified number of steps."""
        self.set_headphones_volume(self.current_headphones_volume - int(steps))

    def set_headphones_volume(self, volume=0, **kwargs):
        """Set the headphones volume to the specified level using the
        headphones map"""

        if self.link_phones_to_main:
            return False  # use set_volume() instead

        volume = int(volume)

        if volume > self.friendly_max_headphone_volume:
            volume = self.friendly_max_headphone_volume
        elif volume < 0:
            volume = 0

        self.current_headphones_volume = volume
        self.send_headphones_volume_to_hw()
        return True

    def temp_duck_volume(self, steps=1, **kwargs):
        """Temporarily duck the volume by the specified number of steps.
        The original value will be saved and can be restored with
        restore_volume().
        """
        steps = int(steps)
        self.temp_ducked_volume_steps = steps
        self.set_volume(self.current_volume - steps)

    def restore_volume(self, **kwargs):
        """Restore the volume to the value it was before the last"""
        self.set_volume(self.current_volume + self.temp_ducked_volume_steps)

    def pulse_lcd_pin(self, pin, ms=100, **kwargs):
        """Pulse the specified LCD pin for the specified number of milliseconds."""
        self.communicator.pulse_lcd_pin(pin, ms)
