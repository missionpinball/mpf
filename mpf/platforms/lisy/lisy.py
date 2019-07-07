"""LISY platform for System 1 and System 80."""
import asyncio
from distutils.version import StrictVersion

from typing import Generator, Dict, Optional, List

from mpf.core.segment_mappings import seven_segments, bcd_segments, fourteen_segments, TextToSegmentMapper, \
    ascii_segments
from mpf.core.platform_batch_light_system import PlatformBatchLight, PlatformBatchLightSystem
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.platforms.interfaces.hardware_sound_platform_interface import HardwareSoundPlatformInterface
from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplaySoftwareFlashPlatformInterface

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.core.logging import LogMixin

from mpf.platforms.lisy.defines import LisyDefines

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade, LightPlatformInterface

from mpf.core.platform import SwitchPlatform, LightsPlatform, DriverPlatform, SwitchSettings, DriverSettings, \
    DriverConfig, SwitchConfig, SegmentDisplaySoftwareFlashPlatform, HardwareSoundPlatform


class LisySwitch(SwitchPlatformInterface):

    """A switch in the LISY platform."""

    __slots__ = ["index"]  # type: List[str]

    def __init__(self, config, number):
        """Initialise switch."""
        super().__init__(config, number)
        self.index = int(number)

    def get_board_name(self):
        """Return board name."""
        return "LISY"


class LisyDriver(DriverPlatformInterface):

    """A driver in the LISY platform."""

    __slots__ = ["platform", "_pulse_ms", "index", "has_rule"]   # type: List[str]

    def __init__(self, config, number, platform):
        """Initialise driver."""
        super().__init__(config, number)
        self.platform = platform
        self._pulse_ms = -1
        self.index = int(number)
        self.has_rule = False

    def _configure_pulse_ms(self, pulse_ms):
        """Configure pulse ms for this driver if it changed."""
        if pulse_ms != self._pulse_ms:
            self._pulse_ms = pulse_ms
            self.platform.send_byte(LisyDefines.SolenoidsSetSolenoidPulseTime, bytes(
                [int(self.number),
                 pulse_ms if pulse_ms < 255 else 255
                 ]))

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse driver."""
        self._configure_pulse_ms(pulse_settings.duration)
        self.platform.send_byte(LisyDefines.SolenoidsPulseSolenioid, bytes([int(self.number)]))

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable driver."""
        del hold_settings
        self._configure_pulse_ms(pulse_settings.duration)
        self.platform.send_byte(LisyDefines.SolenoidsSetSolenoidToOn, bytes([int(self.number)]))

    def disable(self):
        """Disable driver."""
        self.platform.send_byte(LisyDefines.SolenoidsSetSolenoidToOff, bytes([int(self.number)]))

    def get_board_name(self):
        """Return board name."""
        return "LISY"


class LisySimpleLamp(LightPlatformSoftwareFade):

    """A simple light in the LISY platform which only supports on/off."""

    __slots__ = ["platform", "_state"]

    def __init__(self, number, platform):
        """Initialise Lisy Light."""
        super().__init__(number, platform.machine.clock.loop, 50)
        self.platform = platform
        self._state = None

    def set_brightness(self, brightness: float):
        """Turn lamp on or off."""
        if brightness > 0 and self._state is not True:
            self.platform.send_byte(LisyDefines.LampsSetLampOn, bytes([self.number]))
            self._state = True
        elif brightness <= 0 and self._state is not False:
            self.platform.send_byte(LisyDefines.LampsSetLampOff, bytes([self.number]))
            self._state = False

    def get_board_name(self):
        """Return board name."""
        return "LISY"


class LisyModernLight(PlatformBatchLight):

    """A modern light in LISY."""

    __slots__ = ["platform"]

    def __init__(self, number, platform, light_system):
        """Initialise Lisy Light."""
        super().__init__(number, light_system)
        self.platform = platform

    def get_max_fade_ms(self) -> int:
        """Return max fade time."""
        return 65535

    def get_board_name(self):
        """Return board name."""
        return "LISY"


class LisyDisplay(SegmentDisplaySoftwareFlashPlatformInterface):

    """A segment display in the LISY platform."""

    __slots__ = ["platform", "_type_of_display", "_length_of_display"]

    def __init__(self, number: int, platform: "LisyHardwarePlatform") -> None:
        """Initialise segment display."""
        super().__init__(number)
        self.platform = platform
        self._type_of_display = None
        self._length_of_display = None

    @asyncio.coroutine
    def initialize(self):
        """Initialize segment display."""
        if self.platform.api_version >= StrictVersion("0.9"):
            # display info for display
            display_info = yield from (self.platform.send_byte_and_read_response(
                LisyDefines.InfoGetDisplayDetails, bytearray([self.number]), 2))
            if 0 > display_info[1] > 6:
                raise AssertionError("Invalid display type {} in hardware".format(self._type_of_display))

            self._length_of_display = int(display_info[0])
            self._type_of_display = display_info[1]

        # clear display initially
        self._set_text("")

    def _format_text(self, text):
        if self._type_of_display == 1:
            mapping = TextToSegmentMapper.map_text_to_segments(text, self._length_of_display, bcd_segments,
                                                               embed_dots=False)
            result = map(lambda x: x.get_x4x3x2x1_encoding(), mapping)
        elif self._type_of_display == 2:
            mapping = TextToSegmentMapper.map_text_to_segments(text, self._length_of_display, bcd_segments)
            result = map(lambda x: x.get_dpx4x3x2x1_encoding(), mapping)
        elif self._type_of_display == 3:
            mapping = TextToSegmentMapper.map_text_to_segments(text, self._length_of_display, seven_segments)
            result = map(lambda x: x.get_dpgfedcba_encoding(), mapping)
        elif self._type_of_display == 4:
            mapping = TextToSegmentMapper.map_text_to_segments(text, self._length_of_display, fourteen_segments)
            result = map(lambda x: x.get_pinmame_encoding(), mapping)
        elif self._type_of_display == 5:
            mapping = TextToSegmentMapper.map_text_to_segments(text, self._length_of_display, ascii_segments,
                                                               embed_dots=False)
            result = map(lambda x: x.get_ascii_encoding(), mapping)
        elif self._type_of_display == 6:
            mapping = TextToSegmentMapper.map_text_to_segments(text, self._length_of_display, ascii_segments)
            result = map(lambda x: x.get_ascii_with_dp_encoding(), mapping)
        else:
            raise AssertionError("Invalid type {}".format(self._type_of_display))

        return b''.join(result)

    def _set_text(self, text: str):
        """Set text to display."""
        if self.platform.api_version >= StrictVersion("0.9"):
            formatted_text = self._format_text(text)
            self.platform.send_byte(LisyDefines.DisplaysSetDisplay0To + self.number, formatted_text)
        else:
            self.platform.send_string(LisyDefines.DisplaysSetDisplay0To + self.number, text)


class LisySound(HardwareSoundPlatformInterface):

    """Hardware sound interface for LISY."""

    __slots__ = ["platform"]

    def __init__(self, platform):
        """Initialise hardware sound."""
        self.platform = platform        # type: LisyHardwarePlatform

    def play_sound(self, number: int):
        """Play sound with number."""
        self.platform.send_byte(LisyDefines.SoundPlaySound, bytes([number]))

    def play_sound_file(self, file: str, platform_options: dict):
        """Play sound file."""
        flags = 1 if platform_options.get("loop", False) else 0
        flags += 2 if platform_options.get("no_cache", False) else 0
        self.platform.send_string(LisyDefines.SoundPlaySoundFile, chr(flags) + file)

    def text_to_speech(self, text: str, platform_options: dict):
        """Text to speech."""
        flags = 1 if platform_options.get("loop", False) else 0
        flags += 2 if platform_options.get("no_cache", False) else 0
        self.platform.send_string(LisyDefines.SoundTextToSpeech, chr(flags) + text)

    def set_volume(self, volume: float):
        """Set volume."""
        if self.platform.api_version >= StrictVersion("0.9"):
            self.platform.send_byte(LisyDefines.SoundSetVolume, bytes([1, int(volume * 100)]))
        else:
            self.platform.send_byte(LisyDefines.SoundSetVolume, bytes([int(volume * 100)]))

    def stop_all_sounds(self):
        """Stop all sounds."""
        self.platform.send_byte(LisyDefines.SoundStopAllSounds)


# pylint: disable-msg=too-many-instance-attributes
class LisyHardwarePlatform(SwitchPlatform, LightsPlatform, DriverPlatform,
                           SegmentDisplaySoftwareFlashPlatform,
                           HardwareSoundPlatform, LogMixin):

    """LISY platform."""

    __slots__ = ["config", "_writer", "_reader", "_poll_task", "_watchdog_task", "_number_of_lamps",
                 "_number_of_solenoids", "_number_of_displays", "_inputs", "_coils_start_at_one",
                 "_bus_lock", "api_version", "_number_of_switches", "_number_of_modern_lights",
                 "_light_system"]  # type: List[str]

    def __init__(self, machine) -> None:
        """Initialise platform."""
        super().__init__(machine)
        self._writer = None                 # type: Optional[asyncio.StreamWriter]
        self._reader = None                 # type: Optional[asyncio.StreamReader]
        self._poll_task = None
        self._watchdog_task = None
        self._bus_lock = asyncio.Lock(loop=self.machine.clock.loop)
        self._number_of_lamps = None        # type: Optional[int]
        self._number_of_solenoids = None    # type: Optional[int]
        self._number_of_displays = None     # type: Optional[int]
        self._number_of_switches = None     # type: Optional[int]
        self._number_of_modern_lights = None    # type: Optional[int]
        self._inputs = dict()               # type: Dict[str, bool]
        self._coils_start_at_one = None     # type: Optional[str]
        self.features['max_pulse'] = 255

        self.config = self.machine.config_validator.validate_config("lisy", self.machine.config['lisy'])
        self._configure_device_logging_and_debug("lisy", self.config)
        self.api_version = None
        self._light_system = None

    def _disable_dts_on_start_of_serial(self):
        """Prevent DTS toggling when opening the serial.

        This works only on unix. On other platforms import of termios will fail.
        """
        try:
            import termios
        except ImportError:
            self.warning_log("Could not import terminos (this is ok on windows).")
            return
        serial_port = open(self.config['port'])
        attrs = termios.tcgetattr(serial_port)
        attrs[2] = attrs[2] & ~termios.HUPCL
        termios.tcsetattr(serial_port, termios.TCSAFLUSH, attrs)
        serial_port.close()

    @asyncio.coroutine
    def _clear_read_buffer(self):
        """Clear read buffer."""
        if hasattr(self._writer.transport, "_serial"):
            # pylint: disable-msg=protected-access
            self._writer.transport._serial.reset_input_buffer()
        # pylint: disable-msg=protected-access
        self._reader._buffer = bytearray()
        # pylint: disable-msg=protected-access
        self._reader._maybe_resume_transport()

    # pylint: disable-msg=too-many-statements
    # pylint: disable-msg=too-many-branches
    @asyncio.coroutine
    def initialize(self):
        """Initialise platform."""
        with (yield from self._bus_lock):

            yield from super().initialize()

            if self.config['connection'] == "serial":
                self.log.info("Connecting to %s at %sbps", self.config['port'], self.config['baud'])
                if self.config['disable_dtr']:
                    self._disable_dts_on_start_of_serial()
                connector = self.machine.clock.open_serial_connection(
                    url=self.config['port'], baudrate=self.config['baud'], limit=0, do_not_open=True)
            else:
                self.log.info("Connecting to %s:%s", self.config['network_host'], self.config['network_port'])
                connector = self.machine.clock.open_connection(self.config['network_host'], self.config['network_port'])

            self._reader, self._writer = yield from connector

            if self.config['connection'] == "serial":
                if self.config['disable_dtr']:
                    # pylint: disable-msg=protected-access
                    self._writer.transport._serial.dtr = False
                    # pylint: disable-msg=protected-access
                self._writer.transport._serial.open()

            # give the serial a few ms to read the first bytes
            yield from asyncio.sleep(.1, loop=self.machine.clock.loop)

            while True:
                # reset platform
                self.debug_log("Sending reset.")
                yield from self._clear_read_buffer()
                # send command
                self.send_byte(LisyDefines.GeneralReset)
                try:
                    return_code = yield from asyncio.wait_for(self._read_byte(), timeout=0.5,
                                                              loop=self.machine.clock.loop)
                except asyncio.TimeoutError:
                    self.warning_log("Reset of LISY failed. Did not get a response in 500ms. Will retry.")
                    continue
                if return_code != 0:
                    # reset failed
                    self.warning_log("Reset of LISY failed. Got %s instead of 0. Will retry.", return_code)
                    continue

                # if we made it here reset succeeded
                break

            # get type (system 1 vs system 80)
            self.send_byte(LisyDefines.InfoGetConnectedLisyHardware)
            type_str = yield from self._read_string()

            if type_str in (b'LISY1', b'LISY35', b'APC'):
                self._coils_start_at_one = True
            elif type_str == b'LISY80':
                self._coils_start_at_one = False
            else:
                raise AssertionError("Invalid LISY hardware version {}".format(type_str))

            self.send_byte(LisyDefines.InfoLisyVersion)
            lisy_version = yield from self._read_string()
            self.send_byte(LisyDefines.InfoGetApiVersion)
            api_version = yield from self._read_string()

            self.debug_log("Connected to %s hardware. LISY version: %s. API version: %s.",
                           type_str, lisy_version, api_version)

            self.api_version = StrictVersion(api_version.decode())

            self.machine.set_machine_var("lisy_hardware", type_str)
            '''machine_var: lisy_hardware

            desc: Connected LISY hardware. Either LISY1 or LISY80.
            '''
            self.machine.set_machine_var("lisy_version", lisy_version)
            '''machine_var: lisy_version

            desc: LISY version.
            '''
            self.machine.set_machine_var("lisy_api_version", api_version)
            '''machine_var: lisy_api_version

            desc: LISY API version.
            '''

            # get number of lamps
            self.send_byte(LisyDefines.InfoGetNumberOfLamps)
            self._number_of_lamps = yield from self._read_byte()

            # get number of solenoids
            self.send_byte(LisyDefines.InfoGetNumberOfSolenoids)
            self._number_of_solenoids = yield from self._read_byte()

            # get number of displays
            self.send_byte(LisyDefines.InfoGetNumberOfDisplays)
            self._number_of_displays = yield from self._read_byte()

            # get number of switches
            self.send_byte(LisyDefines.InfoGetSwitchCount)
            self._number_of_switches = yield from self._read_byte()

            if self.api_version >= StrictVersion("0.9"):
                # get number of modern lights
                self.send_byte(LisyDefines.GetModernLightsCount)
                self._number_of_modern_lights = yield from self._read_byte()
            else:
                self._number_of_modern_lights = 0

            if self._number_of_modern_lights > 0:
                self._light_system = PlatformBatchLightSystem(self.machine.clock, lambda x: x.number,
                                                              lambda x, y: x.number + 1 == y.number,
                                                              self._send_multiple_light_update,
                                                              self.machine.machine_config['mpf'][
                                                                  'default_light_hw_update_hz'],
                                                              self.config['max_led_batch_size'])
                self._light_system.start()

            self.debug_log("Number of lamps: %s. Number of coils: %s. Numbers of display: %s. Number of switches: %s",
                           self._number_of_lamps, self._number_of_solenoids, self._number_of_displays,
                           self._number_of_switches)

            # initially read all switches
            self.debug_log("Reading all switches.")
            for number in range(self._number_of_switches):
                self.send_byte(LisyDefines.SwitchesGetStatusOfSwitch, bytes([number]))
                state = yield from self._read_byte()
                if state == 2:
                    self.warning_log("Switch %s does not exist in platform.", number)
                elif state > 2:
                    raise AssertionError("Invalid switch {}. Got response: {}".format(number, state))

                self._inputs[str(number)] = state == 1

            self._watchdog_task = self.machine.clock.loop.create_task(self._watchdog())
            self._watchdog_task.add_done_callback(self._done)

            self.debug_log("Init of LISY done.")

    @asyncio.coroutine
    def _send_multiple_light_update(self, sequential_brightness_list):
        common_fade_ms = sequential_brightness_list[0][2]
        if common_fade_ms < 0:
            common_fade_ms = 0
        fade_time = int(common_fade_ms)

        data = bytearray([sequential_brightness_list[0][0].number, int(fade_time / 255), int(fade_time & 0xFF),
                          len(sequential_brightness_list)])
        for _, brightness, _ in sequential_brightness_list:
            data.append(int(255 * brightness))

        self.send_byte(LisyDefines.FadeModernLights, data)

    @asyncio.coroutine
    def start(self):
        """Start reading switch changes."""
        self._poll_task = self.machine.clock.loop.create_task(self._poll())
        self._poll_task.add_done_callback(self._done)

    def stop(self):
        """Stop platform."""
        super().stop()
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None

        if self._watchdog_task:
            self._watchdog_task.cancel()
            self._watchdog_task = None

        if self._reader:
            self._writer.close()
            self._reader = None
            self._writer = None

    @staticmethod
    def _done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    @asyncio.coroutine
    def _poll(self):
        sleep_time = 1.0 / self.config['poll_hz']
        while True:
            with (yield from self._bus_lock):
                self.send_byte(LisyDefines.SwitchesGetChangedSwitches)
                status = yield from self._read_byte()
            if status == 127:
                # no changes. sleep according to poll_hz
                yield from asyncio.sleep(sleep_time, loop=self.machine.clock.loop)
            else:
                # bit 7 is state
                switch_state = 1 if status & 0b10000000 else 0
                # bits 0-6 are the switch number
                switch_num = status & 0b01111111

                # tell the switch controller about the new state
                self.machine.switch_controller.process_switch_by_num(str(switch_num), switch_state, self)

                # store in dict as well
                self._inputs[str(switch_num)] = bool(switch_state)

    @asyncio.coroutine
    def _watchdog(self):
        """Periodically send watchdog."""
        while True:
            # send watchdog
            with (yield from self._bus_lock):
                self.send_byte(LisyDefines.GeneralWatchdog)
                response = yield from self._read_byte()
                if response != 0:
                    self.warning_log("Watchdog returned %s instead 0", response)
            # sleep 500ms
            yield from asyncio.sleep(.5, loop=self.machine.clock.loop)

    # pylint: disable-msg=too-many-arguments
    def _configure_hardware_rule(self, coil: DriverSettings, switch1: SwitchSettings,
                                 switch2: Optional[SwitchSettings], flags1, flags2):
        """Configure hardware rule in LISY."""
        if coil.pulse_settings.duration > 255:
            raise AssertionError("Pulse settings to long for LISY protocol. Got pulse_settings: {}".format(
                coil.pulse_settings))

        coil.hw_driver.has_rule = True

        data = bytearray([coil.hw_driver.index,
                          switch1.hw_switch.index + (0x80 if switch1.invert else 0),
                          switch2.hw_switch.index if switch2 else 0 + 0x80 if switch2 and switch2.invert else 0,
                          0,
                          int(coil.pulse_settings.duration),
                          int(coil.pulse_settings.power * 255),
                          int(coil.hold_settings.power * 255) if coil.hold_settings else 0,
                          flags1,
                          flags2,
                          0
                          ])
        self.send_byte(LisyDefines.ConfigureHardwareRuleForSolenoid, data)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and release rule on driver."""
        assert coil.hold_settings.power > 0
        self._configure_hardware_rule(coil, enable_switch, None, 3, 0)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 disable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and release and disable rule on driver."""
        self._configure_hardware_rule(coil, enable_switch, disable_switch, 3, 2)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and release rule to driver."""
        assert not coil.hold_settings or coil.hold_settings.power == 0
        self._configure_hardware_rule(coil, enable_switch, None, 3, 0)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit rule on driver."""
        assert not coil.hold_settings or coil.hold_settings.power == 0
        self._configure_hardware_rule(coil, enable_switch, None, 1, 0)

    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """Clear hw rule for driver."""
        del switch
        if not coil.hw_driver.has_rule:
            return
        coil.hw_driver.has_rule = False

        data = bytearray([coil.hw_driver.index,
                          0,
                          0,
                          0,
                          0,
                          0,
                          0,
                          0,
                          0,
                          0
                          ])
        self.send_byte(LisyDefines.ConfigureHardwareRuleForSolenoid, data)

    def configure_light(self, number: str, subtype: str, platform_settings: dict) -> LightPlatformInterface:
        """Configure light on LISY."""
        del platform_settings
        assert self._number_of_lamps is not None

        if subtype is None or subtype == "matrix":
            if not self._coils_start_at_one:
                if 0 < int(number) >= self._number_of_lamps:
                    raise AssertionError("LISY only has {} lamps. Cannot configure lamp {} (zero indexed).".
                                         format(self._number_of_lamps, number))
            else:
                if 1 < int(number) > self._number_of_lamps:
                    raise AssertionError("LISY only has {} lamps. Cannot configure lamp {} (one indexed).".
                                         format(self._number_of_lamps, number))

            return LisySimpleLamp(int(number), self)
        elif subtype == "light":
            if 0 < int(number) >= self._number_of_modern_lights:
                raise AssertionError("LISY only has {} modern lights. Cannot configure light {}.".
                                     format(self._number_of_modern_lights, number))
            return LisyModernLight(int(number), self, self._light_system)
        else:
            raise self.raise_config_error("Invalid subtype {}".format(subtype), 1)

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Return a single light."""
        return [
            {
                "number": number,
            }
        ]

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> SwitchPlatformInterface:
        """Configure a switch."""
        if number not in self._inputs:
            raise AssertionError("Invalid switch number {}. Platform reports the following switches as "
                                 "valid: {}".format(number, list(self._inputs.keys())))

        return LisySwitch(config=config, number=number)

    @asyncio.coroutine
    def get_hw_switch_states(self):
        """Return current switch states."""
        return self._inputs

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> DriverPlatformInterface:
        """Configure a driver."""
        assert self._number_of_solenoids is not None
        assert self._number_of_lamps is not None

        if 1 < int(number) > self._number_of_solenoids and int(number) < 100:
            raise AssertionError("LISY only has {} drivers. Cannot configure driver {} (zero indexed).".
                                 format(self._number_of_solenoids, number))
        elif not self._coils_start_at_one:
            if 100 < int(number) >= self._number_of_lamps + 100:
                raise AssertionError("LISY only has {} lamps. Cannot configure lamp driver {} (zero indexed).".
                                     format(self._number_of_lamps, number))
        else:
            if 101 < int(number) > self._number_of_lamps + 100:
                raise AssertionError("LISY only has {} lamps. Cannot configure lamp driver {} (one indexed).".
                                     format(self._number_of_lamps, number))

        return LisyDriver(config=config, number=number, platform=self)

    @asyncio.coroutine
    def configure_segment_display(self, number: str, platform_settings) -> SegmentDisplaySoftwareFlashPlatformInterface:
        """Configure a segment display."""
        del platform_settings
        assert self._number_of_displays is not None

        if 0 < int(number) >= self._number_of_displays:
            raise AssertionError("Invalid display number {}. Hardware only supports {} displays (indexed with 0)".
                                 format(number, self._number_of_displays))

        display = LisyDisplay(int(number), self)
        yield from display.initialize()
        self._handle_software_flash(display)
        return display

    def configure_hardware_sound_system(self) -> HardwareSoundPlatformInterface:
        """Configure hardware sound."""
        return LisySound(self)

    def send_byte(self, cmd: int, byte: bytes = None):
        """Send a command with optional payload."""
        assert self._writer is not None

        if byte is not None:
            cmd_str = bytes([cmd])
            cmd_str += byte
            self.log.debug("Sending %s %s", cmd, byte)
            self._writer.write(cmd_str)
        else:
            self.log.debug("Sending %s", cmd)
            self._writer.write(bytes([cmd]))

    @asyncio.coroutine
    def send_byte_and_read_response(self, cmd: int, byte: bytes = None, read_bytes=0):
        """Send byte and read response."""
        with (yield from self._bus_lock):
            self.send_byte(cmd, byte)
            return (yield from self._reader.readexactly(read_bytes))

    def send_string(self, cmd: int, string: str):
        """Send a command with null terminated string."""
        assert self._writer is not None

        self.log.debug("Sending %s %s", cmd, string)
        self._writer.write(bytes([cmd]) + string.encode() + bytes([0]))

    @asyncio.coroutine
    def _read_byte(self) -> Generator[int, None, int]:
        """Read one byte."""
        assert self._reader is not None

        self.log.debug("Reading one byte")
        data = yield from self._reader.readexactly(1)
        self.log.debug("Received %s", ord(data))
        return ord(data)

    @asyncio.coroutine
    # pylint: disable-msg=inconsistent-return-statements
    def _readuntil(self, separator, min_chars: int = 0):
        """Read until separator.

        Args:
            separator: Read until this separator byte.
            min_chars: Minimum message length before separator
        """
        assert self._reader is not None

        # asyncio StreamReader only supports this from python 3.5.2 on
        buffer = b''
        while True:
            char = yield from self._reader.readexactly(1)
            buffer += char
            if char == separator and len(buffer) > min_chars:
                return buffer

    @asyncio.coroutine
    def _read_string(self) -> Generator[int, None, bytes]:
        """Read zero terminated string."""
        self.log.debug("Reading zero terminated string")
        data = yield from self._readuntil(b'\x00')
        # remove terminator
        data = data[:-1]
        self.log.debug("Received %s", data)
        return data
