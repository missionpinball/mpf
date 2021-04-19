import sys

from mpf.tests.MpfTestCase import MpfTestCase, MagicMock, patch


class MockServer:

    async def stop(self, grace):
        pass

    async def wait_for_termination(self):
        pass


class TestVPE(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/vpe/'

    async def _connect_to_mock_client(self, service, port):
        self.service = service
        await self.simulator.connect(self.service)
        return MockServer()

    def _mock_loop(self):
        self.simulator.init_async()

    def setUp(self):
        if sys.version_info < (3, 6):
            self.skipTest("Test requires Python 3.6+")
            return

        try:
            from mpf.tests.vpe_simulator import VpeSimulation
            from mpf.platforms.visual_pinball_engine import platform_pb2
        except (SyntaxError, ImportError) as e:
            self.skipTest("Cannot import VPE simulator because {}".format(e))
            return

        self.simulator = VpeSimulation({"0": True, "3": False, "6": False})
        import mpf.platforms.visual_pinball_engine.visual_pinball_engine
        mpf.platforms.visual_pinball_engine.visual_pinball_engine.VisualPinballEnginePlatform.listen = self._connect_to_mock_client
        super().setUp()

    def get_platform(self):
        return False

    def test_vpe(self):
        from mpf.platforms.visual_pinball_engine import platform_pb2
        description = self.loop.run_until_complete(
            self.service.GetMachineDescription(platform_pb2.EmptyRequest(), None))
        self.assertEqual(len(description.switches), 3)
        self.assertEqual(len(description.coils), 3)
        self.assertEqual(len(description.lights), 2)

        self.assertTrue(platform_pb2.SwitchDescription(
            name="s_sling",
            hardware_number="0",
            switch_type="NO",
        ) in description.switches)

        self.assertTrue(platform_pb2.CoilDescription(
            name="c_flipper",
            hardware_number="1"
        ) in description.coils)

        self.assertTrue(platform_pb2.LightDescription(
            name="test_light1",
            hardware_channel_number="light-0",
            hardware_channel_color="WHITE"
        ) in description.lights)

        self.assertTrue(platform_pb2.DmdDescription(
            name="default",
            color_mapping=platform_pb2.DmdDescription.ColorMapping.BW,
            width=128,
            height=32
        ) in description.dmds)

        self.assertTrue(platform_pb2.DmdDescription(
            name="test_dmd",
            color_mapping=platform_pb2.DmdDescription.ColorMapping.RGB,
            width=128,
            height=32
        ) in description.dmds)

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
        self.assertEqual(platform_pb2.ConfigureHardwareRuleRequest(
            coil_number="1", switch_number="3", pulse_ms=10, pulse_power=1.0, hold_power=1.0),
            self.simulator.rules["1-3"])

        self.machine.flippers["f_test"].disable()
        self.advance_time_and_run(.1)
        self.assertNotIn("1-3", self.simulator.rules)

        # test set frame to buffer
        frame = bytearray()
        for i in range(4096):
            frame.append(i % 256)

        self.machine.dmds["default"].update(bytes(frame))
        self.advance_time_and_run(.1)

        self.assertEqual((frame, 1.0), self.simulator.dmd_frames["default"])

        rgb_frame = bytearray()
        for i in range(128 * 32 * 3):
            rgb_frame.append(i % 256)

        self.machine.rgb_dmds["test_dmd"].update(bytes(rgb_frame))
        self.advance_time_and_run(.1)

        self.assertEqual((rgb_frame, 1.0), self.simulator.dmd_frames["test_dmd"])
