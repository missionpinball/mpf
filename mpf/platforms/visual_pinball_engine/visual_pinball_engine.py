"""VPE platform."""
from typing import Optional

from grpc.experimental import aio

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.core.platform import LightsPlatform, SwitchPlatform, DriverPlatform, SwitchSettings, DriverSettings, \
    SwitchConfig, DriverConfig, RepulseSettings
from mpf.platforms.visual_pinball_engine import platform_pb2_grpc
from mpf.platforms.visual_pinball_engine import platform_pb2

try:
    from mpf.platforms.visual_pinball_engine.service import MpfHardwareService
except SyntaxError:
    # pylint: disable-msg=invalid-name
    MpfHardwareService = None


class VisualPinballEngineSwitch(SwitchPlatformInterface):

    """A switch in VPE."""

    def __init__(self, config, number):
        """Initialise switch."""
        super().__init__(config, number)
        self.state = self.config.invert

    def get_board_name(self):
        """Return the name of the board of this switch."""
        return "VPE"


class VisualPinballEngineLight(LightPlatformInterface):

    """A light in VPE."""

    __slots__ = ["platform", "clock", "config"]

    def __init__(self, number, platform, config):
        """Initialise LED."""
        super().__init__(number)
        self.platform = platform    # type: VisualPinballEnginePlatform
        self.clock = self.platform.machine.clock
        self.config = config

    def set_fade(self, start_brightness, start_time, target_brightness, target_time):
        """Set fade."""
        # TODO: batch all fades
        current_time = self.clock.get_time()
        if target_time > 0:
            fade_ms = int((target_time - current_time) * 1000)
        else:
            fade_ms = 0

        command = platform_pb2.Commands()
        command.fade_light.common_fade_ms = fade_ms
        command.fade_light.fades.append(platform_pb2.FadeLightRequest.ChannelFade(
            light_number=self.number,
            target_brightness=target_brightness))
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


class VisualPinballEngineDriver(DriverPlatformInterface):

    """A driver in VPE."""

    __slots__ = ["platform"]

    def __init__(self, config, number, platform):
        """Initialise virtual driver to disabled."""
        super().__init__(config, number)
        self.platform = platform    # type: VisualPinballEnginePlatform

    def get_board_name(self):
        """Return the name of the board of this driver."""
        return "VPE"

    def disable(self):
        """Disable virtual coil."""
        command = platform_pb2.Commands()
        command.disable_coil.coil_number = self.number
        self.platform.send_command(command)

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable virtual coil."""
        command = platform_pb2.Commands()
        command.enable_coil.coil_number = self.number
        command.enable_coil.pulse_ms = pulse_settings.duration
        command.enable_coil.pulse_power = pulse_settings.power
        command.enable_coil.hold_power = hold_settings.power
        self.platform.send_command(command)

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse virtual coil."""
        command = platform_pb2.Commands()
        command.pulse_coil.coil_number = self.number
        command.pulse_coil.pulse_ms = pulse_settings.duration
        command.pulse_coil.pulse_power = pulse_settings.power
        self.platform.send_command(command)


class VisualPinballEnginePlatform(LightsPlatform, SwitchPlatform, DriverPlatform):

    """VPE platform."""

    __slots__ = ["config", "_configured_switches", "_configured_lights", "_configured_coils", "_initial_switch_state",
                 "_switch_poll_task", "platform_rpc", "platform_server"]

    def __init__(self, machine):
        """Initialise VPE platform."""
        super().__init__(machine)
        self.config = self.machine.config_validator.validate_config("vpe", self.machine.config.get('vpe', {}))
        self._configure_device_logging_and_debug("VPE Platform", self.config)
        self._initial_switch_state = {}
        self._configured_coils = []
        self._configured_switches = []
        self._configured_lights = []
        self._switch_poll_task = None
        self.platform_rpc = None        # type: Optional[MpfHardwareService]
        self.platform_server = None

        if not MpfHardwareService:
            raise AssertionError("Error loading MpfHardwareService. Is your python version older than 3.6?")

    async def listen(self, service, port):
        """Connect to remote host and port."""
        server = aio.server()
        platform_pb2_grpc.add_MpfHardwareServiceServicer_to_server(service, server)
        listen_addr = "[::]:{}".format(port)
        server.add_insecure_port(listen_addr)
        self.log.info("Starting server on %s", listen_addr)
        await server.start()
        return server

    async def initialize(self):
        """Wait for incoming gRPC connect from VPE."""
        self.platform_rpc = MpfHardwareService(self.machine, self)
        self.platform_server = await self.listen(self.platform_rpc, self.config['listen_port'])
        response = await self.platform_rpc.wait_for_vpe_connect()
        self.info_log("VPE connected")
        self.debug_log("Got response %s", response)
        self._initial_switch_state = response.initial_switch_states

    def get_configured_switches(self):
        """Return configured switches."""
        return self._configured_switches

    def get_configured_coils(self):
        """Return configured coils."""
        return self._configured_coils

    def get_configured_lights(self):
        """Return configured lights."""
        return self._configured_lights

    def stop(self):
        """Stop VPE server."""
        if self._switch_poll_task:
            self._switch_poll_task.cancel()
            self._switch_poll_task = None

        if self.platform_server:
            self.machine.clock.loop.run_until_complete(self.platform_server.stop(1))
            self.machine.clock.loop.run_until_complete(self.platform_server.wait_for_termination())
            self.platform_server = None

    async def start(self):
        """Start listening for switch changes."""
        await super().start()
        self.platform_rpc.set_ready()
        self._switch_poll_task = self.machine.clock.loop.create_task(self._switch_poll())
        self._switch_poll_task.add_done_callback(Util.raise_exceptions)

    async def _switch_poll(self):
        """Listen to switch changes from VPE."""
        switch_stream = self.platform_rpc.get_switch_queue()
        while True:
            change = await switch_stream.get()
            if self._debug:
                self.debug_log("Got Switch Change: %s", change)
            self.machine.switch_controller.process_switch_by_num(state=1 if change.switch_state else 0,
                                                                 num=change.switch_number,
                                                                 platform=self)

    def send_command(self, command):
        """Send command to VPE."""
        self.platform_rpc.send_command(command)

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> "SwitchPlatformInterface":
        """Configure VPE switch."""
        number = str(number)
        switch = VisualPinballEngineSwitch(config, number)
        self._configured_switches.append(switch)
        return switch

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> "DriverPlatformInterface":
        """Configure VPE driver."""
        number = str(number)
        coil = VisualPinballEngineDriver(config, number, self)
        self._configured_coils.append(coil)
        return coil

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Pulse on hit and hold."""
        command = platform_pb2.Commands()
        command.configure_hardware_rule.coil_number = coil.hw_driver.number
        command.configure_hardware_rule.switch_number = enable_switch.hw_switch.number
        command.configure_hardware_rule.pulse_ms = coil.pulse_settings.duration
        command.configure_hardware_rule.pulse_power = coil.pulse_settings.power
        command.configure_hardware_rule.hold_power = coil.hold_settings.power
        self.send_command(command)

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings, eos_switch: SwitchSettings,
                                                      coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Pulse on hit, disable on disable_switch hit."""
        del eos_switch, repulse_settings
        command = platform_pb2.Commands()
        command.configure_hardware_rule.coil_number = coil.hw_driver.number
        command.configure_hardware_rule.switch_number = enable_switch.hw_switch.number
        command.configure_hardware_rule.pulse_ms = coil.pulse_settings.duration
        command.configure_hardware_rule.pulse_power = coil.pulse_settings.power
        command.configure_hardware_rule.hold_power = 0.0
        self.send_command(command)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Pulse on hit and hold, disable on disable_switch hit."""
        command = platform_pb2.Commands()
        command.configure_hardware_rule.coil_number = coil.hw_driver.number
        command.configure_hardware_rule.switch_number = enable_switch.hw_switch.number
        command.configure_hardware_rule.pulse_ms = coil.pulse_settings.duration
        command.configure_hardware_rule.pulse_power = coil.pulse_settings.power
        command.configure_hardware_rule.hold_power = coil.hold_settings.power
        self.send_command(command)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Pulse on hit."""
        command = platform_pb2.Commands()
        command.configure_hardware_rule.coil_number = coil.hw_driver.number
        command.configure_hardware_rule.switch_number = enable_switch.hw_switch.number
        command.configure_hardware_rule.pulse_ms = coil.pulse_settings.duration
        command.configure_hardware_rule.pulse_power = coil.pulse_settings.power
        command.configure_hardware_rule.hold_power = 0.0
        self.send_command(command)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings,
                              coil: DriverSettings):
        """Pulse on hit and release."""
        command = platform_pb2.Commands()
        command.configure_hardware_rule.coil_number = coil.hw_driver.number
        command.configure_hardware_rule.switch_number = enable_switch.hw_switch.number
        command.configure_hardware_rule.pulse_ms = coil.pulse_settings.duration
        command.configure_hardware_rule.pulse_power = coil.pulse_settings.power
        command.configure_hardware_rule.hold_power = 0.0
        self.send_command(command)

    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """Clear hw rule."""
        command = platform_pb2.Commands()
        command.remove_hardware_rule.coil_number = coil.hw_driver.number
        command.remove_hardware_rule.switch_number = switch.hw_switch.number
        self.send_command(command)

    async def get_hw_switch_states(self):
        """Return initial switch state."""
        return self._initial_switch_state

    def configure_light(self, number: str, subtype: str, config, platform_settings: dict) -> "LightPlatformInterface":
        """Configure a VPE light."""
        if not subtype:
            subtype = "light"
        number = "{}-{}".format(subtype, number)
        light = VisualPinballEngineLight(number, self, config)
        self._configured_lights.append(light)
        return light

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse channel str to a list of channels."""
        return [
            {
                "number": str(number)
            }
        ]
