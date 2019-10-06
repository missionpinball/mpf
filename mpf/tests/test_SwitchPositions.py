"""Test Switch Position Mixin."""
from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestSwitchPositions(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/switch_player/'

    def test_switch_positions(self):
        switch1 = self.machine.switches["s_test1"]
        switch2 = self.machine.switches["s_test2"]
        switch3 = self.machine.switches["s_test3"]

        self.assertEqual(switch1.x, 0.4)
        self.assertEqual(switch1.y, 0.5)
        self.assertEqual(switch1.z, 0)

        self.assertEqual(switch2.x, 0.6)
        self.assertEqual(switch2.y, 0.7)
        self.assertEqual(switch2.z, None)

        self.assertEqual(switch3.x, None)
        self.assertEqual(switch3.y, None)
        self.assertEqual(switch3.z, None)
