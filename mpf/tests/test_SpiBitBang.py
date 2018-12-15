import asyncio

from mpf.tests.MpfTestCase import MpfTestCase, MagicMock


class TestSpiBigBang(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/spi_bit_bang/'

    def get_platform(self):
        # no force platform
        return False

    def test_spi_bit_bang(self):

        # wait for o_cs low
        for i in range(100):
            if self.machine.digital_outputs["o_cs"].hw_driver.state == "enabled":
                break
            self.advance_time_and_run(.025)
        else:
            self.fail("Did not find o_cs high")
        self.machine.digital_outputs["o_clock"].hw_driver.pulse = MagicMock()
        # set bit 7
        self.hit_switch_and_run("s_miso", .05)
        self.assertEqual(1, self.machine.digital_outputs["o_clock"].hw_driver.pulse.call_count)
        # unset bit 6
        self.release_switch_and_run("s_miso", .05)
        self.assertEqual(2, self.machine.digital_outputs["o_clock"].hw_driver.pulse.call_count)
        # unset bit 5
        self.release_switch_and_run("s_miso", .05)
        self.assertEqual(3, self.machine.digital_outputs["o_clock"].hw_driver.pulse.call_count)
        # set bit 4
        self.hit_switch_and_run("s_miso", .05)
        self.assertEqual(4, self.machine.digital_outputs["o_clock"].hw_driver.pulse.call_count)
        # set bit 3
        self.hit_switch_and_run("s_miso", .05)
        self.assertEqual(5, self.machine.digital_outputs["o_clock"].hw_driver.pulse.call_count)
        # set bit 2
        self.hit_switch_and_run("s_miso", .05)
        self.assertEqual(6, self.machine.digital_outputs["o_clock"].hw_driver.pulse.call_count)
        # unset bit 1
        self.release_switch_and_run("s_miso", .05)
        self.assertEqual(7, self.machine.digital_outputs["o_clock"].hw_driver.pulse.call_count)
        # set bit 0
        self.hit_switch_and_run("s_miso", .05)
        self.assertEqual(8, self.machine.digital_outputs["o_clock"].hw_driver.pulse.call_count)
        self.advance_time_and_run(.1)

        self.assertSwitchState("s_trough_0", True)
        self.assertSwitchState("s_trough_1", False)
        self.assertSwitchState("s_trough_2", True)
        self.assertSwitchState("s_trough_3", True)
        self.assertSwitchState("s_trough_4", True)
        self.assertSwitchState("s_trough_5", False)
        self.assertSwitchState("s_trough_6", False)
        self.assertSwitchState("s_trough_7", True)

