"""Test MpfMcSegmentDisplayEmulator Platform."""
from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfBcpTestCase import MpfBcpTestCase
from mpf.tests.MpfTestCase import MpfTestCase


class TestMpfMcSegmentDisplayEmulatorPlatform(MpfBcpTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/mpfmc_segment_display_emulator/'

    def get_platform(self):
        return False

    def testSegmentDisplay(self):
        # Test triggers and the trigger player which is used to send trigger messages from MPF over BCP
        client = self.machine.bcp.transport.get_named_client("local_display")
        self.assertIsNotNone(client)

        self.machine.segment_displays["display1"].add_text("1337", key="score")
        self.advance_time_and_run()
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(("trigger", {"name": "update_segment_display_1_text", "text": "1337"}), queue)

        self.machine.segment_displays["display1"].set_color(RGBColor("FF0000"))
        self.advance_time_and_run()
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(("trigger", {"name": "update_segment_display_1_color", "color": RGBColor("FF0000")}), queue)

    def testSegmentDisplayPlayer(self):
        client = self.machine.bcp.transport.get_named_client("local_display")
        self.assertIsNotNone(client)

        self.machine.events.post("update_display2")
        self.advance_time_and_run()
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(("trigger", {"name": "update_segment_display_2_text", "text": "NEW TEXT"}), queue)
