"""Test the virtual segment display connector plugin."""
from unittest.mock import patch, call, ANY

from mpf.core.rgb_color import RGBColor
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType
from mpf.tests.MpfBcpTestCase import MpfBcpTestCase


class TestVirtualSegmentDisplayConnector(MpfBcpTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        # remove config patch which disables bcp
        self.machine_config_patches['bcp'] = \
            {"connections": {"local_display": {"type": "mpf.tests.test_BcpMc.TestBcpClient"}}}
        self.machine_config_patches['bcp']['servers'] = []

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/virtual_segment_display_connector/'

    def setUp(self):
        self.machine_config_patches['mpf']['plugins'] = [
            'mpf.plugins.virtual_segment_display_connector.VirtualSegmentDisplayConnector']
        super().setUp()

    def get_use_bcp(self):
        return True

    @patch("mpf.core.bcp.bcp_interface.BcpInterface.bcp_trigger_client")
    def test_plugin(self, mock_bcp_trigger_client):
        client = self.machine.bcp.transport.get_named_client("local_display")
        self.assertIsNotNone(client)
        self.machine.bcp.interface.add_registered_trigger_event_for_client(client, 'update_segment_display')
        self.advance_time_and_run()

        display1 = self.machine.segment_displays["display1"]
        display2 = self.machine.segment_displays["display2"]
        display3 = self.machine.segment_displays["display3"]  # Should not have virtual connector set

        self.assertIsNotNone(display1.virtual_connector)
        self.assertIsNotNone(display2.virtual_connector)
        self.assertIsNone(display3.virtual_connector)

        display1.add_text("NEW TEXT")
        display1.set_color(RGBColor("FF0000"))
        self.assertTrue(mock_bcp_trigger_client.called)
        mock_bcp_trigger_client.assert_has_calls([call(client=ANY, flashing=FlashingType.NO_FLASH,
                                                       name='update_segment_display', segment_display_name='display1',
                                                       text='NEW TEXT'),
                                                  call(client=ANY, name='update_segment_display',
                                                       segment_display_name='display1', color=["ff0000"])])
        mock_bcp_trigger_client.reset_mock()

        display2.add_text("OTHER TEXT")
        display2.set_flashing(FlashingType.FLASH_ALL)
        self.assertTrue(mock_bcp_trigger_client.called)
        mock_bcp_trigger_client.assert_has_calls([call(client=ANY, flashing=FlashingType.NO_FLASH,
                                                       name='update_segment_display', segment_display_name='display2',
                                                       text='OTHER TEXT'),
                                                  call(client=ANY, flashing=FlashingType.FLASH_ALL,
                                                       name='update_segment_display', segment_display_name='display2',
                                                       text='OTHER TEXT')
                                                  ])
        mock_bcp_trigger_client.reset_mock()

        display3.add_text("IGNORED")
        self.assertFalse(mock_bcp_trigger_client.called)
