"""VPX platform."""
import asyncio
from typing import Dict, List, Optional

import logging


from mpf.devices.segment_display.segment_display_text import ColoredSegmentDisplayText
from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface, FlashingType

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.core.platform import LightsPlatform, SwitchPlatform, DriverPlatform, SwitchSettings, DriverSettings, \
    SwitchConfig, DriverConfig, RepulseSettings, SegmentDisplayPlatform


class VirtualPinballSwitch(SwitchPlatformInterface):

    """A switch in VPX."""

    __slots__ = ["state"]

    def __init__(self, config, number, platform):
        """Initialize switch."""
        super().__init__(config, number, platform)
        self.state = self.config.invert

    def get_board_name(self):
        """Return the name of the board of this switch."""
        return "VPX"


class VirtualPinballLight(LightPlatformInterface):

    """A light in VPX."""

    __slots__ = ["_current_fade", "subtype", "hw_number", "machine"]

    def __init__(self, number, subtype, hw_number, machine):
        """Initialize LED."""
        super().__init__(number)
        self._current_fade = (0, -1, 0, -1)
        self.subtype = subtype
        self.hw_number = hw_number
        self.machine = machine

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
        """Set fade."""
        self._current_fade = (start_brightness, start_time, target_brightness, target_time)

    def get_board_name(self):
        """Return the name of the board of this light."""
        return "VPX"

    def is_successor_of(self, other):
        """Return true if the other light has the same number string plus the suffix '+1'."""
        return self.number == other.number + "+1"

    def get_successor_number(self):
        """Return the number with the suffix '+1'.

        As there is not real number format for virtual is this is all we can do here.
        """
        return self.number + "+1"

    def __lt__(self, other):
        """Not implemented."""
        raise AssertionError("Not implemented. Let us know if you need it.")


class VirtualPinballDriver(DriverPlatformInterface):

    """A driver in VPX."""

    __slots__ = ["clock", "_state"]

    def __init__(self, config, number, clock):
        """Initialize virtual driver to disabled."""
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

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and enable the coil for an explicit duration."""
        raise NotImplementedError

    @property
    def state(self) -> bool:
        """Return current state."""
        # pylint: disable-msg=no-else-return
        if isinstance(self._state, bool):
            return self._state
        else:
            return bool(self.clock.get_time() < self._state)


class VirtualPinballSegmentDisplay(SegmentDisplayPlatformInterface):

    """Virtual segment display."""

    __slots__ = ["_text", "flashing", "flash_mask", "machine"]

    def __init__(self, number, machine) -> None:
        """Initialise virtual segment display."""
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


class VirtualPinballPlatform(LightsPlatform, SwitchPlatform, DriverPlatform, SegmentDisplayPlatform):

    """VPX platform."""

    __slots__ = ["_lights", "_switches", "_drivers", "_last_drivers", "_last_lights", 
                 "_started", "rules", "_configured_segment_displays", "_last_segment_text"]

    def __init__(self, machine):
        """Initialize VPX platform."""
        super().__init__(machine)
        self._lights = {}           # type: Dict[str, VirtualPinballLight]
        self._switches = {}         # type: Dict[str, VirtualPinballSwitch]
        self._drivers = {}          # type: Dict[str, VirtualPinballDriver]
        self._last_drivers = {}     # type: Dict[str, bool]
        self._last_lights = {}      # type: Dict[str, float]
        self._configured_segment_displays = []  # type: List[VirtualPinballSegmentDisplay]
        self._last_segment_text = {}  # type: Dict[str, str]
        self._started = asyncio.Event()
        self.log = logging.getLogger("VPX Platform")
        self.log.debug("Configuring VPX hardware interface.")
        self.rules = {}

    async def initialize(self):
        """Initialize platform."""
        self.machine.bcp.interface.register_command_callback("vpcom_bridge", self._dispatch)
        self.machine.events.add_async_handler("init_phase_5", self._wait_for_connect)

    async def _wait_for_connect(self):
        """Wait until VPX connects."""
        await self._started.wait()

    async def _dispatch(self, client, subcommand=None, **kwargs):
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
        # pylint: disable-msg=broad-except
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
        # pylint: disable-msg=no-else-return
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
        """Return changed lights since last call.

        Returns bool for each light state but floating point brightness
        is stored in _last_lights to support other methods returning float.
        """
        changed_lamps = []
        for number, light in self._lights.items():
            if light.subtype != subtype:
                continue
            brightness = light.current_brightness
            state = bool(brightness > 0.5)
            if state != bool(self._last_lights[number] > 0.5):
                changed_lamps.append((light.hw_number, state))
                self._last_lights[number] = brightness

        return changed_lamps

    def _get_changed_brightness_lights_by_subtype(self, subtype):
        """Return changed lights since last call. Returns float for each light brightness."""
        changed_lamps = []
        for number, light in self._lights.items():
            if light.subtype != subtype:
                continue
            brightness = light.current_brightness
            if brightness != self._last_lights[number]:
                changed_lamps.append((light.hw_number, brightness))
                self._last_lights[number] = brightness

        return changed_lamps

    def _get_changed_segment_text(self):
        """Return changed configured segment text since last call."""
        changed_segments = []
        for segment_display in self._configured_segment_displays:
            text = segment_display.text
            number = segment_display.number
            if text != self._last_segment_text[number]:
                changed_segments.append((number, text))
                self._last_segment_text[number] = text

        return changed_segments

    def vpx_changed_lamps(self):
        """Return changed lamps since last call."""
        return self._get_changed_lights_by_subtype("matrix")

    def vpx_changed_gi_strings(self):
        """Return changed lamps since last call."""
        return self._get_changed_lights_by_subtype("gi")

    def vpx_changed_leds(self):
        """Return changed leds since last call."""
        return self._get_changed_lights_by_subtype("led")

    def vpx_changed_brightness_leds(self):
        """Return changed brightness leds since last call."""
        return self._get_changed_brightness_lights_by_subtype("led")

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

    def vpx_changed_segment_text(self):
        """Return changed segment text since last call."""
        return self._get_changed_segment_text()

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> "SwitchPlatformInterface":
        """Configure VPX switch."""
        number = str(number)
        switch = VirtualPinballSwitch(config, number, self)
        self._switches[number] = switch
        return switch

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> "DriverPlatformInterface":
        """Configure VPX driver."""
        number = str(number)
        driver = VirtualPinballDriver(config, number, self.machine.clock)
        self._drivers[number] = driver
        self._last_drivers[number] = False
        return driver

    def validate_segment_display_section(self, segment_display, config):
        """Validate segment display sections."""
        del segment_display
        return config

    def vpx_get_hardwarerules(self):
        """Return hardware rules."""
        hardware_rules = []
        for rswitchandcoil, hold in self.rules.items():
            hardware_rules.append((rswitchandcoil[0].number, rswitchandcoil[1].number, hold))
        return hardware_rules

    def _add_rule(self, switch, coil, hold):
        """Add rule with or without hold."""
        if (switch, coil) in self.rules:
            raise AssertionError("Overwrote a rule without clearing it first {} <-> {}".format(
                switch, coil))
        self.rules[(switch, coil)] = hold

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Pulse on hit and hold."""
        self._add_rule(enable_switch.hw_switch, coil.hw_driver, True)

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings, eos_switch: SwitchSettings,
                                                      coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Pulse on hit, disable on disable_switch hit."""
        del eos_switch
        # eos_switch is missing here intentionally
        self._add_rule(enable_switch.hw_switch, coil.hw_driver, False)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Pulse on hit and hold, disable on disable_switch hit."""
        del eos_switch
        # eos_switch is missing here intentionally
        self._add_rule(enable_switch.hw_switch, coil.hw_driver, True)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Pulse on hit and hold."""
        self._add_rule(enable_switch.hw_switch, coil.hw_driver, True)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings,
                              coil: DriverSettings):
        """Pulse on hit and release."""
        self._add_rule(enable_switch.hw_switch, coil.hw_driver, False)

    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """Clear hw rule."""
        if (switch.hw_switch, coil.hw_driver) in self.rules:
            del self.rules[(switch.hw_switch, coil.hw_driver)]
        else:
            self.log.debug("Tried to clear a non-existing rules %s <-> %s", switch, coil)

    def vpx_get_coilactive(self, number):
        """Return True if a MPF hw rule for the coil(number) exists."""
        for rswitchandcoil, _ in self.rules.items():
            if rswitchandcoil[1].number == number:
                return True

        return False

    async def get_hw_switch_states(self):
        """Return initial switch state."""
        hw_switches = {}
        for switch in self._switches.values():
            hw_switches[switch.number] = switch.state ^ switch.config.invert
        return hw_switches

    def configure_light(self, number: str, subtype: str, config, platform_settings: dict) -> "LightPlatformInterface":
        """Configure a VPX light."""
        del config
        if subtype and subtype not in ("gi", "matrix", "led", "flasher"):
            raise AssertionError("Unknown subtype: {}".format(subtype))
        if not subtype:
            subtype = "matrix"
        number = str(number)
        key = number + "-" + subtype
        light = VirtualPinballLight(key, subtype, number, self.machine)
        self._lights[key] = light
        self._last_lights[key] = 0.0
        return light

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse channel str to a list of channels."""
        # pylint: disable-msg=no-else-return
        if subtype in ("gi", "matrix", "led", "flasher") or not subtype:
            return [
                {
                    "number": str(number)
                }
            ]
        else:
            raise AssertionError("Unknown subtype {}".format(subtype))

    async def configure_segment_display(self, number: str, display_size: int,
                                        platform_settings) -> SegmentDisplayPlatformInterface:
        """Configure segment display."""
        del platform_settings
        del display_size
        segment_display = VirtualPinballSegmentDisplay(number, self.machine)
        self._configured_segment_displays.append(segment_display)
        self._last_segment_text[number] = None
        return segment_display
