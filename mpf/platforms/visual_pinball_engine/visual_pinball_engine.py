"""VPE platform."""
import asyncio
from typing import Optional, List

from mpf.core.segment_mappings import TextToSegmentMapper, FOURTEEN_SEGMENTS
from mpf.devices.segment_display.segment_display_text import ColoredSegmentDisplayText
from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplaySoftwareFlashPlatformInterface
from mpf.platforms.visual_pinball_engine.platform_pb2 import SetSegmentDisplayFrameRequest

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.core.platform import LightsPlatform, SwitchPlatform, DriverPlatform, SwitchSettings, DriverSettings, \
    SwitchConfig, DriverConfig, RepulseSettings, RgbDmdPlatform, DmdPlatform, SegmentDisplayPlatform
from mpf.platforms.visual_pinball_engine import platform_pb2_grpc
from mpf.platforms.visual_pinball_engine import platform_pb2

try:
    from mpf.platforms.visual_pinball_engine.service import MpfHardwareService
except (SyntaxError, ImportError):
    # pylint: disable-msg=invalid-name
    MpfHardwareService = None

try:
    from grpc.experimental import aio   # pylint: disable-msg=import-error
except ImportError:
    aio = None


class VisualPinballEngineSwitch(SwitchPlatformInterface):

    """A switch in VPE."""

    def __init__(self, config, number, platform):
        """initialize switch."""
        super().__init__(config, number, platform)
        self.state = self.config.invert

    def get_board_name(self):
        """Return the name of the board of this switch."""
        return "VPE"


class VisualPinballEngineLight(LightPlatformInterface):

    """A light in VPE."""

    __slots__ = ["platform", "clock", "config"]

    def __init__(self, number, platform, config):
        """initialize LED."""
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
        """initialize virtual driver to disabled."""
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

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and enable the coil for an explicit duration."""
        raise NotImplementedError


class VisualPinballEngineDmd(DmdPlatformInterface):

    """VPE DMD."""

    __slots__ = ["data", "brightness", "platform", "name", "color_mapping", "width", "height"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, name, platform, color_mapping, width, height) -> None:
        """initialize virtual DMD."""
        self.data = None        # type: Optional[bytes]
        self.brightness = 1.0   # type: Optional[float]
        self.name = name
        self.platform = platform
        self.width = width
        self.height = height
        self.color_mapping = color_mapping

    def update(self, data: bytes):
        """Update data on the DMD.

        Args:
        ----
            data: bytes to send to DMD
        """
        if data != self.data:
            self.data = data
            self._send_frame()

    def _send_frame(self):
        command = platform_pb2.Commands()
        command.dmd_frame_request.name = self.name
        command.dmd_frame_request.frame = self.data
        command.dmd_frame_request.brightness = self.brightness
        self.platform.send_command(command)

    def set_brightness(self, brightness: float):
        """Set brightness."""
        self.brightness = brightness
        if self.data is not None:
            self._send_frame()


class VisualPinballEngineSegmentDisplay(SegmentDisplaySoftwareFlashPlatformInterface):

    """VPE segment display."""

    __slots__ = ["platform", "length_of_display"]

    def __init__(self, number, display_size, platform):
        """initialize segment display."""
        super().__init__(number)
        self.platform = platform
        self.length_of_display = display_size

    def _set_text(self, text: ColoredSegmentDisplayText) -> None:
        """Set text to VPE segment displays."""
        assert not text.embed_commas
        mapping = TextToSegmentMapper.map_segment_text_to_segments(text, self.length_of_display, FOURTEEN_SEGMENTS)
        result = map(lambda x: x.get_vpe_encoding(), mapping)
        command = platform_pb2.Commands()
        command.segment_display_frame_request.name = self.number
        command.segment_display_frame_request.frame = b''.join(result)
        command.segment_display_frame_request.colors.extend(
            [SetSegmentDisplayFrameRequest.SegmentDisplayColor(r=color.red / 255.0,
                                                               b=color.blue / 255.0,
                                                               g=color.green / 255.0)
             for color in text.get_colors()])

        self.platform.send_command(command)


class VisualPinballEnginePlatform(LightsPlatform, SwitchPlatform, DriverPlatform, RgbDmdPlatform, DmdPlatform,
                                  SegmentDisplayPlatform):

    """VPE platform."""

    __slots__ = ["config", "_configured_switches", "_configured_lights", "_configured_coils", "_initial_switch_state",
                 "_switch_poll_task", "platform_rpc", "platform_server", "_configured_dmds",
                 "_configured_segment_displays"]

    def __init__(self, machine):
        """initialize VPE platform."""
        super().__init__(machine)
        self.config = self.machine.config_validator.validate_config("vpe", self.machine.config.get('vpe', {}))
        self._configure_device_logging_and_debug("VPE Platform", self.config)
        self._initial_switch_state = {}
        self._configured_coils = []     # type: List[VisualPinballEngineDriver]
        self._configured_switches = []  # type: List[VisualPinballEngineSwitch]
        self._configured_lights = []    # type: List[VisualPinballEngineLight]
        self._configured_dmds = []      # type: List[VisualPinballEngineDmd]
        self._configured_segment_displays = []  # type: List[VisualPinballEngineSegmentDisplay]
        self._switch_poll_task = None
        self.platform_rpc = None        # type: Optional[MpfHardwareService]
        self.platform_server = None

        if not aio:
            raise AssertionError("Please install mpf with the VPE feature.")

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

    def get_configured_dmds(self):
        """Return configured dmds."""
        return self._configured_dmds

    def get_configured_segment_displays(self):
        """Return configured segment displays."""
        return self._configured_segment_displays

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
        self._switch_poll_task = asyncio.create_task(self._switch_poll())
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

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> VisualPinballEngineSwitch:
        """Configure VPE switch."""
        number = str(number)
        switch = VisualPinballEngineSwitch(config, number, self)
        self._configured_switches.append(switch)
        return switch

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> VisualPinballEngineDriver:
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

    def configure_light(self, number: str, subtype: str, config, platform_settings: dict) -> VisualPinballEngineLight:
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

    def configure_rgb_dmd(self, name: str):
        """Configure RGB dmd."""
        dmd = VisualPinballEngineDmd(platform=self, name=name, color_mapping="RGB", width=128, height=32)
        self._configured_dmds.append(dmd)
        return dmd

    def configure_dmd(self):
        """Configure dmd."""
        dmd = VisualPinballEngineDmd(platform=self, name="default", color_mapping="BW", width=128, height=32)
        self._configured_dmds.append(dmd)
        return dmd

    async def configure_segment_display(self, number: str, display_size: int,
                                        platform_settings) -> VisualPinballEngineSegmentDisplay:
        """Configure segment display."""
        segment_display = VisualPinballEngineSegmentDisplay(number, display_size, self)
        self._configured_segment_displays.append(segment_display)
        return segment_display
