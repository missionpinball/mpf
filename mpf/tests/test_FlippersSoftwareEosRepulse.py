from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings

from mpf.core.platform import SwitchSettings, DriverSettings, RepulseSettings

from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock, call


class TestFlippersSoftwareEosRepulse(MpfTestCase):

    def get_config_file(self):
        return 'software_eos_repulse.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/flippers/'

    def get_platform(self):
        return 'virtual'

    def test_single_wound_flipper_with_software_eos_repulse(self):
        """Test software repulse behaviour.

        Assuming platform supports cut-off
        """
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse = MagicMock()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable = MagicMock()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable = MagicMock()

        # nothing should happen on EOS close without flipper button active
        self.hit_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # nothing should happen on EOS open without flipper button active
        self.release_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # flipper activation should also not yet do what
        self.hit_switch_and_run("s_flipper_single", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # EOS closes. nothing happens yet
        self.hit_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # EOS opens. nothing should happen as flipper is not enabled
        self.release_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # release flipper prior to enabling the flipper
        self.release_switch_and_run("s_flipper_single", 1)

        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule = MagicMock()
        self.assertPlaceholderEvaluates(False, "device.flippers.single_flipper.enabled")

        # enable flipper
        self.post_event("enable_flipper_single")
        self.assertPlaceholderEvaluates(True, "device.flippers.single_flipper.enabled")

        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule.
                                _mock_call_args_list))
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_flipper_single"].hw_switch, invert=False, debounce=False),
            SwitchSettings(hw_switch=self.machine.switches["s_flipper_single_eos"].hw_switch, invert=False,
                           debounce=False),
            DriverSettings(hw_driver=self.machine.coils["c_flipper_single_main"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=30),
                           hold_settings=HoldSettings(power=0.3), recycle=False),
            None    # this is not passed as we implement it in software
        )

        # nothing should happen on EOS close without flipper button active
        self.hit_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # nothing should happen on EOS open without flipper button active
        self.release_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # flipper activation should also not yet do what
        self.hit_switch_and_run("s_flipper_single", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # EOS closes. nothing happens yet
        self.hit_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # EOS opens. it should repulse
        self.release_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_called_with(
            PulseSettings(power=1.0, duration=30), HoldSettings(power=0.3))
        self.machine.coils["c_flipper_single_main"].hw_driver.enable = MagicMock()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # EOS closes only shortly
        self.hit_switch_and_run("s_flipper_single_eos", .1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # EOS opens. it should not repulse yet
        self.release_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # EOS closes. nothing happens yet
        self.hit_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # EOS opens. it should repulse
        self.release_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_called_with(
            PulseSettings(power=1.0, duration=30), HoldSettings(power=0.3))
        self.machine.coils["c_flipper_single_main"].hw_driver.enable = MagicMock()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # EOS closes. nothing happens yet
        self.hit_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # flipper button releases
        self.release_switch_and_run("s_flipper_single", 1)

        # eos opens - nothing should happen
        self.release_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_called_with()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable = MagicMock()

        # disable flipper
        self.post_event("disable_flipper_single")
        self.assertPlaceholderEvaluates(False, "device.flippers.single_flipper.enabled")

        # nothing should happen on EOS close without flipper button active
        self.hit_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # nothing should happen on EOS open without flipper button active
        self.release_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # flipper activation should also not yet do what
        self.hit_switch_and_run("s_flipper_single", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # EOS closes. nothing happens yet
        self.hit_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # EOS opens. nothing should happen as flipper is not enabled
        self.release_switch_and_run("s_flipper_single_eos", 1)
        self.machine.coils["c_flipper_single_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_single_main"].hw_driver.disable.assert_not_called()

        # release flipper prior to enabling the flipper
        self.release_switch_and_run("s_flipper_single", 1)

    def test_dual_wound_flipper_with_software_eos_repulse(self):
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse = MagicMock()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable = MagicMock()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable = MagicMock()

        # nothing should happen on EOS close without flipper button active
        self.hit_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # nothing should happen on EOS open without flipper button active
        self.release_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # flipper activation should also not yet do what
        self.hit_switch_and_run("s_flipper_dual_wound", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # EOS closes. nothing happens yet
        self.hit_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # EOS opens. nothing should happen as flipper is not enabled
        self.release_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # release flipper prior to enabling the flipper
        self.release_switch_and_run("s_flipper_dual_wound", 1)

        self.machine.default_platform.set_pulse_on_hit_and_release_and_disable_rule = MagicMock()
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule = MagicMock()
        self.assertPlaceholderEvaluates(False, "device.flippers.dual_wound_flipper.enabled")

        # enable flipper
        self.post_event("enable_flipper_dual_wound")
        self.assertPlaceholderEvaluates(True, "device.flippers.dual_wound_flipper.enabled")

        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_release_and_disable_rule.
                                _mock_call_args_list))
        self.assertEqual(1, len(self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.
                                _mock_call_args_list))
        self.machine.default_platform.set_pulse_on_hit_and_release_and_disable_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_flipper_dual_wound"].hw_switch, invert=False,
                           debounce=False),
            SwitchSettings(hw_switch=self.machine.switches["s_flipper_dual_wound_eos"].hw_switch, invert=False,
                           debounce=False),
            DriverSettings(hw_driver=self.machine.coils["c_flipper_dual_wound_main"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=30),
                           hold_settings=None, recycle=False),
            None    # this is not passed as we implement it in software
        )
        self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule.assert_called_once_with(
            SwitchSettings(hw_switch=self.machine.switches["s_flipper_dual_wound"].hw_switch, invert=False,
                           debounce=False),
            DriverSettings(hw_driver=self.machine.coils["c_flipper_dual_wound_hold"].hw_driver,
                           pulse_settings=PulseSettings(power=1.0, duration=10),
                           hold_settings=HoldSettings(power=1.0), recycle=False)
        )

        # nothing should happen on EOS close without flipper button active
        self.hit_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # nothing should happen on EOS open without flipper button active
        self.release_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # flipper activation should also not yet do what
        self.hit_switch_and_run("s_flipper_dual_wound", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # EOS closes. nothing happens yet
        self.hit_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # EOS opens. it should repulse
        self.release_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_called_with(
            PulseSettings(power=1.0, duration=30))
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse = MagicMock()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # EOS closes only shortly
        self.hit_switch_and_run("s_flipper_dual_wound_eos", .1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # EOS opens. it should not repulse yet
        self.release_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # EOS closes. nothing happens yet
        self.hit_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # EOS opens. it should repulse
        self.release_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_called_with(
            PulseSettings(power=1.0, duration=30))
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse = MagicMock()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # EOS closes. nothing happens yet
        self.hit_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # flipper button releases
        self.release_switch_and_run("s_flipper_dual_wound", 1)

        # eos opens - nothing should happen
        self.release_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_called_with()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable = MagicMock()

        # disable flipper
        self.post_event("disable_flipper_dual_wound")
        self.assertPlaceholderEvaluates(False, "device.flippers.dual_wound_flipper.enabled")

        # nothing should happen on EOS close without flipper button active
        self.hit_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # nothing should happen on EOS open without flipper button active
        self.release_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # flipper activation should also not yet do what
        self.hit_switch_and_run("s_flipper_dual_wound", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # EOS closes. nothing happens yet
        self.hit_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # EOS opens. nothing should happen as flipper is not enabled
        self.release_switch_and_run("s_flipper_dual_wound_eos", 1)
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.pulse.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.enable.assert_not_called()
        self.machine.coils["c_flipper_dual_wound_main"].hw_driver.disable.assert_not_called()

        # release flipper prior to enabling the flipper
        self.release_switch_and_run("s_flipper_dual_wound", 1)
