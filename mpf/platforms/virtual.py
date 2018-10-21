"""Contains code for a virtual hardware platform."""
import asyncio
import logging
from typing import Callable, Tuple

from mpf.platforms.interfaces.hardware_sound_platform_interface import HardwareSoundPlatformInterface
from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface

from mpf.exceptions.ConfigFileError import ConfigFileError
from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface

from mpf.core.platform import ServoPlatform, SwitchPlatform, DriverPlatform, AccelerometerPlatform, I2cPlatform, \
    DmdPlatform, RgbDmdPlatform, LightsPlatform, DriverConfig, SwitchConfig, SegmentDisplayPlatform, StepperPlatform, \
    HardwareSoundPlatform
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings


class VirtualHardwarePlatform(AccelerometerPlatform, I2cPlatform, ServoPlatform, LightsPlatform, SwitchPlatform,
                              DriverPlatform, DmdPlatform, RgbDmdPlatform, SegmentDisplayPlatform, StepperPlatform,
                              HardwareSoundPlatform):

    """Base class for the virtual hardware platform."""

    def __init__(self, machine):
        """Initialise virtual platform."""
        super().__init__(machine)
        self._setup_log()

        # Since the virtual platform doesn't have real hardware, we need to
        # maintain an internal list of switches that were confirmed so we have
        # something to send when MPF needs to know the hardware states of
        # switches
        self.hw_switches = dict()
        self.initial_states_sent = False
        self.features['tickless'] = True
        self._next_driver = 1000
        self._next_switch = 1000
        self._next_light = 1000
        self.rules = {}

    def __repr__(self):
        """Return string representation."""
        return '<Platform.Virtual>'

    def _setup_log(self):
        self.log = logging.getLogger("Virtual Platform")
        self.log.debug("Configuring virtual hardware interface.")

    @asyncio.coroutine
    def initialize(self):
        """Initialise platform."""
        pass

    def stop(self):
        """Stop platform."""
        pass

    def configure_servo(self, number: str):
        """Configure a servo device in paltform."""
        return VirtualServo(number)

    def configure_stepper(self, number: str, config: dict):
        """Configure a smart stepper / axis device in platform."""
        del config
        return VirtualStepper(number)

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
        """Configure driver."""
        del platform_settings
        # generate number if None
        if number is None:
            number = self._next_driver
            self._next_driver += 1

        driver = VirtualDriver(config, number)

        return driver

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict):
        """Configure switch."""
        # switch needs a number to be distingishable from other switches
        if number is None:
            number = self._next_switch
            self._next_switch += 1

        # We want to have the virtual platform set all the initial switch states
        # to inactive, so we have to check the config.
        self.hw_switches[number] = config.invert

        return VirtualSwitch(config, number)

    @asyncio.coroutine
    def get_hw_switch_states(self):
        """Return hw switch states."""
        if not self.initial_states_sent:

            if 'virtual_platform_start_active_switches' in self.machine.config:

                initial_active_switches = []
                for switch in Util.string_to_list(self.machine.config['virtual_platform_start_active_switches']):
                    if switch not in self.machine.switches:
                        raise ConfigFileError("Switch {} used in virtual_platform_start_active_switches was not found "
                                              "in switches section.".format(switch), 1, self.log.name)
                    initial_active_switches.append(self.machine.switches[switch].hw_switch.number)

                for k in self.hw_switches:
                    if k in initial_active_switches:
                        self.hw_switches[k] ^= 1

            self.initial_states_sent = True

        else:
            switches = [x for x in self.machine.switches if x.platform == self]

            for switch in switches:
                self.hw_switches[switch.hw_switch.number] = switch.state ^ switch.invert

        return self.hw_switches

    def _get_platforms(self):
        platforms = []
        for name, platform in self.machine.config['mpf']['platforms'].items():
            if name == "virtual" or name == "smart_virtual":
                continue
            platforms.append(Util.string_to_class(platform))
        return platforms

    def validate_switch_section(self, switch, config):
        """Validate switch sections."""
        return config

    def validate_coil_section(self, driver, config):
        """Validate coil sections."""
        return config

    def configure_accelerometer(self, config, callback):
        """Configure accelerometer."""
        pass

    def configure_light(self, number, subtype, platform_settings):
        """Configure light channel."""
        if not subtype:
            subtype = "led"
        return VirtualLight("{}-{}".format(subtype, number), platform_settings)

    # pylint: disable-msg=no-self-use
    def configure_hardware_sound_system(self) -> "HardwareSoundPlatformInterface":
        """Configure virtual hardware sound system."""
        return VirtualSound()

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse channel str to a list of channels."""
        if number is None:
            number = self._next_light
            self._next_light += 1
        if subtype in ("gi", "matrix"):
            return [
                {
                    "number": str(number)
                }
            ]
        elif subtype == "led" or not subtype:
            return [
                {
                    "number": str(number) + "-r",
                },
                {
                    "number": str(number) + "-g",
                },
                {
                    "number": str(number) + "-b",
                }
            ]
        else:
            raise AssertionError("Unknown subtype {}".format(subtype))

    def clear_hw_rule(self, switch, coil):
        """Clear hw rule."""
        if (switch.hw_switch, coil.hw_driver) in self.rules:
            del self.rules[(switch.hw_switch, coil.hw_driver)]
        else:
            self.log.debug("Tried to clear a non-existing rules %s <-> %s", switch, coil)

    def i2c_write8(self, address, register, value):
        """Write to I2C."""
        pass

    @asyncio.coroutine
    def i2c_read8(self, address, register):
        """Read I2C."""
        del address
        del register
        return None

    def i2c_read16(self, address, register):
        """Read I2C."""
        del address
        del register
        return None

    @asyncio.coroutine
    def i2c_read_block(self, address, register, count):
        """Read I2C block."""
        del address
        del register
        del count
        return None

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        """Set rule."""
        if (enable_switch.hw_switch, coil.hw_driver) in self.rules:
            raise AssertionError("Overwrote a rule without clearing it first {} <-> {}".format(
                enable_switch.hw_switch, coil.hw_driver))
        else:
            self.rules[(enable_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit_and_enable_and_release"

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set rule."""
        if (enable_switch.hw_switch, coil.hw_driver) in self.rules:
            raise AssertionError("Overwrote a rule without clearing it first {} <-> {}".format(
                enable_switch.hw_switch, coil.hw_driver))
        else:
            self.rules[(enable_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit_and_release"

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        """Set rule."""
        if (enable_switch.hw_switch, coil.hw_driver) in self.rules:
            raise AssertionError("Overwrote a rule without clearing it first {} <-> {}".format(
                enable_switch.hw_switch, coil.hw_driver))
        else:
            self.rules[(enable_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit_and_enable_and_release_and_disable"
        if (disable_switch.hw_switch, coil.hw_driver) in self.rules:
            raise AssertionError("Overwrote a rule without clearing it first {} <-> {}".format(
                disable_switch.hw_switch, coil.hw_driver))
        else:
            self.rules[(disable_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit_and_enable_and_release_and_disable"

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        """Set rule."""
        if (enable_switch.hw_switch, coil.hw_driver) in self.rules:
            raise AssertionError("Overwrote a rule without clearing it first {} <-> {}".format(
                enable_switch.hw_switch, coil.hw_driver))
        else:
            self.rules[(enable_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit"

    def configure_dmd(self):
        """Configure DMD."""
        return VirtualDmd()

    def configure_rgb_dmd(self, name: str):
        """Configure DMD."""
        del name
        return VirtualDmd()

    def configure_segment_display(self, number: str) -> SegmentDisplayPlatformInterface:
        """Configure segment display."""
        return VirtualSegmentDisplay(number)


class VirtualSegmentDisplay(SegmentDisplayPlatformInterface):

    """Virtual segment display."""

    def __init__(self, number):
        """Initialise virtual segment display."""
        super().__init__(number)
        self.text = ''
        self.flashing = False

    def set_text(self, text: str, flashing: bool):
        """Set text."""
        self.text = text
        self.flashing = flashing


class VirtualSound(HardwareSoundPlatformInterface):

    """Virtual hardware sound interface."""

    def __init__(self):
        """Initialise virtual hardware sound."""
        self.playing = None
        self.volume = None

    def play_sound(self, number: int):
        """Play virtual sound."""
        self.playing = number

    def play_sound_file(self, file: str, platform_options: dict):
        """Play a sound file."""
        self.playing = file

    def text_to_speech(self, text: str, platform_options: dict):
        """Text to speech output."""
        self.playing = text

    def set_volume(self, volume: float):
        """Set volume."""
        self.volume = volume

    def stop_all_sounds(self):
        """Stop sound."""
        self.playing = None


class VirtualDmd(DmdPlatformInterface):

    """Virtual DMD."""

    def __init__(self):
        """Initialise virtual DMD."""
        self.data = None
        self.brightness = None

    def update(self, data: bytes):
        """Update data on the DMD.

        Args:
            data: bytes to send to DMD
        """
        self.data = data

    def set_brightness(self, brightness: float):
        """Set brightness."""
        self.brightness = brightness


class VirtualSwitch(SwitchPlatformInterface):

    """Represents a switch in a pinball machine used with virtual hardware."""

    def __init__(self, config, number):
        """Initialise switch."""
        super().__init__(config, number)
        self.log = logging.getLogger('VirtualSwitch')

    def get_board_name(self):
        """Return the name of the board of this switch."""
        return "Virtual"

    def __repr__(self):
        """Str representation."""
        return "VirtualSwitch.{}".format(self.number)


class VirtualLight(LightPlatformInterface):

    """Virtual Light."""

    def __init__(self, number, settings):
        """Initialise LED."""
        super().__init__(number)
        self.settings = settings
        self.color_and_fade_callback = None

    @property
    def current_brightness(self) -> float:
        """Return current brightness."""
        return self.get_current_brightness_for_fade()

    def get_current_brightness_for_fade(self, max_fade=0) -> float:
        """Return brightness for a max_fade long fade."""
        if self.color_and_fade_callback:
            return self.color_and_fade_callback(max_fade)[0]

        return 0

    def set_fade(self, color_and_fade_callback: Callable[[int], Tuple[float, int]]):
        """Store CB function."""
        self.color_and_fade_callback = color_and_fade_callback

    def get_board_name(self):
        """Return the name of the board of this light."""
        return "Virtual"


class VirtualServo(ServoPlatformInterface):

    """Virtual servo."""

    def __init__(self, number):
        """Initialise servo."""
        self.log = logging.getLogger('VirtualServo')
        self.number = number
        self.current_position = None
        self.speed = None
        self.acceleration = None

    def go_to_position(self, position):
        """Go to position."""
        self.current_position = position

    @classmethod
    def set_speed_limit(cls, speed_limit):
        """Todo emulate speed parameter."""
        pass

    @classmethod
    def set_acceleration_limit(cls, acceleration_limit):
        """Todo emulate acceleration parameter."""
        pass


class VirtualStepper(StepperPlatformInterface):

    """Virtual Stepper."""

    def __init__(self, number):
        """Initialise servo."""
        self.log = logging.getLogger('VirtualStepper')
        self.number = number
        self._current_position = 0
        self.velocity = 0
        self.direction = 0  # clockwise

    def home(self):
        """Home an axis, resetting 0 position."""
        self._current_position = 0

    def move_abs_pos(self, position):
        """Move axis to a certain absolute position."""
        self._current_position = position

    def move_rel_pos(self, position):
        """Move axis to a relative position."""
        self._current_position += position

    def move_vel_mode(self, velocity):
        """Move at a specific velocity indefinitely."""
        self.velocity = velocity

    def current_position(self):
        """Return current position of stepper."""
        return self._current_position

    def stop(self):
        """Stop motor."""
        self.velocity = 0


class VirtualDriver(DriverPlatformInterface):

    """A virtual driver object."""

    def __init__(self, config, number):
        """Initialise virtual driver to disabled."""
        self.log = logging.getLogger("VirtualDriver.{}".format(number))
        super().__init__(config, number)
        self.state = "disabled"

    def get_board_name(self):
        """Return the name of the board of this driver."""
        return "Virtual"

    def __repr__(self):
        """Str representation."""
        return "VirtualDriver.{}".format(self.number)

    def disable(self):
        """Disable virtual coil."""
        self.log.debug("Disabling driver")
        self.state = "disabled"

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable virtual coil."""
        del pulse_settings, hold_settings
        self.log.debug("Enabling driver")
        self.state = "enabled"

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse virtual coil."""
        self.log.debug("Pulsing driver for %sms", pulse_settings.duration)
        self.state = "pulsed_" + str(pulse_settings.duration)
