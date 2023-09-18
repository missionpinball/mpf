"""MPF Hardware Service for VPE.

This is separated from the platform because we need to catch a syntax error in python 3.5 and earlier.
"""
import asyncio
from mpf.platforms.visual_pinball_engine import platform_pb2_grpc
from mpf.platforms.visual_pinball_engine import platform_pb2


class MpfHardwareService(platform_pb2_grpc.MpfHardwareServiceServicer):

    """MPF Service for VPE."""

    __slots__ = ["machine", "platform", "switch_queue", "command_queue", "_started"]

    def __init__(self, machine, platform):
        """initialize MPF service for VPE."""
        self._connected = asyncio.Future()
        self.machine = machine
        self.platform = platform
        self.switch_queue = asyncio.Queue()
        self.command_queue = asyncio.Queue()
        self._started = asyncio.Future()

    def send_command(self, command):
        """Send command to VPE."""
        self.command_queue.put_nowait(command)

    def get_switch_queue(self):
        """Return switch queue."""
        return self.switch_queue

    async def wait_for_vpe_connect(self):
        """Wait until VPE has connected."""
        return await self._connected

    def set_ready(self):
        """Mark service as ready."""
        self._started.set_result(True)

    async def Start(self, request, context):    # noqa
        """Start MPF."""
        self._connected.set_result(request)
        while True:
            command = await self.command_queue.get()
            # this only works in Python 3.6+
            yield command

    async def GetMachineDescription(self, request, context):    # noqa
        """Get Platform Configuration of VPE platform."""
        switches = []
        await self._started
        for switch in self.platform.get_configured_switches():
            switch_description = platform_pb2.SwitchDescription()
            switch_description.name = switch.config.name
            switch_description.hardware_number = switch.number
            switch_description.switch_type = "NC" if switch.config.invert else "NO"
            switches.append(switch_description)

        coils = []
        for coil in self.platform.get_configured_coils():
            coil_description = platform_pb2.CoilDescription()
            coil_description.name = coil.config.name
            coil_description.hardware_number = coil.number
            coils.append(coil_description)

        lights = []
        for light in self.platform.get_configured_lights():
            light_description = platform_pb2.LightDescription()
            light_description.name = light.config.name
            light_description.hardware_channel_number = light.number
            light_description.hardware_channel_color = light.config.color.name
            lights.append(light_description)

        dmds = []
        for dmd in self.platform.get_configured_dmds():
            dmd_description = platform_pb2.DmdDescription()
            dmd_description.name = dmd.name
            if dmd.color_mapping == "RGB":
                dmd_description.color_mapping = platform_pb2.DmdDescription.ColorMapping.RGB
            elif dmd.color_mapping == "BW":
                dmd_description.color_mapping = platform_pb2.DmdDescription.ColorMapping.BW
            else:
                raise AssertionError("Invalid color mapping {}".format(dmd.color_mapping))

            dmd_description.height = dmd.height
            dmd_description.width = dmd.width
            dmds.append(dmd_description)

        segment_displays = []
        for segment_display in self.platform.get_configured_segment_displays():
            segment_display_description = platform_pb2.SegmentDisplayDescription()
            segment_display_description.name = segment_display.number
            segment_display_description.width = segment_display.length_of_display
            segment_displays.append(segment_display_description)

        machine_description = platform_pb2.MachineDescription(switches=switches, coils=coils, lights=lights, dmds=dmds,
                                                              segment_displays=segment_displays)

        return machine_description

    async def SendSwitchChanges(self, request_iterator, context):   # noqa
        """Process a stream of switches."""
        async for element in request_iterator:
            self.switch_queue.put_nowait(element)

        return platform_pb2.EmptyResponse()

    async def Quit(self, request, context):     # noqa
        """Stop MPF."""
        self.machine.stop(reason="VPE exited.")
        return platform_pb2.EmptyResponse()
