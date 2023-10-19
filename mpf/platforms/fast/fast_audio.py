from math import ceil
from mpf.core.logging import LogMixin


class FASTAudioInterface(LogMixin):

    """Hardware sound system using the FAST Audio board."""

    # __slots__ = ["platform", "communicator", "amps", "temp_ducked_volume_steps"]

    def __init__(self, platform, communicator):
        self.platform = platform
        self.machine = platform.machine
        self.communicator = communicator
        self.amps = {'main': {}, 'sub': {}, 'headphones': {}}
        self.temp_ducked_volume_steps = 0

        # need to get this in before the soft_reset(), but after machine vars load
        self.machine.events.add_handler('init_phase_1', self._initialize, priority=100)

    def _initialize(self, **kwargs):
        self._configure_machine_vars()
        self._init_amps()
        self._init_hw_config()
        self._register_event_handlers()

    def _configure_machine_vars(self):
        for amp in self.amps.keys():
            var_name = f'fast_audio_{amp}_volume'

            if amp != 'main' and self.communicator.config[f'link_{amp}_to_main']:
                value_to_set = self.machine.variables.get_machine_var('fast_audio_main_volume')
            else:
                value_to_set = self.communicator.config[f'default_{amp}_volume']

            # Check if the machine variable already exists. If not, set it.
            if not self.machine.variables.is_machine_var(var_name):
                self.machine.variables.set_machine_var(name=var_name,
                                                    value=value_to_set,
                                                    persist=self.communicator.config[f'persist_volume_settings'])
    def _init_amps(self):
        for amp in self.amps.keys():
            self.amps[amp]['steps'] = self.communicator.config[f'{amp}_steps']
            self.amps[amp]['max_volume'] = self.communicator.config[f'max_volume_{amp}']
            self.amps[amp]['levels_list'] = self.communicator.config[f'{amp}_levels_list']
            self.amps[amp]['link_to_main'] = self.communicator.config[f'link_{amp}_to_main']

            # Just set everything here. The communicator will send the
            # config as part of its init process later
            if self.communicator.config[f'{amp}_amp_enabled']:
                self.communicator.enable_amp(amp, send_now=False)

            if not self.amps[amp]['levels_list']:
                self._create_levels_list(amp)
            else:
                # if we have a levels list in the config, make sure the steps num is right
                self.amps[amp]['steps'] = len(self.amps[amp]['levels_list']) - 1

            if self.amps[amp]['link_to_main'] and len(self.amps[amp]['levels_list']) != len(self.amps['main']['levels_list']):
                raise AssertionError(f"Invalid {amp}_levels_list / steps. Must be same length as main_levels_list / steps to link to main.")

            self.communicator.set_volume(amp, self.get_hw_volume(amp), send_now=False)

    def _init_hw_config(self):
        # Just set everything here. The communicator will send it to the board later
        self.communicator.set_phones_level(self.communicator.config['headphones_level'], send_now=False)

        if self.communicator.config['mute_speakers_with_headphones']:
            phones = 'mute'
        else:
            phones = 'ignore'

        self.communicator.set_phones_behavior(phones, send_now=False)

    def _register_event_handlers(self):
        self.platform.machine.events.add_handler('machine_var_fast_audio_main_volume', self.set_volume, amp='main')
        self.platform.machine.events.add_handler('machine_var_fast_audio_sub_volume', self.set_volume, amp='sub')
        self.platform.machine.events.add_handler('fast_audio_headphones_volume', self.set_volume, amp='headphones')
        self.platform.machine.events.add_handler('fast_audio_duck', self.temp_duck_volume, steps=4)
        self.platform.machine.events.add_handler('fast_audio_restore', self.restore_volume)
        self.platform.machine.events.add_handler('fast_audio_pulse_lcd_pin', self.pulse_lcd_pin, pin=1)
        self.platform.machine.events.add_handler('fast_audio_pulse_power_pin', self.pulse_power_pin)
        self.platform.machine.events.add_handler('fast_audio_pulse_reset_pin', self.pulse_reset_pin)

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

        self.communicator.set_volume(amp, self.get_hw_volume(amp))

    def get_hw_volume(self, amp):
        return self.amps[amp]['levels_list'][self.get_volume(amp)]

    def increase_volume(self, amp, change=1, **kwargs):
        """Increase the volume by the specified number of steps."""
        self.set_volume(amp, self.amps[amp]['volume'] + int(change))

    def decrease_volume(self, amp, change=1, **kwargs):
        """Decrease the volume by the specified number of steps."""
        self.set_volume(amp, self.amps[amp]['volume'] - int(change))

    def set_volume(self, amp, value=0, **kwargs):
        """Set the amp volume to the specified level, using the volume map"""
        value = int(value)

        if value > self.amps[amp]['steps']:
            value = self.amps[amp]['steps']
        elif value < 0:
            value = 0

        self.send_volume_to_hw(amp)

        for other_amp in self.amps.keys():
            if self.amps[other_amp]['link_to_main'] and other_amp != amp:
                self._set_machine_var_volume(other_amp, self.amps[amp]['levels_list'][value])
                self.send_volume_to_hw(other_amp)

    def get_volume(self, amp, **kwargs):
        return self.machine.variables.get_machine_var(f'fast_audio_{amp}_volume')

    def _set_machine_var_volume(self, amp, value):
        self.machine.variables.set_machine_var(f'fast_audio_{amp}_volume', value)

    def temp_duck_volume(self, change=1, **kwargs):
        """Temporarily duck the volume by the specified number of steps.
        The original value will be saved and can be restored with
        restore_volume().
        """
        change = int(change)
        self.temp_ducked_volume_steps = change
        self.set_volume('main', self.get_volume('main') - change)

    def restore_volume(self, **kwargs):
        """Restore the volume to the value it was before it was ducked."""
        self.set_volume(self.get_volume('main') + self.temp_ducked_volume_steps)

    def pulse_lcd_pin(self, pin, ms=100, **kwargs):
        """Pulse the specified LCD pin for the specified number of milliseconds.

        pin is the label from the board, 1-6
        """
        pin = int(pin)
        assert 1 <= pin <= 6, f"Invalid pin {pin}"
        # pins are zero indexed in the hardware
        self.communicator.pulse_control_pin(pin-1, ms)

    def pulse_power_pin(self, ms=100, **kwargs):
        """Pulse the specified power pin for the specified number of milliseconds."""
        self.communicator.pulse_control_pin(6, ms)

    def pulse_reset_pin(self, ms=100, **kwargs):
        """Pulse the specified reset pin for the specified number of milliseconds."""
        self.communicator.pulse_control_pin(7, ms)
