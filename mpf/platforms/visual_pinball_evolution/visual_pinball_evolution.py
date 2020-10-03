"""VPE platform."""
import asyncio
from typing import Optional

from grpc.experimental import aio

from mpf import _version
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.core.platform import LightsPlatform, SwitchPlatform, DriverPlatform, SwitchSettings, DriverSettings, \
    SwitchConfig, DriverConfig, RepulseSettings
from mpf.platforms.visual_pinball_evolution.coils_pb2 import PulseCoilRequest, DisableCoilRequest, EnableCoilRequest, \
    ConfigureHardwareRuleRequest, RemoveHardwareRuleRequest
from mpf.platforms.visual_pinball_evolution.fade_light_pb2 import FadeLightRequest
from mpf.platforms.visual_pinball_evolution.get_plaform_details_pb2 import GetPlatformDetailsRequest
from mpf.platforms.visual_pinball_evolution.platform_pb2_grpc import HardwarePlatformStub
from mpf.platforms.visual_pinball_evolution.switch_pb2 import SwitchChangesRequest


class VisualPinballEvolutionSwitch(SwitchPlatformInterface):

    """A switch in VPE."""

    def __init__(self, config, number):
        """Initialise switch."""
        super().__init__(config, number)
        self.state = self.config.invert

    def get_board_name(self):
        """Return the name of the board of this switch."""
        return "VPE"


class VisualPinballEvolutionLight(LightPlatformInterface):

    """A light in VPE."""

    __slots__ = ["platform", "clock"]

    def __init__(self, number, platform):
        """Initialise LED."""
        super().__init__(number)
        self.platform = platform    # type: VisualPinballEvolutionPlatform
        self.clock = self.platform.machine.clock

    def set_fade(self, start_brightness, start_time, target_brightness, target_time):
        """Set fade."""
        # TODO: batch all fades
        current_time = self.clock.get_time()
        if target_time > 0:
            fade_ms = int((target_time - current_time) * 1000)
        else:
            fade_ms = 0
        command = self.platform.platform_rpc.LightFade(
            FadeLightRequest(common_fade_ms=fade_ms,
                             fades=[FadeLightRequest.ChannelFade(
                                 light_number=self.number,
                                 target_brightness=target_brightness)]))
        self.platform.send_command(command)

    def get_board_name(self):
        """Return the name of the board of this light."""
        return "VPE"

    def is_successor_of(self, other):
        """Not implemented."""
        raise AssertionError("Not implemented. Let us know if you need it.")

    def get_successor_number(self):
        """Not implemented."""
        raise AssertionError("Not implemented. Let us know if you need it.")

    def __lt__(self, other):
        """Not implemented."""
        raise AssertionError("Not implemented. Let us know if you need it.")


class VisualPinballEvolutionDriver(DriverPlatformInterface):

    """A driver in VPE."""

    __slots__ = ["platform"]

    def __init__(self, config, number, platform):
        """Initialise virtual driver to disabled."""
        super().__init__(config, number)
        self.platform = platform    # type: VisualPinballEvolutionPlatform

    def get_board_name(self):
        """Return the name of the board of this driver."""
        return "VPE"

    def disable(self):
        """Disable virtual coil."""
        command = self.platform.platform_rpc.CoilDisable(DisableCoilRequest(coil_number=self.number))
        self.platform.send_command(command)

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable virtual coil."""
        command = self.platform.platform_rpc.CoilEnable(EnableCoilRequest(coil_number=self.number,
                                                                          pulse_ms=pulse_settings.duration,
                                                                          pulse_power=pulse_settings.power,
                                                                          hold_power=hold_settings.power))
        self.platform.send_command(command)

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse virtual coil."""
        command = self.platform.platform_rpc.CoilPulse(PulseCoilRequest(coil_number=self.number,
                                                                        pulse_ms=pulse_settings.duration,
                                                                        pulse_power=pulse_settings.power))
        self.platform.send_command(command)


class VisualPinballEvolutionPlatform(LightsPlatform, SwitchPlatform, DriverPlatform):

    """VPE platform."""

    __slots__ = ["config", "_known_switches", "_known_lights", "_known_coils", "_initial_switch_state",
                 "_switch_poll_task", "platform_rpc"]

    def __init__(self, machine):
        """Initialise VPE platform."""
        super().__init__(machine)
        self.config = self.machine.config_validator.validate_config("vpe", self.machine.config.get('vpe', {}))
        self._configure_device_logging_and_debug("VPE Platform", self.config)
        self._initial_switch_state = {}
        self._known_switches = []
        self._known_lights = []
        self._known_coils = []
        self._switch_poll_task = None
        self.platform_rpc = None

    async def connect(self, host, port):
        """Connect to remote host and port."""
        connection_string = "{}:{}".format(host, port)
        channel = aio.insecure_channel(connection_string)
        self.log.info("Connecting to VPE on %s", connection_string)
        await channel.channel_ready()
        return HardwarePlatformStub(channel)

    async def initialize(self):
        """Connect to VPE via gRPC."""
        self.platform_rpc = await self.connect(self.config['remote_host'], self.config['remote_port'])
        detail_request = GetPlatformDetailsRequest()
        detail_request.mpf_version = _version.version
        response = await self.platform_rpc.GetPlatformDetails(detail_request)
        self.info_log("VPE connected")
        self.debug_log("Got response %s", response)
        self._known_switches = list(response.known_switches_with_initial_state.keys())
        self._initial_switch_state = response.known_switches_with_initial_state
        self._known_coils = response.known_coils
        self._known_lights = response.known_lights

    async def start(self):
        """Start listening for switch changes."""
        await super().start()
        self._switch_poll_task = self.machine.clock.loop.create_task(self._switch_poll())
        self._switch_poll_task.add_done_callback(Util.raise_exceptions)

    async def _switch_poll(self):
        """Listen to switch changes from VPE."""
        switch_change_request = SwitchChangesRequest()
        switch_stream = self.platform_rpc.GetSwitchChanges(switch_change_request)
        while True:
            change = await switch_stream.read()
            if self._debug:
                self.debug_log("Got Switch Change: %s", change)
            self.machine.switch_controller.process_switch_by_num(state=1 if change.switch_state else 0,
                                                                 num=change.switch_number,
                                                                 platform=self)

    @staticmethod
    def send_command(command):
        """Send command in the background using asyncio."""
        command_future = asyncio.ensure_future(command)
        command_future.add_done_callback(Util.raise_exceptions)

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> "SwitchPlatformInterface":
        """Configure VPE switch."""
        number = str(number)
        if number not in self._known_switches:
            self.raise_config_error("Switch {} is not known to VPE".format(number), 1)
        return VisualPinballEvolutionSwitch(config, number)

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> "DriverPlatformInterface":
        """Configure VPE driver."""
        number = str(number)
        if number not in self._known_coils:
            self.raise_config_error("Coil {} is not known to VPE".format(number), 2)
        return VisualPinballEvolutionDriver(config, number, self)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Pulse on hit and hold."""
        command = self.platform_rpc.ConfigureHardwareRule(ConfigureHardwareRuleRequest(
            coil_number=coil.hw_driver.number,
            switch_number=enable_switch.hw_switch.number,
            pulse_ms=coil.pulse_settings.duration,
            pulse_power=coil.pulse_settings.power,
            hold_power=coil.hold_settings.power
        ))
        self.send_command(command)

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings, eos_switch: SwitchSettings,
                                                      coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Pulse on hit, disable on disable_switch hit."""
        del eos_switch, repulse_settings
        command = self.platform_rpc.ConfigureHardwareRule(ConfigureHardwareRuleRequest(
            coil_number=coil.hw_driver.number,
            switch_number=enable_switch.hw_switch.number,
            pulse_ms=coil.pulse_settings.duration,
            pulse_power=coil.pulse_settings.power,
            hold_power=0.0
        ))
        self.send_command(command)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Pulse on hit and hold, disable on disable_switch hit."""
        command = self.platform_rpc.ConfigureHardwareRule(ConfigureHardwareRuleRequest(
            coil_number=coil.hw_driver.number,
            switch_number=enable_switch.hw_switch.number,
            pulse_ms=coil.pulse_settings.duration,
            pulse_power=coil.pulse_settings.power,
            hold_power=coil.hold_settings.power
        ))
        self.send_command(command)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Pulse on hit."""
        command = self.platform_rpc.ConfigureHardwareRule(ConfigureHardwareRuleRequest(
            coil_number=coil.hw_driver.number,
            switch_number=enable_switch.hw_switch.number,
            pulse_ms=coil.pulse_settings.duration,
            pulse_power=coil.pulse_settings.power,
            hold_power=0.0
        ))
        self.send_command(command)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings,
                              coil: DriverSettings):
        """Pulse on hit and release."""
        command = self.platform_rpc.ConfigureHardwareRule(ConfigureHardwareRuleRequest(
            coil_number=coil.hw_driver.number,
            switch_number=enable_switch.hw_switch.number,
            pulse_ms=coil.pulse_settings.duration,
            pulse_power=coil.pulse_settings.power,
            hold_power=0.0
        ))
        self.send_command(command)

    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """Clear hw rule."""
        command = self.platform_rpc.RemoveHardwareRule(RemoveHardwareRuleRequest(
            coil_number=coil.hw_driver.number,
            switch_number=switch.hw_switch.number,
        ))
        self.send_command(command)

    async def get_hw_switch_states(self):
        """Return initial switch state."""
        return self._initial_switch_state

    def configure_light(self, number: str, subtype: str, platform_settings: dict) -> "LightPlatformInterface":
        """Configure a VPE light."""
        if not subtype:
            subtype = "light"
        number = "{}-{}".format(subtype, number)
        if number not in self._known_lights:
            self.raise_config_error("Light {} is not known to VPE".format(number), 3)
        return VisualPinballEvolutionLight(number, self)

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse channel str to a list of channels."""
        return [
            {
                "number": str(number)
            }
        ]
