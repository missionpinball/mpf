"""VPX platform."""
import asyncio
from typing import Callable, Tuple, Dict

import logging

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings

from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.core.platform import LightsPlatform, SwitchPlatform, DriverPlatform, SwitchSettings, DriverSettings, \
    SwitchConfig, DriverConfig


class VirtualPinballSwitch(SwitchPlatformInterface):

    """A switch in VPX."""

    def __init__(self, config, number):
        """Initialise switch."""
        super().__init__(config, number)
        self.state = self.config.invert

    def get_board_name(self):
        """Return the name of the board of this switch."""
        return "VPX"

class VirtualPinballLight(LightPlatformInterface):

    """A light in VPX."""

    def __init__(self, number, subtype, hw_number):
        """Initialise LED."""
        super().__init__(number)
        self.color_and_fade_callback = None
        self.subtype = subtype
        self.hw_number = hw_number

    @property
    def current_brightness(self) -> float:
        """Return current brightness."""
        if self.color_and_fade_callback:
            return self.color_and_fade_callback(0)[0]

        return 0

    def set_fade(self, color_and_fade_callback: Callable[[int], Tuple[float, int]]):
        """Store CB function."""
        self.color_and_fade_callback = color_and_fade_callback

    def get_board_name(self):
        """Return the name of the board of this light."""
        return "VPX"


class VirtualPinballDriver(DriverPlatformInterface):

    """A driver in VPX."""

    def __init__(self, config, number, clock):
        """Initialise virtual driver to disabled."""
        super().__init__(config, number)
        self.clock = clock
        self._state = False

    def get_board_name(self):
        """Return the name of the board of this driver."""
        return "VPX"

    def disable(self):
        """Disable virtual coil."""
        self._state = False

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable virtual coil."""
        del pulse_settings, hold_settings
        self._state = True

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse virtual coil."""
        self._state = self.clock.get_time() + (pulse_settings.duration / 1000.0)

    @property
    def state(self) -> bool:
        """Return current state."""
        if isinstance(self._state, bool):
            return self._state
        else:
            return bool(self.clock.get_time() < self._state)


class VirtualPinballPlatform(LightsPlatform, SwitchPlatform, DriverPlatform):

    """VPX platform."""

    def __init__(self, machine):
        """Initialise VPX platform."""
        super().__init__(machine)
        self._lights = {}       # type: Dict[str, VirtualPinballLight]
        self._switches = {}     # type: Dict[str, VirtualPinballSwitch]
        self._drivers = {}      # type: Dict[str, VirtualPinballDriver]
        self._last_drivers = {} # type: Dict[str, bool]
        self._last_lights = {}  # type: Dict[str, bool]
        self._started = asyncio.Event(loop=self.machine.clock.loop)
        self.log = logging.getLogger("VPX Platform")
        self.log.debug("Configuring VPX hardware interface.")
        self.rules = {}

    @asyncio.coroutine
    def initialize(self):
        """Initialise platform."""
        self.machine.bcp.interface.register_command_callback("vpcom_bridge", self._dispatch)
        self.machine.events.add_async_handler("init_phase_5", self._wait_for_connect)

    @asyncio.coroutine
    def _wait_for_connect(self):
        """Wait until VPX connects."""
        yield from self._started.wait()

    @asyncio.coroutine
    def _dispatch(self, client, subcommand=None, **kwargs):
        """Dispatch a VPX COM call."""
        self.log.debug("Got command %s args: %s", subcommand, kwargs)
        if not subcommand:
            self.machine.bcp.transport.send_to_client(client, "vpcom_bridge_response", error="command missing")
        try:
            method = getattr(self, "vpx_" + subcommand)
        except AttributeError:
            self.machine.bcp.transport.send_to_client(client, "vpcom_bridge_response",
                                                      error="Unknown command {}".format(subcommand))
            return

        try:
            result = method(**kwargs)
        except Exception as e:
            self.machine.bcp.transport.send_to_client(client, "vpcom_bridge_response",
                                                      error="Exception: {}".format(e))
            return
        self.machine.bcp.transport.send_to_client(client, "vpcom_bridge_response", result=result)

    def vpx_start(self):
        """Start machine."""
        self._started.set()
        return True

    def vpx_get_switch(self, number):
        """Return switch value."""
        if self._switches[str(number)].config.invert:
            return not self._switches[str(number)].state
        else:
            return self._switches[str(number)].state

    def vpx_switch(self, number):
        """Return switch value."""
        return self.vpx_get_switch(number)

    def vpx_set_switch(self, number, value):
        """Update switch from VPX."""
        self._switches[str(number)].state = value
        self.machine.switch_controller.process_switch_by_num(state=1 if value else 0,
                                                             num=str(number),
                                                             platform=self)
        return True

    def vpx_pulsesw(self, number):
        """Pulse switch from VPX."""
        self._switches[str(number)].state = True
        self.machine.switch_controller.process_switch_by_num(state=1,
                                                             num=str(number),
                                                             platform=self)
        self._switches[str(number)].state = False
        self.machine.switch_controller.process_switch_by_num(state=0,
                                                             num=str(number),
                                                             platform=self)
        return True

    def vpx_changed_solenoids(self):
        """Return changed solenoids since last call."""
        changed_drivers = []
        for number, driver in self._drivers.items():
            if driver.state != self._last_drivers[number]:
                changed_drivers.append((number, driver.state))
                self._last_drivers[number] = driver.state

        return changed_drivers

    def _get_changed_lights_by_subtype(self, subtype):
        """Return changed lights since last call."""
        changed_lamps = []
        for number, light in self._lights.items():
            if light.subtype != subtype:
                continue
            brightness = light.current_brightness
            state = bool(brightness > 0.5)
            if state != self._last_lights[number]:
                changed_lamps.append((light.hw_number, state))
                self._last_lights[number] = state

        return changed_lamps

    def vpx_changed_lamps(self):
        """Return changed lamps since last call."""
        return self._get_changed_lights_by_subtype("matrix")

    def vpx_changed_gi_strings(self):
        """Return changed lamps since last call."""
        return self._get_changed_lights_by_subtype("gi")

    def vpx_changed_leds(self):
        """Return changed lamps since last call."""
        return self._get_changed_lights_by_subtype("led")

    def vpx_changed_flashers(self):
        """Return changed lamps since last call."""
        return self._get_changed_lights_by_subtype("flasher")

    def vpx_mech(self, number):
        """Not implemented."""
        self.log.warning("Command \"mech\" unimplemented: %s", number)
        return True

    def vpx_get_mech(self, number):
        """Not implemented."""
        self.log.warning("Command \"get_mech\" unimplemented: %s", number)
        return True

    def vpx_set_mech(self, number, value):
        """Not implemented."""
        self.log.warning("Command \"set_mech\" unimplemented: %s %s", number, value)
        return True

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> "SwitchPlatformInterface":
        """Configure VPX switch."""
        number = str(number)
        switch = VirtualPinballSwitch(config, number)
        self._switches[number] = switch
        return switch

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> "DriverPlatformInterface":
        """Configure VPX driver."""
        number = str(number)
        driver = VirtualPinballDriver(config, number, self.machine.clock)
        self._drivers[number] = driver
        self._last_drivers[number] = False
        return driver

    def vpx_get_hardwarerules(self):
        """Return hardware rules."""
        hardware_rules = []
        for rswitchandcoil, hold in self.rules.items():
            hardware_rules.append((rswitchandcoil[0].number, rswitchandcoil[1].number, hold))
        return hardware_rules

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Pulse on hit and hold."""
        if (enable_switch.hw_switch, coil.hw_driver) in self.rules:
            raise AssertionError("Overwrote a rule without clearing it first {} <-> {}".format(
                enable_switch.hw_switch, coil.hw_driver))
        else:
            self.rules[(enable_switch.hw_switch, coil.hw_driver)] = True

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 disable_switch: SwitchSettings, coil: DriverSettings):
        """Pulse on hit and hold, disable on disable_switch hit."""
        if (enable_switch.hw_switch, coil.hw_driver) in self.rules:
            raise AssertionError("Overwrote a rule without clearing it first {} <-> {}".format(
                enable_switch.hw_switch, coil.hw_driver))
        else:
            """disable_switch missing"""
            self.rules[(enable_switch.hw_switch, coil.hw_driver)] = True

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Pulse on hit and hold."""
        if (enable_switch.hw_switch, coil.hw_driver) in self.rules:
            raise AssertionError("Overwrote a rule without clearing it first {} <-> {}".format(
                enable_switch.hw_switch, coil.hw_driver))
        else:
            self.rules[(enable_switch.hw_switch, coil.hw_driver)] = True

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings,
                              coil: DriverSettings):
        """Pulse on hit and release."""
        if (enable_switch.hw_switch, coil.hw_driver) in self.rules:
            raise AssertionError("Overwrote a rule without clearing it first {} <-> {}".format(
                enable_switch.hw_switch, coil.hw_driver))
        else:
            self.rules[(enable_switch.hw_switch, coil.hw_driver)] = False

    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """Clear hw rule."""
        if (switch.hw_switch, coil.hw_driver) in self.rules:
            del self.rules[(switch.hw_switch, coil.hw_driver)]
        else:
            self.log.debug("Tried to clear a non-existing rules %s <-> %s", switch, coil)

    def vpx_get_coilactive(self, number):
        """Return True if a MPF hw rule for the coil(number) exists."""
        for rswitchandcoil, hold in self.rules.items():
            if rswitchandcoil[1].number == number:
                return True

        return False

    @asyncio.coroutine
    def get_hw_switch_states(self):
        """Return initial switch state."""
        hw_switches = {}
        for switch in self._switches.values():
            hw_switches[switch.number] = switch.state ^ switch.config.invert
        return hw_switches

    def configure_light(self, number: str, subtype: str, platform_settings: dict) -> "LightPlatformInterface":
        """Configure a VPX light."""
        if subtype and subtype not in ("gi", "matrix", "led", "flasher"):
            raise AssertionError("Unknown subtype: {}".format(subtype))
        if not subtype:
            subtype = "matrix"
        number = str(number)
        key = number + "-" + subtype
        light = VirtualPinballLight(key, subtype, number)
        self._lights[key] = light
        self._last_lights[key] = False
        return light

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse channel str to a list of channels."""
        if subtype in ("gi", "matrix", "led", "flasher") or not subtype:
            return [
                {
                    "number": str(number)
                }
            ]
        else:
            raise AssertionError("Unknown subtype {}".format(subtype))
