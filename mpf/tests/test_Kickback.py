from unittest.mock import MagicMock

from mpf.platforms.interfaces.driver_platform_interface import PulseSettings

from mpf.core.platform import SwitchSettings, DriverSettings

from mpf.tests.MpfTestCase import MpfTestCase


class TestKickback(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/kickback/'

    def test_kickback_with_ball_save(self):
        self.machine.default_platform.set_pulse_on_hit_rule = MagicMock()
        self.mock_event("kickback_kickback_test_fired")
        self.assertFalse(self.machine.ball_saves.kickback_save.enabled)

        # kickback is not enabled. nothing should happen
        self.hit_and_release_switch("s_kickback")
        self.advance_time_and_run(.01)
        self.assertEventNotCalled("kickback_kickback_test_fired")

        # enable kickback
        self.post_event("kickback_enable")
        self.advance_time_and_run(.01)

        # should write a hw rule
        self.machine.default_platform.set_pulse_on_hit_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches.s_kickback.hw_switch, invert=False, debounce=False),
            DriverSettings(hw_driver=self.machine.coils.kickback_coil.hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=100), hold_settings=None, recycle=True)
        )

        # a hit should fire it
        self.hit_and_release_switch("s_kickback")
        self.advance_time_and_run(.01)
        self.assertEventCalled("kickback_kickback_test_fired")

        # ball save should be enabled just in case
        self.assertTrue(self.machine.ball_saves.kickback_save.enabled)

        # but disable after 6s
        self.advance_time_and_run(6.1)
        self.assertFalse(self.machine.ball_saves.kickback_save.enabled)

        # it only works once though
        self.mock_event("kickback_kickback_test_fired")
        self.hit_and_release_switch("s_kickback")
        self.advance_time_and_run(.01)
        self.assertEventNotCalled("kickback_kickback_test_fired")
