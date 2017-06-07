"""LISY platform for System 1 and System 80."""
import asyncio
from typing import Generator

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.core.logging import LogMixin

from mpf.platforms.lisy.defines import LisyDefines

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade

from mpf.core.platform import SwitchPlatform, LightsPlatform, DriverPlatform, SwitchSettings, DriverSettings, \
    DriverConfig, SwitchConfig


class LisySwitch(SwitchPlatformInterface):

    """A switch in the LISY platform."""

    pass


class LisyDriver(DriverPlatformInterface):

    """A driver in the LISY platform."""

    def __init__(self, config, number, platform):
        """Initialise driver."""
        super().__init__(config, number)
        self.platform = platform

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse driver."""
        del pulse_settings
        self.platform.send_byte(LisyDefines.SolenoidsPulseSolenioid, int(self.number))

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable driver."""
        del pulse_settings
        del hold_settings
        self.platform.send_byte(LisyDefines.SolenoidsSetSolenoidToOn, int(self.number))

    def disable(self):
        """Disable driver."""
        self.platform.send_byte(LisyDefines.SolenoidsSetSolenoidToOff, int(self.number))

    def get_board_name(self):
        """Return board name."""
        return "LISY"


class LisyLight(LightPlatformSoftwareFade):

    """A light in the LISY platform."""

    def __init__(self, number, platform):
        """Initialise Lisy Light."""
        super().__init__(platform.machine.clock.loop, 50)
        self.number = number
        self.platform = platform

    def set_brightness(self, brightness: float):
        """Turn lamp on or off."""
        if brightness > 0:
            self.platform.send_byte(LisyDefines.LampsSetLampOn, self.number)
        else:
            self.platform.send_byte(LisyDefines.LampsSetLampOff, self.number)


class LisyHardwarePlatform(SwitchPlatform, LightsPlatform, DriverPlatform, LogMixin):

    """LISY platform."""

    def __init__(self, machine):
        """Initialise platform."""
        super().__init__(machine)
        self.config = None
        self._writer = None
        self._reader = None
        self._poll_task = None
        self._number_of_lamps = None
        self._number_of_solenoids = None
        self._number_of_displays = None
        self._inputs = dict()

    @asyncio.coroutine
    def initialize(self):
        """Initialise platform."""
        self.config = self.machine.config_validator.validate_config("lisy", self.machine.config['lisy'])

        self.configure_logging("lisy", self.config['console_log'], self.config['file_log'])

        self.log.info("Connecting to %s at %sbps", self.config['port'], self.config['baud'])

        connector = self.machine.clock.open_serial_connection(
            url=self.config['port'], baudrate=self.config['baud'], limit=0)
        self._reader, self._writer = yield from connector

        # reset platform
        self.send_byte(LisyDefines.GeneralReset)
        return_code = yield from self.read_byte()
        if return_code != 0:
            raise AssertionError("Reset of LISY failed. Got {} instead of 0".format(return_code))

        # get number of lamps
        self.send_byte(LisyDefines.InfoGetNumberOfLamps)
        self._number_of_lamps = yield from self.read_byte()

        # get number of solenoids
        self.send_byte(LisyDefines.InfoGetNumberOfSolenoids)
        self._number_of_solenoids = yield from self.read_byte()

        # get number of displays
        self.send_byte(LisyDefines.InfoGetNumberOfDisplays)
        self._number_of_displays = yield from self.read_byte()

        # initially read all switches
        for row in range(8):
            for col in range(8):
                number = row * 10 + col
                self.send_byte(LisyDefines.SwitchesGetStatusOfSwitch, number)
                state = yield from self.read_byte()
                if state > 1:
                    raise AssertionError("Invalid switch {}. Got response: {}".format(number, state))

                self._inputs[str(number)] = state == 1

        self._poll_task = self.machine.clock.loop.create_task(self._poll())
        self._poll_task.add_done_callback(self._done)

    def stop(self):
        """Stop platform."""
        if self._poll_task:
            self._poll_task.cancel()

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

        if int(number) >= self._number_of_lamps:
            raise AssertionError("LISY only has {} lamps. Cannot configure lamp {} (zero indexed).".
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

    def get_hw_switch_states(self):
        """Return current switch states."""
        return self._inputs

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> DriverPlatformInterface:
        """Configure a driver."""
        return LisyDriver(config=config, number=number, platform=self)

    def send_byte(self, cmd: int, byte: int=None):
        """Send a command with optional payload."""
        if byte is not None:
            self._writer.write(bytes([cmd, byte]))
        else:
            self._writer.write(bytes([cmd]))

    @asyncio.coroutine
    def read_byte(self) -> Generator[int, None, int]:
        """Read one byte."""
        data = yield from self._reader.readexactly(1)
        return ord(data)
