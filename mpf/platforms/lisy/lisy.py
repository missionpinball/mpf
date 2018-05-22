"""LISY platform for System 1 and System 80."""
import asyncio
from typing import Generator, Dict

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.platforms.interfaces.hardware_sound_platform_interface import HardwareSoundPlatformInterface
from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplaySoftwareFlashPlatformInterface

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.core.logging import LogMixin

from mpf.platforms.lisy.defines import LisyDefines

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade

from mpf.core.platform import SwitchPlatform, LightsPlatform, DriverPlatform, SwitchSettings, DriverSettings, \
    DriverConfig, SwitchConfig, SegmentDisplaySoftwareFlashPlatform, HardwareSoundPlatform


class LisySwitch(SwitchPlatformInterface):

    """A switch in the LISY platform."""

    def get_board_name(self):
        """Return board name."""
        return "LISY"


class LisyDriver(DriverPlatformInterface):

    """A driver in the LISY platform."""

    def __init__(self, config, number, platform):
        """Initialise driver."""
        super().__init__(config, number)
        self.platform = platform
        self._pulse_ms = -1

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


class LisyLight(LightPlatformSoftwareFade):

    """A light in the LISY platform."""

    def __init__(self, number, platform):
        """Initialise Lisy Light."""
        super().__init__(number, platform.machine.clock.loop, 50)
        self.platform = platform

    def set_brightness(self, brightness: float):
        """Turn lamp on or off."""
        if brightness > 0:
            self.platform.send_byte(LisyDefines.LampsSetLampOn, bytes([self.number]))
        else:
            self.platform.send_byte(LisyDefines.LampsSetLampOff, bytes([self.number]))

    def get_board_name(self):
        """Return board name."""
        return "LISY"


class LisyDisplay(SegmentDisplaySoftwareFlashPlatformInterface):

    """A segment display in the LISY platform."""

    def __init__(self, number: int, platform: "LisyHardwarePlatform") -> None:
        """Initialise segment display."""
        super().__init__(number)
        self.platform = platform
        # clear display initially
        self.platform.send_string(LisyDefines.DisplaysSetDisplay0To + self.number, "")

    def _set_text(self, text: str):
        """Set text to display."""
        self.platform.send_string(LisyDefines.DisplaysSetDisplay0To + self.number, text)


class LisySound(HardwareSoundPlatformInterface):

    """Hardware sound interface for LISY."""

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
        self.platform.send_byte(LisyDefines.SoundSetVolume, bytes([int(volume * 100)]))

    def stop_all_sounds(self):
        """Stop all sounds."""
        self.platform.send_byte(LisyDefines.SoundStopAllSounds)


class LisyHardwarePlatform(SwitchPlatform, LightsPlatform, DriverPlatform,
                           SegmentDisplaySoftwareFlashPlatform,
                           HardwareSoundPlatform, LogMixin):

    """LISY platform."""

    def __init__(self, machine) -> None:
        """Initialise platform."""
        super().__init__(machine)
        self.config = None
        self._writer = None                 # type: asyncio.StreamWriter
        self._reader = None                 # type: asyncio.StreamReader
        self._poll_task = None
        self._watchdog_task = None
        self._number_of_lamps = None
        self._number_of_solenoids = None
        self._number_of_displays = None
        self._inputs = dict()               # type: Dict[str, bool]
        self._system_type = None
        self.features['max_pulse'] = 255

    @asyncio.coroutine
    def initialize(self):
        """Initialise platform."""
        self.config = self.machine.config_validator.validate_config("lisy", self.machine.config['lisy'])

        self.configure_logging("lisy", self.config['console_log'], self.config['file_log'])

        yield from super().initialize()

        if self.config['connection'] == "serial":
            self.log.info("Connecting to %s at %sbps", self.config['port'], self.config['baud'])
            connector = self.machine.clock.open_serial_connection(
                url=self.config['port'], baudrate=self.config['baud'], limit=0)
        else:
            self.log.info("Connecting to %s:%s", self.config['network_host'], self.config['network_port'])
            connector = self.machine.clock.open_connection(self.config['network_host'], self.config['network_port'])

        self._reader, self._writer = yield from connector

        # reset platform
        self.debug_log("Sending reset.")
        self.send_byte(LisyDefines.GeneralReset)
        return_code = yield from self.read_byte()
        if return_code != 0:
            raise AssertionError("Reset of LISY failed. Got {} instead of 0".format(return_code))

        # get type (system 1 vs system 80)
        self.send_byte(LisyDefines.InfoGetConnectedLisyHardware)
        type_str = yield from self.read_string()

        if type_str == b'LISY1':
            self._system_type = 1
        elif type_str == b'LISY80':
            self._system_type = 80
        else:
            raise AssertionError("Invalid LISY hardware version {}".format(type_str))

        self.send_byte(LisyDefines.InfoLisyVersion)
        lisy_version = yield from self.read_string()
        self.send_byte(LisyDefines.InfoGetApiVersion)
        api_version = yield from self.read_string()

        self.debug_log("Connected to %s hardware. LISY version: %s. API version: %s.",
                       type_str, lisy_version, api_version)

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
        self._number_of_lamps = yield from self.read_byte()

        # get number of solenoids
        self.send_byte(LisyDefines.InfoGetNumberOfSolenoids)
        self._number_of_solenoids = yield from self.read_byte()

        # get number of displays
        self.send_byte(LisyDefines.InfoGetNumberOfDisplays)
        self._number_of_displays = yield from self.read_byte()

        self.debug_log("Number of lamps: %s. Number of coils: %s. Numbers of display: %s",
                       self._number_of_lamps, self._number_of_solenoids, self._number_of_displays)

        # initially read all switches
        self.debug_log("Reading all switches.")
        for row in range(8):
            for col in range(8):
                number = row * 10 + col
                self.send_byte(LisyDefines.SwitchesGetStatusOfSwitch, bytes([number]))
                state = yield from self.read_byte()
                if state > 1:
                    raise AssertionError("Invalid switch {}. Got response: {}".format(number, state))

                self._inputs[str(number)] = state == 1

        self._watchdog_task = self.machine.clock.loop.create_task(self._watchdog())
        self._watchdog_task.add_done_callback(self._done)

        self.debug_log("Init of LISY done.")

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
        while True:
            self.send_byte(LisyDefines.SwitchesGetChangedSwitches)
            status = yield from self.read_byte()
            if status == 127:
                # no changes. sleep 1ms
                yield from asyncio.sleep(.001, loop=self.machine.clock.loop)
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
            self.send_byte(LisyDefines.GeneralWatchdog)
            # sleep 500ms
            yield from asyncio.sleep(.5, loop=self.machine.clock.loop)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """No rules on LISY."""
        raise AssertionError("Hardware rules are not support in LISY.")

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 disable_switch: SwitchSettings, coil: DriverSettings):
        """No rules on LISY."""
        raise AssertionError("Hardware rules are not support in LISY.")

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """No rules on LISY."""
        raise AssertionError("Hardware rules are not support in LISY.")

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """No rules on LISY."""
        raise AssertionError("Hardware rules are not support in LISY.")

    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """No rules on LISY."""
        raise AssertionError("Hardware rules are not support in LISY.")

    def configure_light(self, number: str, subtype: str, platform_settings: dict) -> LightPlatformSoftwareFade:
        """Configure light on LISY."""
        del platform_settings, subtype

        if self._system_type == 80:
            if 0 < int(number) >= self._number_of_lamps:
                raise AssertionError("LISY only has {} lamps. Cannot configure lamp {} (zero indexed).".
                                     format(self._number_of_lamps, number))
        else:
            if 1 < int(number) > self._number_of_lamps:
                raise AssertionError("LISY only has {} lamps. Cannot configure lamp {} (one indexed).".
                                     format(self._number_of_lamps, number))

        return LisyLight(int(number), self)

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Return a single light."""
        return [
            {
                "number": number,
            }
        ]

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> SwitchPlatformInterface:
        """Configure a switch."""
        if (int(number) % 10) > 7 or 0 < int(number) > 77:
            raise AssertionError("Invalid switch number {}".format(number))

        return LisySwitch(config=config, number=number)

    @asyncio.coroutine
    def get_hw_switch_states(self):
        """Return current switch states."""
        return self._inputs

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> DriverPlatformInterface:
        """Configure a driver."""
        if 1 < int(number) > self._number_of_solenoids and int(number) < 100:
            raise AssertionError("LISY only has {} drivers. Cannot configure driver {} (zero indexed).".
                                 format(self._number_of_solenoids, number))
        elif self._system_type == 80:
            if 100 < int(number) >= self._number_of_lamps + 100:
                raise AssertionError("LISY only has {} lamps. Cannot configure lamp driver {} (zero indexed).".
                                     format(self._number_of_lamps, number))
        else:
            if 101 < int(number) > self._number_of_lamps + 100:
                raise AssertionError("LISY only has {} lamps. Cannot configure lamp driver {} (one indexed).".
                                     format(self._number_of_lamps, number))

        return LisyDriver(config=config, number=number, platform=self)

    def configure_segment_display(self, number: str) -> SegmentDisplaySoftwareFlashPlatformInterface:
        """Configure a segment display."""
        if 0 < int(number) >= self._number_of_displays:
            raise AssertionError("Invalid display number {}. Hardware only supports {} displays (indexed with 0)".
                                 format(number, self._number_of_displays))

        display = LisyDisplay(int(number), self)
        self._handle_software_flash(display)
        return display

    def configure_hardware_sound_system(self) -> HardwareSoundPlatformInterface:
        """Configure hardware sound."""
        return LisySound(self)

    def send_byte(self, cmd: int, byte: bytes = None):
        """Send a command with optional payload."""
        if byte is not None:
            cmd_str = bytes([cmd])
            cmd_str += byte
            self.log.debug("Sending %s %s", cmd, byte)
            self._writer.write(cmd_str)
        else:
            self.log.debug("Sending %s", cmd)
            self._writer.write(bytes([cmd]))

    def send_string(self, cmd: int, string: str):
        """Send a command with null terminated string."""
        self.log.debug("Sending %s %s", cmd, string)
        self._writer.write(bytes([cmd]) + string.encode() + bytes([0]))

    @asyncio.coroutine
    def read_byte(self) -> Generator[int, None, int]:
        """Read one byte."""
        self.log.debug("Reading one byte")
        data = yield from self._reader.readexactly(1)
        self.log.debug("Received %s", ord(data))
        return ord(data)

    @asyncio.coroutine
    # pylint: disable-msg=inconsistent-return-statements
    def readuntil(self, separator, min_chars: int = 0):
        """Read until separator.

        Args:
            separator: Read until this separator byte.
            min_chars: Minimum message length before separator
        """
        # asyncio StreamReader only supports this from python 3.5.2 on
        buffer = b''
        while True:
            char = yield from self._reader.readexactly(1)
            buffer += char
            if char == separator and len(buffer) > min_chars:
                return buffer

    @asyncio.coroutine
    def read_string(self) -> Generator[int, None, bytes]:
        """Read zero terminated string."""
        self.log.debug("Reading zero terminated string")
        data = yield from self.readuntil(b'\x00')
        # remove terminator
        data = data[:-1]
        self.log.debug("Received %s", data)
        return data
