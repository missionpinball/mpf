from math import ceil
from mpf.core.logging import LogMixin


class FASTAudioInterface(LogMixin):

    """Hardware sound system using the FAST Audio board."""

    __slots__ = ["platform", "machine", "communicator", "amps", "control_pin_pulse_times"]

    def __init__(self, platform, communicator):
        self.platform = platform
        self.machine = platform.machine
        self.communicator = communicator
        self.amps = {'main': {}, 'sub': {}, 'headphones': {}}
        self.control_pin_pulse_times = list()

        # need to get this in before the soft_reset(), but after machine vars load
        self.machine.events.add_handler('init_phase_1', self._initialize, priority=100)

    def _initialize(self, **kwargs):
        self._configure_machine_vars()
        self._init_amps()
        self._configure_control_pins()
        self._init_hw_config()
        self._register_event_handlers()

    def _configure_machine_vars(self):
        for amp in self.amps.keys():
            var_name = f'fast_audio_{amp}_volume'

            if amp != 'main' and self.communicator.config[f'link_{amp}_to_main']:
                self.machine.variables.set_machine_var(
                    name=var_name,
                    value=self.machine.variables.get_machine_var('fast_audio_main_volume'),
                    persist=self.communicator.config[f'persist_volume_settings'])

            elif not self.machine.variables.is_machine_var(var_name):
                self.machine.variables.set_machine_var(name=var_name,
                                                    value=self.communicator.config[f'default_{amp}_volume'],
                                                    persist=self.communicator.config[f'persist_volume_settings'])
    def _init_amps(self):
        for amp in self.amps.keys():
            self.amps[amp]['steps'] = self.communicator.config[f'{amp}_steps']
            self.amps[amp]['max_volume'] = self.communicator.config[f'max_hw_volume_{amp}']
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
                raise AssertionError(f"Cannot link {amp} to main. The number of volume steps must be the same. "
                                     f"Main has {len(self.amps['main']['levels_list'])} steps, "
                                     f"but {amp} has {len(self.amps[amp]['levels_list'])} steps.")

            self.communicator.set_volume(amp, self.get_hw_volume(amp), send_now=False)

    def _configure_control_pins(self):
        for i in range(6):
            self.control_pin_pulse_times.append(self.communicator.config[f'pin{i+1}_pulse_time'])

        self.control_pin_pulse_times.append(self.communicator.config['power_pulse_time'])
        self.control_pin_pulse_times.append(self.communicator.config['reset_pulse_time'])

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
        self.platform.machine.events.add_handler('machine_var_fast_audio_headphones_volume', self.set_volume, amp='headphones')
        self.platform.machine.events.add_handler('fast_audio_temp_volume', self.temp_volume)
        self.platform.machine.events.add_handler('fast_audio_restore', self.restore_volume)
        self.platform.machine.events.add_handler('fast_audio_pulse_lcd_pin', self.pulse_lcd_pin)
        self.platform.machine.events.add_handler('fast_audio_pulse_power_pin', self.pulse_power_pin)
        self.platform.machine.events.add_handler('fast_audio_pulse_reset_pin', self.pulse_reset_pin)

    def _create_levels_list(self, amp):
        steps = self.communicator.config[f'{amp}_steps']
        max_volume = self.communicator.config[f'max_hw_volume_{amp}']
        step_percent = 1 / steps

        if max_volume > 63:
            raise AssertionError(f"Invalid max_hw_volume_{amp}: {max_volume}")

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
        try:
            return self.amps[amp]['levels_list'][self.get_volume(amp)]
        except IndexError:
            raise AssertionError(f"Invalid volume {self.get_volume(amp)} for amp: {amp}.",
                                 f"There are only {len(self.amps[amp]['levels_list'])} entries in the volume levels list.")

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

    def temp_volume(self, amp, change=1, **kwargs):
        """Temporarily change the volume by the specified number of steps, up or down,
        but without changing the machine var. This is used for ducking or other
        temporary volume changes where you don't want to save it to disk.
        """
        change = int(change)
        self.communicator.set_volume(amp, self.amps['main']['levels_list'][self.get_volume(amp) + change],
                                     send_now=True)

    def restore_volume(self, amp, **kwargs):
        """Restore the volume to the value to the machine var value"""
        self.communicator.set_volume(amp, self.amps['main']['levels_list'][self.get_volume(amp)],
                                     send_now=True)

    def pulse_lcd_pin(self, pin, ms=None, **kwargs):
        """Pulse the specified LCD pin for the specified number of milliseconds.

        pin is the label from the board, 1-6
        """
        if not ms:
            ms = self.control_pin_pulse_times[pin-1]

        pin = int(pin)
        assert 1 <= pin <= 6, f"Invalid pin {pin}"
        # pins are zero indexed in the hardware
        self.communicator.pulse_control_pin(pin-1, ms)

    def pulse_power_pin(self, ms=None, **kwargs):
        """Pulse the specified power pin for the specified number of milliseconds."""
        if not ms:
            ms = self.control_pin_pulse_times[6]
        self.communicator.pulse_control_pin(6, ms)

    def pulse_reset_pin(self, ms=None, **kwargs):
        """Pulse the specified reset pin for the specified number of milliseconds."""
        if not ms:
            ms = self.control_pin_pulse_times[7]
        self.communicator.pulse_control_pin(7, ms)
