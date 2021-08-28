"""Pinotaur platform."""
import asyncio
from typing import Dict, Optional, List

from mpf.core.platform_batch_light_system import PlatformBatchLight, PlatformBatchLightSystem
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface
from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.core.logging import LogMixin
from mpf.core.utility_functions import Util

from mpf.platforms.pinotaur.defines import PinotaurDefines

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade, LightPlatformInterface

from mpf.core.platform import SwitchPlatform, LightsPlatform, DriverPlatform, SwitchSettings, DriverSettings, \
    DriverConfig, SwitchConfig, RepulseSettings, ServoPlatform, StepperPlatform


class PinotaurSwitch(SwitchPlatformInterface):

    """A switch in the Pinotaur platform."""

    __slots__ = ["index"]  # type: List[str]

    def __init__(self, config, number):
        """Initialise switch."""
        super().__init__(config, number)
        self.index = int(number)

    def get_board_name(self):
        """Return board name."""
        return "Pinotaur"


class PinotaurDriver(DriverPlatformInterface):

    """A driver in the Pinotaur platform."""

    __slots__ = ["platform", "_pulse_ms", "_recycle_time", "index", "has_rule", "_pulse_power",
                 "_hold_settings"]     # type: List[str]

    def __init__(self, config, number, platform):
        """Initialise driver."""
        super().__init__(config, number)
        self.platform = platform        # type: PinotaurHardwarePlatform
        self._pulse_ms = -1
        self._pulse_power = -1
        self._recycle_time = None
        self.index = int(number)
        self.has_rule = False
        self._hold_settings = None

    def configure_recycle(self, recycle_time):
        """Configure recycle time."""
        if recycle_time > 255:
            recycle_time = 255
        elif recycle_time < 0:
            recycle_time = 0

        if self._recycle_time != recycle_time:
            self._recycle_time = recycle_time
            self.platform.send_command_background(PinotaurDefines.SetSolenoidRecycle,
                                                  bytes([self.index, recycle_time]))

    def _configure_pulse_ms(self, pulse_ms):
        """Configure pulse ms for this driver if it changed."""
        # pulse_ms 0 is ok here (but not in the pulse command)
        assert 0 <= pulse_ms <= 255
        if pulse_ms != self._pulse_ms:
            self._pulse_ms = pulse_ms
            self.platform.send_command_background(PinotaurDefines.SetSolenoidPulseTime, bytes(
                [self.index,
                 pulse_ms
                 ]))

    def _configure_pulse_power(self, pulse_power):
        """Configure pulse power for this driver if it changed."""
        if pulse_power != self._pulse_power:
            self._pulse_power = pulse_power
            on, off = Util.power_to_on_off(pulse_power, 20)
            self.platform.send_command_background(PinotaurDefines.SetSolenoidPulsePWM, bytes(
                [self.index,
                 int(on),
                 int(on + off)
                 ]))

    def _configure_hold_power(self, hold_settings: Optional[HoldSettings]):
        """Configure pulse power for this driver if it changed."""
        if hold_settings == self._hold_settings:
            return
        if hold_settings:
            self.platform.send_command_background(PinotaurDefines.SetHoldTime, bytes([self.index, 255, 255]))
            self._hold_settings = hold_settings
            on, off = Util.power_to_on_off(hold_settings.power, 20)
            self.platform.send_command_background(PinotaurDefines.SetSolenoidHoldPWM, bytes(
                [self.index,
                 int(on),
                 int(on + off),
                 0,     # not implemented in firmware
                 0,     # not implemented in firmware
                 0,     # not implemented in firmware
                 0,     # not implemented in firmware
                 ]))
        else:
            self.platform.send_command_background(PinotaurDefines.SetHoldTime, bytes([self.index, 0, 0]))

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse driver."""
        if self.has_rule:
            # TODO: check if this is actually possible with rule -> do we need a timer?
            raise AssertionError("It is currently not possible to pulse this coil while a rule is active.")

        # pulse_ms 0 has special meaning in Pinotaur firmware
        assert 0 < pulse_settings.duration <= 255
        self._pulse_ms = pulse_settings.duration
        self._configure_pulse_power(pulse_settings.power)
        self._configure_hold_power(None)
        self.platform.send_command_background(PinotaurDefines.PulseSolenoid,
                                              bytes([self.index, pulse_settings.duration]))
        # TODO: restore pulse_ms/pulse_power/hold_power in case we have a rule

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable driver."""
        if self.has_rule:
            # TODO: check if this is actually possible with rule -> do we need a timer?
            raise AssertionError("It is currently not possible to enable this coil while a rule is active.")
        self._configure_pulse_power(pulse_settings.power)
        assert 0 <= pulse_settings.duration <= 255
        # pulse_ms 0 has special meaning in Pinotaur firmware
        pulse_ms = pulse_settings.duration if pulse_settings.duration > 0 else 1
        self._pulse_ms = pulse_settings.duration
        self._configure_hold_power(hold_settings)
        # TODO: remove child coil here in case this is another one
        self.platform.send_command_background(PinotaurDefines.PulseSolenoid,
                                              bytes([self.index, pulse_ms]))
        # TODO: restore pulse_ms/pulse_power/hold_power in case we have a rule

    def disable(self):
        """Disable driver."""
        self.platform.send_command_background(PinotaurDefines.DisableSolenoid, bytes([self.index]))

    def get_board_name(self):
        """Return board name."""
        return "Pinotaur"


# TODO: Pinotaur start/launch lights

class PinotaurSimpleLamp(LightPlatformSoftwareFade):

    """A simple light in the Pinotaur platform which only supports on/off."""

    __slots__ = ["platform", "_state"]

    def __init__(self, number, platform):
        """Initialise Pinotaur Light."""
        super().__init__(number, platform.machine.clock.loop, 50)
        self.platform = platform
        self._state = None

    def set_brightness(self, brightness: float):
        """Turn lamp on or off."""
        if brightness > 0 and self._state is not True:
            self.platform.send_byte(PinotaurDefines.GiChannelOn, bytes([self.number]))
            self._state = True
        elif brightness <= 0 and self._state is not False:
            self.platform.send_byte(PinotaurDefines.GiChannelOff, bytes([self.number]))
            self._state = False

    def get_board_name(self):
        """Return board name."""
        return "Pinotaur"

    def is_successor_of(self, other):
        """Return true if the other light has the previous number."""
        return self.number == other.number + 1

    def get_successor_number(self):
        """Return next number."""
        return self.number + 1

    def __lt__(self, other):
        """Order lights by their order on the hardware."""
        return self.number < other.number


class PinotaurModernLight(PlatformBatchLight):

    """A modern light in Pinotaur."""

    __slots__ = ["platform"]

    def __init__(self, number, platform, light_system):
        """Initialise Pinotaur Light."""
        super().__init__(number, light_system)
        self.platform = platform

    def get_max_fade_ms(self) -> int:
        """Return max fade time."""
        return 65535

    def get_board_name(self):
        """Return board name."""
        return "Pinotaur"

    def is_successor_of(self, other):
        """Return true if the other light has the previous number."""
        return self.number == other.number + 1

    def get_successor_number(self):
        """Return next number."""
        return self.number + 1

    def __lt__(self, other):
        """Order lights by their order on the hardware."""
        return self.number < other.number


# pylint: disable-msg=too-many-instance-attributes
class PinotaurHardwarePlatform(SwitchPlatform, LightsPlatform, DriverPlatform, ServoPlatform, StepperPlatform,
                               LogMixin):

    """Pinotaur platform."""

    # TODO: add new MotorPlatform

    __slots__ = ["config", "_writer", "_reader", "_poll_task", "_watchdog_task", "_number_of_lamps",
                 "_number_of_solenoids", "_inputs",
                 "_bus_lock", "_number_of_modern_lights",
                 "_light_system", "_firmware_version", "_hardware_name"]  # type: List[str]

    def __init__(self, machine) -> None:
        """Initialise platform."""
        super().__init__(machine)
        self._writer = None                 # type: Optional[asyncio.StreamWriter]
        self._reader = None                 # type: Optional[asyncio.StreamReader]
        self._poll_task = None
        self._watchdog_task = None
        self._bus_lock = asyncio.Lock()
        self._number_of_lamps = None        # type: Optional[int]
        self._number_of_solenoids = None    # type: Optional[int]
        self._number_of_modern_lights = None    # type: Optional[int]
        self._inputs = dict()               # type: Dict[str, bool]
        self.features['max_pulse'] = 255
        self._firmware_version = None
        self._hardware_name = None

        self.config = self.machine.config_validator.validate_config("pinotaur",
                                                                    self.machine.config.get('pinotaur', {}))
        self._configure_device_logging_and_debug("Pinotaur", self.config)
        self._light_system = None

    def _clear_read_buffer(self):
        """Clear read buffer."""
        # pylint: disable-msg=protected-access
        if self.debug and self._reader._buffer:
            # pylint: disable-msg=protected-access
            self.debug_log("Flushed: %s%s", self._reader._buffer, "".join(" 0x%02x" % b for b in self._reader._buffer))
        if hasattr(self._writer.transport, "_serial"):
            # pylint: disable-msg=protected-access
            self._writer.transport._serial.reset_input_buffer()
        # pylint: disable-msg=protected-access
        self._reader._buffer = bytearray()
        # pylint: disable-msg=protected-access
        self._reader._maybe_resume_transport()

    # pylint: disable-msg=too-many-statements
    # pylint: disable-msg=too-many-branches
    async def initialize(self):
        """Initialise platform."""
        await super().initialize()

        self.log.info("Connecting to %s", self.config['port'])
        connector = self.machine.clock.open_serial_connection(
            url=self.config['port'], baudrate=self.config['baud'])

        self._reader, self._writer = await connector

        # give the serial a few ms to read the first bytes
        await asyncio.sleep(.1)

        while True:
            # reset platform
            self.debug_log("Sending reset.")
            self._clear_read_buffer()
            try:
                # try init
                response = await asyncio.wait_for(
                    self.send_command_and_read_response(PinotaurDefines.InitReset, None, 1), timeout=.5)
            except asyncio.TimeoutError:
                self.warning_log("Reset of Pinotaur failed. Did get a timeout. Will retry.")
                continue
            if response[0] != 0:
                # reset failed
                self.warning_log("Reset of Pinotaur failed. Got %s instead of 0. Will retry.", response[0])
                continue

            # get type
            hardware_name = await self.send_command_and_read_response(PinotaurDefines.GetConnectedHardware,
                                                                      None, None)

            firmware_version = await self.send_command_and_read_response(PinotaurDefines.GetFirmwareVersion,
                                                                         None, 1)

            self.debug_log("Connected to %s hardware. Firmware version: %s.", hardware_name, firmware_version)

            if not firmware_version:
                self.error_log("Failed to read pinotaur_version from Pinotaur. Got %s", firmware_version)
                continue

            self._firmware_version = firmware_version.decode()

            # if we made it here reset succeeded
            break

        self._hardware_name = hardware_name.decode()

        self.machine.variables.set_machine_var("pinotaur_hardware", self._hardware_name)
        '''machine_var: pinotaur_hardware

        desc: Connected Pinotaur hardware.
        '''

        self.machine.variables.set_machine_var("pinotaur_version", self._firmware_version)
        '''machine_var: pinotaur_version

        desc: Pinotaur version.
        '''

        # get number of lamps
        self._number_of_lamps = (await self.send_command_and_read_response(PinotaurDefines.GetSimpleLampCount,
                                                                           None, 1))[0]

        # get number of solenoids
        self._number_of_solenoids = (await self.send_command_and_read_response(PinotaurDefines.GetSolenoidCount,
                                                                               None, 1))[0]

        # get number of modern lights
        self._number_of_modern_lights = (await self.send_command_and_read_response(
            PinotaurDefines.GetModernLightCount, None, 1))[0]

        self._light_system = PlatformBatchLightSystem(self.machine.clock,
                                                      self._send_multiple_light_update,
                                                      self.machine.config['mpf'][
                                                          'default_light_hw_update_hz'],
                                                      10)       # TODO: figure out max batch size

        self.debug_log("Number of lamps: %s. Number of coils: %s. Number of modern lights: %s",
                       self._number_of_lamps, self._number_of_solenoids, self._number_of_modern_lights)

        # initially read all switches
        self.debug_log("Reading all switches.")
        # clear all changes since we will read all switches now
        await self.send_command(PinotaurDefines.FlushChanged)
        for number in range(128):
            state = await self.send_command_and_read_response(PinotaurDefines.GetSwitchStatus, bytes([number]), 2)
            if state[1] == 2:
                continue
            if state[1] > 2:
                raise AssertionError("Invalid switch {}. Got response: {}".format(number, state))

            self._inputs[str(number)] = state[1] == 1

        self.debug_log("Init of Pinotaur done.")

    async def _send_multiple_light_update(self, sequential_brightness_list):
        # TODO: figure out correct command - current fade speed is tricky
        common_fade_ms = sequential_brightness_list[0][2]
        if common_fade_ms < 0:
            common_fade_ms = 0
        fade_time = int(common_fade_ms)

        data = bytearray([int(sequential_brightness_list[0][0].number / 256),
                          sequential_brightness_list[0][0].number % 256,
                          int(fade_time / 255), int(fade_time & 0xFF),
                          len(sequential_brightness_list)])
        for _, brightness, _ in sequential_brightness_list:
            data.append(int(255 * brightness))

        # TODO: use correct command
        await self.send_command(PinotaurDefines.SetRGBLight)

    async def start(self):
        """Start reading switch changes."""
        self._watchdog_task = self.machine.clock.loop.create_task(self._watchdog())
        self._watchdog_task.add_done_callback(Util.raise_exceptions)
        self._poll_task = self.machine.clock.loop.create_task(self._poll())
        self._poll_task.add_done_callback(Util.raise_exceptions)
        self._light_system.start()

        # turn on relay
        await self.send_command(PinotaurDefines.RelayControl, bytes([1]))

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

    async def _poll(self):
        sleep_time = 1.0 / self.config['poll_hz']
        while True:
            try:
                status = await self.send_command_and_read_response(PinotaurDefines.GetChangedSwitches, None, 1)
            except TimeoutError:
                self.warning_log("Polling switches timed out.")
                await asyncio.sleep(sleep_time)
                continue
            if status[0] == 0x7f:
                # no changes. sleep according to poll_hz
                await asyncio.sleep(sleep_time)
            else:
                # bit 7 is state
                switch_state = 1 if status[0] & 0b10000000 else 0
                # bits 0-6 are the switch number
                switch_num = status[0] & 0b01111111

                # tell the switch controller about the new state
                self.machine.switch_controller.process_switch_by_num(str(switch_num), switch_state, self)

                # store in dict as well
                self._inputs[str(switch_num)] = bool(switch_state)

    async def _watchdog(self):
        """Periodically send watchdog."""
        # TODO: handle any over-currents or faults here
        while True:
            # send watchdog
            try:
                response = await self.send_command_and_read_response(PinotaurDefines.WatchDogFlag, None, 1)
            except TimeoutError:
                self.warning_log("Watchdog response timed out.")
                await asyncio.sleep(.1)
                continue
            if response[0] != 0:
                self.warning_log("Watchdog returned %s instead 0", response[0])
            # sleep 500ms
            await asyncio.sleep(.5)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and release rule on driver."""
        # TODO: implement

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                      eos_switch: SwitchSettings, coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver.

        Pulses a driver when a switch is hit. When the switch is released
        the pulse is canceled and the driver gets disabled. When the eos_switch is hit the pulse is canceled
        and the driver becomes disabled. Typically used on the main coil for dual-wound coil flippers with eos switch.
        """
        # TODO: implement

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver becomes disabled. When the eos_switch is hit the pulse is canceled
        and the driver becomes enabled (likely with PWM).
        Typically used on the coil for single-wound coil flippers with eos switch.
        """
        # TODO: implement

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and release rule to driver."""
        # TODO: implement

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit rule on driver."""
        # TODO: implement

    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """Clear hw rule for driver."""
        # TODO: implement

    def configure_light(self, number: str, subtype: str, config, platform_settings: dict) -> LightPlatformInterface:
        """Configure light on Pinotaur."""
        del platform_settings, config
        assert self._number_of_lamps is not None
        assert self._number_of_modern_lights is not None

        if subtype is None or subtype == "gi":
            if 0 < int(number) >= self._number_of_lamps:
                raise AssertionError("Pinotaur only has {} lamps. Cannot configure lamp {}.".
                                     format(self._number_of_lamps, number))

            return PinotaurSimpleLamp(int(number), self)
        if subtype == "light":
            if 0 < int(number) >= self._number_of_modern_lights:
                raise AssertionError("Pinotaur only has {} modern lights. Cannot configure light {}.".
                                     format(self._number_of_modern_lights, number))
            return PinotaurModernLight(int(number), self, self._light_system)

        raise self.raise_config_error("Invalid subtype {}".format(subtype), 1)

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Return a single light."""
        # TODO handle subtypes
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

        return PinotaurSwitch(config=config, number=number)

    async def get_hw_switch_states(self):
        """Return current switch states."""
        return self._inputs

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> DriverPlatformInterface:
        """Configure a driver."""
        assert self._number_of_solenoids is not None
        assert self._number_of_lamps is not None

        if 0 < int(number) > self._number_of_solenoids:
            raise AssertionError("Pinotaur only has {} drivers. Cannot configure driver {}.".
                                 format(self._number_of_solenoids, number))

        driver = PinotaurDriver(config=config, number=number, platform=self)
        recycle_time = config.default_pulse_ms * 2 if config.default_recycle else config.default_pulse_ms
        if recycle_time > 255:
            recycle_time = 255
        driver.configure_recycle(recycle_time)
        return driver

    def send_command_background(self, cmd: int, payload: Optional[bytes] = None):
        """Send command in the background."""
        future = asyncio.ensure_future(self.send_command_and_read_response(cmd, payload, 0))
        future.add_done_callback(Util.raise_exceptions)

    async def send_command(self, cmd: int, payload: Optional[bytes] = None):
        """Send command to bus."""
        assert self._reader is not None
        async with self._bus_lock:
            self._send_command(cmd, payload)

    async def send_command_and_read_response(self, cmd: int, payload: Optional[bytes],
                                             response_size: Optional[int]) -> bytes:
        """Send command and wait for response."""
        assert self._reader is not None
        async with self._bus_lock:
            self._send_command(cmd, payload)
            if response_size is not None:
                return await self._read_response(cmd, response_size)

            return await self._read_string(cmd)

    def _send_command(self, cmd: int, payload: Optional[bytes] = None):
        """Send command to bus without bus lock."""
        msg = bytearray()
        msg.append(ord('<'))
        msg.append(cmd)
        msg.append((len(payload) << 1) | 0x81 if payload else 0x81)
        if payload:
            msg.extend(payload)
        self._clear_read_buffer()
        self._writer.write(bytes(msg))

    async def _read_response(self, cmd: int, response_size: int) -> bytes:
        """Read response from bus without bus lock."""
        response = await asyncio.wait_for(self._reader.readexactly(2 + response_size), timeout=0.1)
        if self._debug:
            self.debug_log("Received Response %s (%s)", bytes(response), "".join(" 0x%02x" % b for b in response))
        if response[0] != ord('>') or response[1] != cmd:
            # TODO: handle this
            raise AssertionError("Incorrect response: {} ({})".format(
                response, "".join(" 0x%02x" % b for b in response)))
        return response[2:]

    # pylint: disable-msg=inconsistent-return-statements
    async def _read_until(self, separator, min_chars: int = 0):
        """Read until separator.

        Args:
        ----
            separator: Read until this separator byte.
            min_chars: Minimum message length before separator
        """
        assert self._reader is not None

        # asyncio StreamReader only supports this from python 3.5.2 on
        buffer = b''
        while True:
            char = await self._reader.readexactly(1)
            buffer += char
            if char == separator and len(buffer) > min_chars:
                return buffer

    async def _read_string(self, cmd) -> bytes:
        """Read zero terminated string."""
        response = await asyncio.wait_for(self._reader.readexactly(2), timeout=0.1)
        if response[0] != ord('>') or response[1] != cmd:
            # TODO: handle this
            raise AssertionError("Incorrect response: {}".format(response))
        data = await asyncio.wait_for(self._read_until(b'\x00'), timeout=0.1)
        # remove terminator
        data = data[:-1]
        self.debug_log("Received String %s", data)
        return data

    def get_info_string(self):
        """Dump info about Pinotaur platform."""
        info = ""
        info += "Pinotaur connected via serial on {}\n".format(self.config['port'])
        info += "Hardware: {} Firmware Version: {}\n".format(
            self._hardware_name, self._firmware_version)
        info += "Input map: {}\n".format(sorted(list(self._inputs.keys()), key=int))
        info += "Coil count: {}\n".format(self._number_of_solenoids)
        info += "Modern lights count: {}\n".format(self._number_of_modern_lights)
        info += "Traditional lights count: {}\n".format(self._number_of_lamps)
        return info

    async def configure_servo(self, number: str) -> ServoPlatformInterface:
        """Configure a servo."""
        # TODO: implement

    async def configure_stepper(self, number: str, config: dict) -> StepperPlatformInterface:
        """Configure a stepper."""
        # TODO: implement
