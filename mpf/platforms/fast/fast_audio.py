from math import ceil
from mpf.core.logging import LogMixin


class FASTAudioInterface(LogMixin):

    """Hardware sound system using the FAST Audio board."""

    __slots__ = ["platform", "communicator", "amps", "temp_ducked_volume_steps"]

    def __init__(self, platform, communicator):
        self.platform = platform
        self.communicator = communicator

        self.amps = {'main': {}, 'sub': {}, 'headphones': {}}

        for amp in self.amps.keys():

            self.amps[amp]['steps'] = communicator.config[f'{amp}_steps']
            self.amps[amp]['max_volume'] = communicator.config[f'max_volume_{amp}']
            self.amps[amp]['levels_list'] = communicator.config[f'{amp}_levels_list']
            self.amps[amp]['link_to_main'] = communicator.config[f'link_{amp}_to_main']

            # Just set everything here. The communicator will update the
            # config on its own as part of its init process
            if communicator.config[f'{amp}_amp_enabled']:
                communicator.enable_amp(amp, send_now=False)

            if not self.amps[amp]['levels_list']:
                self._create_levels_list(amp)
            else:
                # if we have a levels list in the config, make sure the steps num is right
                self.amps[amp]['steps'] = len(self.amps[amp]['levels_list']) - 1

            # TODO read in machine vars, fall back to defaults if not set
            self.amps[amp]['volume'] = communicator.config['default_main_volume']

            if self.amps[amp]['link_to_main']:
                if len(self.amps[amp]['levels_list']) != len(self.amps['main']['levels_list']):
                    raise AssertionError(f"Invalid {amp}_levels_list. Must be same length as main_levels_list")

                self.amps[amp]['volume'] = self.amps['main']['volume']
            else:
                self.amps[amp]['volume'] = communicator.config[f'default_{amp}_volume']

            self.communicator.set_volume(amp, self.amps[amp]['volume'], send_now=False)

            # TODO register for machine var volume changes & other control events

        # Set audio board config

        communicator.set_phones_level(communicator.config['headphones_level'], send_now=False)

        if communicator.config['mute_speakers_with_headphones']:
            phones = 'mute'
        else:
            phones = 'ignore'

        self.temp_ducked_volume_steps = 0

        communicator.set_phones_behavior(phones, send_now=False)

    def _create_levels_list(self, amp):
        steps = self.communicator.config[f'{amp}_steps']
        max_volume = self.communicator.config[f'max_volume_{amp}']
        step_percent = 1 / steps

        if max_volume > 63:
            raise AssertionError(f"Invalid max_volume_{amp}: {max_volume}")

        for i in range(steps):
            volume = ceil(max_volume * (1 - (i * step_percent)))
            self.amps[amp]['levels_list'].append(volume)

        # technically our list is number of volume levels + 1, since that's more logicial
        # for humans. e.g. 20 volume steps of 5% each is 0-100% volume, which
        # has 21 items in the list.
        self.amps[amp]['levels_list'].append(0)
        self.amps[amp]['levels_list'].reverse()

    def send_volume_to_hw(self, amp=None):
        """Send the current volume to the hardware."""
        if amp is None:
            for amp in self.amps.keys():
                self.send_volume_to_hw(amp)
            return

        self.communicator.set_volume(amp, self.amps[amp]['volume'])

    def increase_volume(self, amp, steps=1, **kwargs):
        """Increase the volume by the specified number of steps."""
        self.set_volume(amp, self.amps[amp]['volume'] + int(steps))

    def decrease_volume(self, amp, steps=1, **kwargs):
        """Decrease the volume by the specified number of steps."""
        self.set_volume(amp, self.amps[amp]['volume'] - int(steps))

    def set_volume(self, amp, volume=0, **kwargs):
        """Set the amp volume to the specified level, using the volume map"""
        volume = int(volume)

        if volume > self.amps[amp]['steps']:
            volume = self.amps[amp]['steps']
        elif volume < 0:
            volume = 0

        self.amps[amp]['volume'] = volume
        self.send_volume_to_hw(amp)

        for other_amp in self.amps.keys():
            if self.amps[other_amp]['link_to_main'] and other_amp != amp:
                self.amps[other_amp]['volume'] = volume
                self.send_volume_to_hw(other_amp)

        # TODO write new machine var (verify if it's the same value that it
        # won't re-post)

    def temp_duck_volume(self, steps=1, **kwargs):
        """Temporarily duck the volume by the specified number of steps.
        The original value will be saved and can be restored with
        restore_volume().
        """
        steps = int(steps)
        self.temp_ducked_volume_steps = steps
        self.set_volume('main', self.amps['main']['volume'] - steps)

    def restore_volume(self, **kwargs):
        """Restore the volume to the value it was before it was ducked."""
        self.set_volume(self.amps['main']['volume'] + self.temp_ducked_volume_steps)

    def pulse_lcd_pin(self, pin, ms=100, **kwargs):
        """Pulse the specified LCD pin for the specified number of milliseconds."""
        self.communicator.pulse_lcd_pin(pin, ms)
