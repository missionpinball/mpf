"""Hardware sound system using the FAST Audio board."""

from math import ceil
from mpf.core.logging import LogMixin
from mpf.core.settings_controller import SettingEntry

VARIABLE_NAME = "fast_audio_%s_volume"
SETTING_TYPE = "hw_volume"


class FASTAudioInterface(LogMixin):

    """Hardware sound system using the FAST Audio board."""

    __slots__ = ["platform", "machine", "communicator", "amps", "control_pin_pulse_times"]

    def __init__(self, platform, communicator):
        """Initialize audio interface."""
        super().__init__()
        self.platform = platform
        self.machine = platform.machine
        self.communicator = communicator
        self.amps = {
            'main': {'name': 'fast_audio_main', 'label': "Speakers", 'sort': 0},
            'sub': {'name': 'fast_audio_sub', 'label': "Subwoofer", 'sort': 1},
            'headphones': {'name': 'fast_audio_headphones', 'label': "Headphones", 'sort': 2}
        }
        self.control_pin_pulse_times = list()

        # need to get this in before the soft_reset(), but after machine vars load
        self.machine.events.add_handler('init_phase_1', self._initialize, priority=100)

    def _initialize(self, **kwargs):
        del kwargs
        self._configure_machine_vars()
        self._init_amps()
        self._configure_control_pins()
        self._init_hw_config()
        self._register_event_handlers()

    def _configure_machine_vars(self):
        # See if main volume has been defined yet, otherwise use default
        main_volume = self.machine.variables.get_machine_var('fast_audio_main_volume')
        if main_volume is None:
            main_volume = self.communicator.config['default_main_volume']

        for amp_name, settings in self.amps.items():

            default_value = self.communicator.config[f'default_{amp_name}_volume']
            if self.communicator.config.get(f'link_{amp_name}_to_main', False):
                machine_var_name = VARIABLE_NAME % "main"
            else:
                machine_var_name = VARIABLE_NAME % amp_name

                # Create a machine variable if one doesn't exist
                if not self.machine.variables.is_machine_var(machine_var_name):
                    self.machine.variables.set_machine_var(machine_var_name, default_value,
                                                           self.communicator.config['persist_volume_settings'])

            # Identify the machine var for this amp
            settings["machine_var"] = machine_var_name
            self.machine.settings.add_setting(SettingEntry(
                settings['name'],
                settings['label'],
                settings['sort'],
                machine_var_name,
                default_value,
                None,
                SETTING_TYPE
            ))

    def _init_amps(self):
        for amp_name, amp in self.amps.items():
            amp['steps'] = self.communicator.config[f'{amp_name}_steps']
            amp['max_volume'] = self.communicator.config[f'max_hw_volume_{amp_name}']
            amp['levels_list'] = self.communicator.config[f'{amp_name}_levels_list']

            # Just set everything here. The communicator will send the
            # config as part of its init process later
            if self.communicator.config[f'{amp_name}_amp_enabled']:
                self.communicator.enable_amp(amp_name, send_now=False)

            if not amp['levels_list']:
                self._create_levels_list(amp_name)
            else:
                # if we have a levels list in the config, make sure the steps num is right
                amp['steps'] = len(amp['levels_list']) - 1

            if self.communicator.config[f'link_{amp_name}_to_main'] and \
                    len(amp['levels_list']) != len(self.amps['main']['levels_list']):
                raise AssertionError(f"Cannot link {amp_name} to main. The number of volume steps must be the same. "
                                     f"Main has {len(self.amps['main']['levels_list'])} steps, "
                                     f"but {amp_name} has {len(amp['levels_list'])} steps.")

        # Write the volume levels to the hardware layer, but no need to send
        # them because (regular priority) init_phase_1 includes a soft_reset()
        self.send_volume_to_hw(send_now=False)

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
        self.platform.machine.events.add_handler('machine_var_fast_audio_main_volume',
                                                 self._set_volume, amp_name='main')
        self.platform.machine.events.add_handler('machine_var_fast_audio_sub_volume',
                                                 self._set_volume, amp_name='sub')
        self.platform.machine.events.add_handler('machine_var_fast_audio_headphones_volume',
                                                 self._set_volume, amp_name='headphones')
        self.platform.machine.events.add_handler('fast_audio_temp_volume', self.temp_volume)
        self.platform.machine.events.add_handler('fast_audio_restore', self.restore_volume)
        self.platform.machine.events.add_handler('fast_audio_pulse_lcd_pin', self.pulse_lcd_pin)
        self.platform.machine.events.add_handler('fast_audio_pulse_power_pin', self.pulse_power_pin)
        self.platform.machine.events.add_handler('fast_audio_pulse_reset_pin', self.pulse_reset_pin)

    def _create_levels_list(self, amp_name):
        steps = self.communicator.config[f'{amp_name}_steps']
        max_volume = self.communicator.config[f'max_hw_volume_{amp_name}']
        step_percent = 1 / steps

        if max_volume > 63:
            raise AssertionError(f"Invalid max_hw_volume_{amp_name}: {max_volume}")

        for i in range(steps):
            volume = ceil(max_volume * (1 - (i * step_percent)))
            self.amps[amp_name]['levels_list'].append(volume)

        # technically our list is number of volume levels + 1, since that's more logicial
        # for humans. e.g. 20 volume steps of 5% each is 0-100% volume, which
        # has 21 items in the list.
        self.amps[amp_name]['levels_list'].append(0)
        self.amps[amp_name]['levels_list'].reverse()

    def send_volume_to_hw(self, amp_name=None, send_now=True):
        """Send the current volume to the hardware."""
        if amp_name is None:
            for each_amp_name in self.amps:
                self.send_volume_to_hw(each_amp_name, send_now)
            return
        self.communicator.set_volume(amp_name, self.get_volume(amp_name), send_now)

    def _set_volume(self, amp_name, value=0, **kwargs):
        """Set the amp volume to the specified level, in absolute units.

        This is a private method, volume changes should be instigated by
        updating the corresponding machine variable.
        """
        del kwargs
        value = int(value)

        if value > self.amps[amp_name]['max_volume']:
            value = self.amps[amp_name]['max_volume']
        elif value < 0:
            value = 0

        #self.platform.debug_log("Writing FAST amp volume %s to %s (decimal)", amp_name, value)
        self.send_volume_to_hw(amp_name)

    def get_volume(self, amp_name, **kwargs):
        """Return the current volume of the specified amp."""
        del kwargs
        return self.machine.variables.get_machine_var(self.amps[amp_name]["machine_var"]) or 0

    def _set_machine_var_volume(self, amp_name, value):
        self.machine.variables.set_machine_var(self.amps[amp_name]["machine_var"], value)

    def temp_volume(self, amp_name, change=1, **kwargs):
        """Temporarily change the volume by the specified number of units, up or down.

        This changes without changing the machine var, and is used for ducking or other
        temporary volume changes where you don't want to save it to disk.
        """
        del kwargs
        change = int(change)
        self.communicator.set_volume(amp_name, self.get_volume(amp_name) + change,
                                     send_now=True)

    def restore_volume(self, amp_name, **kwargs):
        """Restore the volume to the value to the machine var value."""
        del kwargs
        self.communicator.set_volume(amp_name, self.get_volume(amp_name),
                                     send_now=True)

    def pulse_lcd_pin(self, pin, ms=None, **kwargs):
        """Pulse the specified LCD pin for the specified number of milliseconds.

        pin is the label from the board, 1-6
        """
        del kwargs
        if not ms:
            ms = self.control_pin_pulse_times[pin - 1]

        pin = int(pin)
        assert 1 <= pin <= 6, f"Invalid pin {pin}"
        # pins are zero indexed in the hardware
        self.communicator.pulse_control_pin(pin - 1, ms)

    def pulse_power_pin(self, ms=None, **kwargs):
        """Pulse the specified power pin for the specified number of milliseconds."""
        del kwargs
        if not ms:
            ms = self.control_pin_pulse_times[6]
        self.communicator.pulse_control_pin(6, ms)

    def pulse_reset_pin(self, ms=None, **kwargs):
        """Pulse the specified reset pin for the specified number of milliseconds."""
        del kwargs
        if not ms:
            ms = self.control_pin_pulse_times[7]
        self.communicator.pulse_control_pin(7, ms)

    def save_settings_to_firmware(self, **kwargs):
        """Write the current volume settings to the platform's memory."""
        del kwargs
        self.communicator.save_settings_to_firmware()
