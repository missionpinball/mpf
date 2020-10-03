import sys

from functools import partial

import asyncio
import grpc

import mpf.platforms.visual_pinball_evolution.visual_pinball_evolution
from mpf.platforms.visual_pinball_evolution import platform_pb2_grpc
from mpf.platforms.visual_pinball_evolution.coils_pb2 import ConfigureHardwareRuleRequest
from mpf.platforms.visual_pinball_evolution.get_plaform_details_pb2 import GetPlatformDetailsResponse
from mpf.platforms.visual_pinball_evolution.switch_pb2 import SwitchChanges

from mpf.tests.MpfTestCase import MpfTestCase

try:
    class VpeSimulation(platform_pb2_grpc.HardwarePlatformServicer):

        def __init__(self, switches):
            self.switches = switches
            self.change_queue = None
            self.lights = {}
            self.coils = {}
            self.rules = {}

        def init_async(self):
            self.change_queue = asyncio.Queue()

        async def GetPlatformDetails(self, request, context):
            return GetPlatformDetailsResponse(
                known_switches_with_initial_state=self.switches,
                known_lights=["light-0", "light-1"],
                known_coils=["0", "1", "2"])

        def set_switch(self, switch, state):
            self.switches[switch] = state
            self.change_queue.put_nowait((switch, state))

        async def GetSwitchChanges(self, request, context):
            while True:
                changed_switch = await self.change_queue.get()
                yield SwitchChanges(switch_number=changed_switch[0], switch_state=changed_switch[1])

        async def LightFade(self, request, context):
            for fade in request.fades:
                if request.common_fade_ms > 0:
                    self.lights[fade.light_number] = (asyncio.get_event_loop().time() +
                                                      (request.common_fade_ms / 1000.0), fade.target_brightness)
                else:
                    self.lights[fade.light_number] = fade.target_brightness

        async def CoilPulse(self, request, context):
            self.coils[request.coil_number] = "pulsed-{}-{}".format(request.pulse_ms, request.pulse_power)

        async def CoilEnable(self, request, context):
            self.coils[request.coil_number] = "enabled-{}-{}-{}".format(request.pulse_ms, request.pulse_power, request.hold_power)

        async def CoilDisable(self, request, context):
            self.coils[request.coil_number] = "disabled"

        async def ConfigureHardwareRule(self, request, context):
            self.rules["{}-{}".format(request.coil_number, request.switch_number)] = request

        async def RemoveHardwareRule(self, request, context):
            del self.rules["{}-{}".format(request.coil_number, request.switch_number)]
except SyntaxError:
    # python 3.5 and earlier will fail to parse this code
    pass


class GrpcAsyncTestChannel(grpc.Channel):

    def __init__(self, simulator):
        super().__init__()
        self.simulator = simulator

    def _get_method(self, method):
        parts = method.split("/")
        assert len(parts) == 3
        return getattr(self.simulator, parts[2])

    def subscribe(self, callback, try_to_connect=False):
        pass

    def unsubscribe(self, callback):
        pass

    def _async_call(self, method, request):
        return method(request=request, context=[])

    def _async_stream_call(self, method, request):
        coroutine = method(request=request, context=[])
        print(coroutine)
        class Stream:
            def read(self):
                return coroutine.__anext__()

        return Stream()

    def unary_unary(self, method, request_serializer=None, response_deserializer=None):
        method = self._get_method(method)
        return partial(self._async_call, method)

    def unary_stream(self, method, request_serializer=None, response_deserializer=None):
        method = self._get_method(method)
        return partial(self._async_stream_call, method)

    def stream_unary(self, method, request_serializer=None, response_deserializer=None):
        print(method)
        return method()

    def stream_stream(self, method, request_serializer=None, response_deserializer=None):
        pass

    def close(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestVPE(MpfTestCase):


    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/vpe/'

    async def _connect_to_mock_server(self, host, port):
        channel = GrpcAsyncTestChannel(self.simulator)
        return platform_pb2_grpc.HardwarePlatformStub(channel)

    def _mock_loop(self):
        self.simulator.init_async()

    def setUp(self):
        if sys.version_info < (3, 6):
            self.skipTest("Test requires Python 3.6+")
            return

        self.simulator = VpeSimulation({"0": True, "3": False, "6": False})
        mpf.platforms.visual_pinball_evolution.visual_pinball_evolution.VisualPinballEvolutionPlatform.connect = self._connect_to_mock_server
        super().setUp()

    def get_platform(self):
        return False

    def test_vpe(self):
        self.assertSwitchState("s_sling", True)
        self.assertSwitchState("s_flipper", False)
        self.assertSwitchState("s_test", False)
        self.simulator.set_switch("6", True)
        self.advance_time_and_run(.1)
        self.assertSwitchState("s_test", True)

        self.simulator.set_switch("6", False)
        self.advance_time_and_run(.1)
        self.assertSwitchState("s_test", False)

        self.machine.lights["test_light1"].color("CCCCCC")
        self.advance_time_and_run(.1)
        self.assertAlmostEqual(0.8, self.simulator.lights["light-0"])

        self.machine.coils["c_flipper"].pulse()
        self.advance_time_and_run(.1)
        self.assertEqual("pulsed-10-1.0", self.simulator.coils["1"])

        self.machine.coils["c_flipper"].enable()
        self.advance_time_and_run(.1)
        self.assertEqual("enabled-10-1.0-1.0", self.simulator.coils["1"])

        self.machine.coils["c_flipper"].disable()
        self.advance_time_and_run(.1)
        self.assertEqual("disabled", self.simulator.coils["1"])

        self.machine.flippers["f_test"].enable()
        self.advance_time_and_run(.1)
        self.assertEqual(ConfigureHardwareRuleRequest(
            coil_number="1", switch_number="3", pulse_ms=10, pulse_power=1.0, hold_power=1.0),
            self.simulator.rules["1-3"])

        self.machine.flippers["f_test"].disable()
        self.advance_time_and_run(.1)
        self.assertNotIn("1-3", self.simulator.rules)
