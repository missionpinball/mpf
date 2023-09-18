"""Contains code for a virtual hardware platform."""
from typing import Dict, Tuple, Optional, Union

import asyncio
import logging

from mpf.devices.segment_display.segment_display_text import ColoredSegmentDisplayText
from mpf.platforms.interfaces.hardware_sound_platform_interface import HardwareSoundPlatformInterface
from mpf.platforms.interfaces.i2c_platform_interface import I2cPlatformInterface
from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface, FlashingType

from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface

from mpf.core.platform import ServoPlatform, SwitchPlatform, DriverPlatform, AccelerometerPlatform, I2cPlatform, \
    DmdPlatform, RgbDmdPlatform, LightsPlatform, DriverConfig, SwitchConfig, SegmentDisplayPlatform, StepperPlatform, \
    HardwareSoundPlatform, SwitchSettings, DriverSettings, RepulseSettings
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings


# pylint: disable=too-many-ancestors,too-many-public-methods
class VirtualHardwarePlatform(AccelerometerPlatform, I2cPlatform, ServoPlatform, LightsPlatform, SwitchPlatform,
                              DriverPlatform, DmdPlatform, RgbDmdPlatform, SegmentDisplayPlatform, StepperPlatform,
                              HardwareSoundPlatform):

    """Base class for the virtual hardware platform."""

    __slots__ = ["hw_switches", "initial_states_sent", "_next_driver", "_next_switch", "_next_light", "__dict__",
                 "rules"]

    def __init__(self, machine) -> None:
        """initialize virtual platform."""
        super().__init__(machine)
        self._setup_log()

        # Since the virtual platform doesn't have real hardware, we need to
        # maintain an internal list of switches that were confirmed so we have
        # something to send when MPF needs to know the hardware states of
        # switches
        self.hw_switches = dict()   # type: Dict[str, bool]
        self.initial_states_sent = False
        self.features['tickless'] = True
        self.features['allow_empty_numbers'] = True
        self._next_driver = 1000
        self._next_switch = 1000
        self._next_light = 1000
        self.rules = {}     # type: Dict[Tuple[SwitchPlatformInterface, DriverPlatformInterface], str]

    def __repr__(self):
        """Return string representation."""
        return '<Platform.Virtual>'

    def _setup_log(self):
        self.log = logging.getLogger("Virtual Platform")
        self.log.debug("Configuring virtual hardware interface.")

    async def initialize(self) -> None:
        """initialize platform."""

    def stop(self):
        """Stop platform."""

    async def configure_servo(self, number: str, config: dict):
        """Configure a servo device in platform."""
        del config
        return VirtualServo(number)

    async def configure_stepper(self, number: str, config: dict):
        """Configure a smart stepper / axis device in platform."""
        del config
        return VirtualStepper(number, self.machine)

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
        """Configure driver."""
        del platform_settings
        # generate number if None
        if number is None:
            number = str(self._next_driver)
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

        return VirtualSwitch(config, number, self)

    async def get_hw_switch_states(self):
        """Return hw switch states."""
        if not self.initial_states_sent:

            if 'virtual_platform_start_active_switches' in self.machine.config:
                initial_active_switches = []
                for switch in Util.string_to_list(self.machine.config['virtual_platform_start_active_switches']):
                    if switch not in self.machine.switches:
                        if " " in switch:
                            self.raise_config_error("MPF no longer supports lists separated by space in "
                                                    "virtual_platform_start_active_switches. Please separate "
                                                    "switches by comma: {}.".format(switch), 1)
                        else:
                            self.raise_config_error("Switch {} used in virtual_platform_start_active_switches was not "
                                                    "found in switches section.".format(switch), 1)
                    initial_active_switches.append(self.machine.switches[switch].hw_switch.number)

                for k in self.hw_switches:
                    if k in initial_active_switches:
                        self.hw_switches[k] ^= 1

            self.initial_states_sent = True

        else:
            switches = [x for x in self.machine.switches.values() if x.platform == self]

            for switch in switches:
                self.hw_switches[switch.hw_switch.number] = switch.state ^ switch.invert

        return self.hw_switches

    def _get_platforms(self):
        platforms = []
        for name, platform in self.machine.config['mpf']['platforms'].items():
            if name in ("virtual", "smart_virtual"):
                continue
            platforms.append(Util.string_to_class(platform))
        return platforms

    def validate_stepper_section(self, stepper, config):
        """Validate stepper sections."""
        return config

    def validate_switch_section(self, switch, config):
        """Validate switch sections."""
        return config

    def validate_coil_section(self, driver, config):
        """Validate coil sections."""
        return config

    def validate_segment_display_section(self, segment_display, config):
        """Validate segment display sections."""
        del segment_display
        return config

    def configure_accelerometer(self, number, config, callback):
        """Configure accelerometer."""

    def configure_light(self, number, subtype, config, platform_settings):
        """Configure light channel."""
        del config
        if not subtype:
            subtype = "led"
        return VirtualLight("{}-{}".format(subtype, number), platform_settings, self.machine)

    # pylint: disable-msg=no-self-use
    def configure_hardware_sound_system(self, platform_settings) -> "HardwareSoundPlatformInterface":
        """Configure virtual hardware sound system."""
        del platform_settings
        return VirtualSound()

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse channel str to a list of channels."""
        if number is None:
            number = self._next_light
            self._next_light += 1
        if subtype in ("gi", "matrix", "simple", "incand"):
            return [
                {
                    "number": str(number)
                }
            ]
        if subtype == "led" or not subtype:
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

        raise AssertionError("Unknown subtype {}".format(subtype))

    def clear_hw_rule(self, switch, coil):
        """Clear hw rule."""
        if (switch.hw_switch, coil.hw_driver) in self.rules:
            del self.rules[(switch.hw_switch, coil.hw_driver)]
        else:
            self.log.debug("Tried to clear a non-existing rules %s <-> %s", switch, coil)

    def _assert_rule_does_not_exist(self, switch, driver):
        if (switch, driver) in self.rules:
            raise AssertionError("Overwrote a rule without clearing it first {} <-> {}".format(
                switch, driver))

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        """Set rule."""
        self._assert_rule_does_not_exist(enable_switch.hw_switch, coil.hw_driver)
        self.rules[(enable_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit_and_enable_and_release"

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set rule."""
        self._assert_rule_does_not_exist(enable_switch.hw_switch, coil.hw_driver)
        self.rules[(enable_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit_and_release"

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings, eos_switch: SwitchSettings,
                                                      coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Set rule."""
        self._assert_rule_does_not_exist(enable_switch.hw_switch, coil.hw_driver)
        self.rules[(enable_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit_and_release_and_disable"

        self._assert_rule_does_not_exist(eos_switch.hw_switch, coil.hw_driver)
        self.rules[(eos_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit_and_release_and_disable"

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings,
                                                                 coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Set rule."""
        self._assert_rule_does_not_exist(enable_switch.hw_switch, coil.hw_driver)
        self.rules[(enable_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit_and_enable_and_release_and_disable"

        self._assert_rule_does_not_exist(eos_switch.hw_switch, coil.hw_driver)
        self.rules[(eos_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit_and_enable_and_release_and_disable"

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        """Set rule."""
        self._assert_rule_does_not_exist(enable_switch.hw_switch, coil.hw_driver)
        self.rules[(enable_switch.hw_switch, coil.hw_driver)] = "pulse_on_hit"

    def configure_dmd(self):
        """Configure DMD."""
        return VirtualDmd()

    def configure_rgb_dmd(self, name: str):
        """Configure DMD."""
        del name
        return VirtualDmd()

    async def configure_segment_display(self, number: str, display_size: int,
                                        platform_settings) -> SegmentDisplayPlatformInterface:
        """Configure segment display."""
        del platform_settings
        del display_size
        return VirtualSegmentDisplay(number, self.machine)

    async def configure_i2c(self, number: str) -> "I2cPlatformInterface":
        """Configure virtual i2c device."""
        return VirtualI2cDevice(number, self._get_initial_i2c(number))

    @staticmethod
    def _get_initial_i2c(number):
        """Get virtual i2c layout.

        Mock this in your test.
        """
        del number
        return {}


class VirtualI2cDevice(I2cPlatformInterface):

    """Virtual i2c device."""

    __slots__ = ["data"]

    def __init__(self, number, initial_layout) -> None:
        """initialize virtual i2c device."""
        super().__init__(number)
        self.data = initial_layout

    def i2c_write8(self, register, value):
        """Write data."""
        self.data[int(register)] = value

    async def i2c_read_block(self, register, count):
        """Read data block."""
        result = []
        for i in range(int(register), int(register) + count):
            result.append(self.data[i])
        return result

    async def i2c_read8(self, register):
        """Read data."""
        return self.data[int(register)]


class VirtualSegmentDisplay(SegmentDisplayPlatformInterface):

    """Virtual segment display."""

    __slots__ = ["_text", "flashing", "flash_mask", "machine", "post_update_events"]

    def __init__(self, number, machine) -> None:
        """initialize virtual segment display."""
        super().__init__(number)
        self.machine = machine
        self._text = None
        self.flashing = FlashingType.NO_FLASH
        self.flash_mask = ""

    def set_text(self, text: ColoredSegmentDisplayText, flashing: FlashingType, flash_mask: str) -> None:
        """Set text."""
        self._text = text
        self.flashing = flashing
        self.flash_mask = flash_mask

    @property
    def text(self):
        """Return text."""
        return self._text.convert_to_str()

    @property
    def colors(self):
        """Return colors."""
        return self._text.get_colors()


class VirtualSound(HardwareSoundPlatformInterface):

    """Virtual hardware sound interface."""

    __slots__ = ["playing", "volume"]

    def __init__(self) -> None:
        """initialize virtual hardware sound."""
        self.playing = None     # type: Optional[Union[int, str]]
        self.volume = None      # type: Optional[float]

    def play_sound(self, number: int, track: int = 1):
        """Play virtual sound."""
        self.playing = number

    def play_sound_file(self, file: str, platform_options: dict, track: int = 1):
        """Play a sound file."""
        self.playing = file

    def text_to_speech(self, text: str, platform_options: dict, track: int = 1):
        """Text to speech output."""
        self.playing = text

    def set_volume(self, volume: float, track: int = 1):
        """Set volume."""
        self.volume = volume

    def stop_all_sounds(self, track: int = 1):
        """Stop sound."""
        self.playing = None


class VirtualDmd(DmdPlatformInterface):

    """Virtual DMD."""

    __slots__ = ["data", "brightness"]

    def __init__(self) -> None:
        """initialize virtual DMD."""
        self.data = None        # type: Optional[bytes]
        self.brightness = None  # type: Optional[float]

    def update(self, data: bytes):
        """Update data on the DMD.

        Args:
        ----
            data: bytes to send to DMD
        """
        self.data = data

    def set_brightness(self, brightness: float):
        """Set brightness."""
        self.brightness = brightness


class VirtualSwitch(SwitchPlatformInterface):

    """Represents a switch in a pinball machine used with virtual hardware."""

    __slots__ = ["log"]

    def __init__(self, config, number, platform) -> None:
        """initialize switch."""
        super().__init__(config, number, platform)
        self.log = logging.getLogger('VirtualSwitch')

    def get_board_name(self):
        """Return the name of the board of this switch."""
        return "Virtual"

    def __repr__(self):
        """Str representation."""
        return "VirtualSwitch.{}".format(self.number)


class VirtualLight(LightPlatformInterface):

    """Virtual Light."""

    __slots__ = ["settings", "_current_fade", "machine"]

    def __init__(self, number, settings, machine) -> None:
        """initialize LED."""
        super().__init__(number)
        self.settings = settings
        self.machine = machine
        self._current_fade = (0, -1, 0, -1)

    @property
    def current_brightness(self) -> float:
        """Return current brightness."""
        current_time = self.machine.clock.get_time()
        start_brightness, start_time, target_brightness, target_time = self._current_fade
        if target_time > current_time:
            ratio = ((current_time - start_time) /
                     (target_time - start_time))
            return start_brightness + (target_brightness - start_brightness) * ratio

        return target_brightness

    def set_fade(self, start_brightness, start_time, target_brightness, target_time):
        """Store CB function."""
        self._current_fade = (start_brightness, start_time, target_brightness, target_time)

    def get_board_name(self):
        """Return the name of the board of this light."""
        return "Virtual"

    def is_successor_of(self, other):
        """Return true if the other light has the same number string plus the suffix '+1'."""
        return self.number == other.number + "+1"

    def get_successor_number(self):
        """Return the number with the suffix '+1'.

        As there is not real number format for virtual is this is all we can do here.
        """
        return self.number + "+1"

    def __lt__(self, other):
        """Order lights by string."""
        return self.number < other.number


class VirtualServo(ServoPlatformInterface):

    """Virtual servo."""

    __slots__ = ["log", "number", "current_position", "speed_limit", "acceleration_limit"]

    def __init__(self, number) -> None:
        """initialize servo."""
        self.log = logging.getLogger('VirtualServo')
        self.number = number
        self.current_position = None
        self.speed_limit = None
        self.acceleration_limit = None

    def go_to_position(self, position):
        """Go to position."""
        self.current_position = position

    def set_speed_limit(self, speed_limit):
        """Set speed parameter."""
        self.speed_limit = speed_limit

    def set_acceleration_limit(self, acceleration_limit):
        """Set acceleration parameter."""
        self.acceleration_limit = acceleration_limit

    def stop(self):
        """Stop this servo."""
        self.current_position = "stop"


class VirtualStepper(StepperPlatformInterface):

    """Virtual Stepper."""

    __slots__ = ["log", "number", "_current_position", "velocity", "direction", "machine"]

    def __init__(self, number, machine) -> None:
        """initialize servo."""
        self.log = logging.getLogger('VirtualStepper')
        self.number = number
        self._current_position = 0
        self.velocity = 0
        self.direction = 0  # clockwise
        self.machine = machine

    def home(self, direction):
        """Home an axis, resetting 0 position."""
        self._current_position = 0

    async def wait_for_move_completed(self):
        """Wait until move completed."""
        await asyncio.sleep(0.1)

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

    __slots__ = ["state", "log", "__dict__"]

    def __init__(self, config, number) -> None:
        """initialize virtual driver to disabled."""
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

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and hold virtual coil for an explicit duration."""
        self.log.debug("Timed enabling driver: pulse for %sms, hold for %sms",
                       pulse_settings.duration, hold_settings.duration)
        self.state = "timed_enabled_" + str(pulse_settings.duration) + "_" + str(hold_settings.duration)
