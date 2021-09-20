"""VPE simulator.

This needs to be in a separate file so that we can handle syntax errors for python <= 3.5.
"""

import asyncio
from mpf.platforms.visual_pinball_engine import platform_pb2


class VpeSimulation:

    def __init__(self, switches):
        self.switches = switches
        self.change_queue = None
        self.lights = {}
        self.coils = {}
        self.rules = {}
        self.dmd_frames = {}
        self.segment_displays = {}
        self._command_task = None
        self._switch_task = None

    def init_async(self):
        self.change_queue = asyncio.Queue()

    async def connect(self, service):
        configuration = platform_pb2.MachineState(
            initial_switch_states=self.switches)
        command_stream = service.Start(configuration, None)
        self._command_task = asyncio.ensure_future(self.read_commands(command_stream))
        self._switch_task = asyncio.ensure_future(service.SendSwitchChanges(self.switch_changes(), None))

    def stop(self):
        self._command_task.cancel()
        self._switch_task.cancel()

    async def switch_changes(self):
        while True:
            changed_switch = await self.change_queue.get()
            yield platform_pb2.SwitchChanges(switch_number=changed_switch[0], switch_state=changed_switch[1])

    async def read_commands(self, stream):
        async for command in stream:
            variant = command.WhichOneof("command")
            if variant == "fade_light":
                self.handle_fade_light(command.fade_light)
            elif variant == "pulse_coil":
                self.handle_pulse(command.pulse_coil)
            elif variant == "enable_coil":
                self.handle_enable(command.enable_coil)
            elif variant == "disable_coil":
                self.handle_disable(command.disable_coil)
            elif variant == "configure_hardware_rule":
                self.handle_rule(command.configure_hardware_rule)
            elif variant == "remove_hardware_rule":
                self.handle_rule_remove(command.remove_hardware_rule)
            elif variant == "dmd_frame_request":
                self.handle_dmd_frame_request(command.dmd_frame_request)
            elif variant == "segment_display_frame_request":
                self.handle_segment_display_frame_request(command.segment_display_frame_request)
            else:
                raise AssertionError("Not implemented {}".format(variant))

    def set_switch(self, switch, state):
        self.switches[switch] = state
        self.change_queue.put_nowait((switch, state))

    def handle_fade_light(self, request):
        for fade in request.fades:
            if request.common_fade_ms > 0:
                self.lights[fade.light_number] = (asyncio.get_event_loop().time() +
                                                  (request.common_fade_ms / 1000.0), fade.target_brightness)
            else:
                self.lights[fade.light_number] = fade.target_brightness

    def handle_pulse(self, request):
        self.coils[request.coil_number] = "pulsed-{}-{}".format(request.pulse_ms, request.pulse_power)

    def handle_enable(self, request):
        self.coils[request.coil_number] = "enabled-{}-{}-{}".format(request.pulse_ms, request.pulse_power, request.hold_power)

    def handle_disable(self, request):
        self.coils[request.coil_number] = "disabled"

    def handle_rule(self, request):
        self.rules["{}-{}".format(request.coil_number, request.switch_number)] = request

    def handle_rule_remove(self, request):
        del self.rules["{}-{}".format(request.coil_number, request.switch_number)]

    def handle_dmd_frame_request(self, request):
        self.dmd_frames[request.name] = (request.frame, request.brightness)

    def handle_segment_display_frame_request(self, request):
        self.segment_displays[request.name] = (request.frame, request.colors)
