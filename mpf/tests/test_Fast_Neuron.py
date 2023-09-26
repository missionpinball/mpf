# mpf.tests.test_Fast

from mpf.core.platform import SwitchConfig
from mpf.tests.test_Fast import TestFastBase


class TestFastNeuron(TestFastBase):
    """Tests FAST Neuron hardware."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['net2', 'seg', 'dmd']

    def get_config_file(self):
        return 'neuron.yaml'

    def create_expected_commands(self):
        # These is everything that happens based on this config file before the
        # code in the test starts. (These commands also do lots of tests themselves.),
        # including initial switch and driver states.

        super().create_expected_commands()

        net_commands_from_this_config = {
            'NN:00': 'NN:00,FP-I/O-3208-3   ,01.10,08,20,00,00,00,00,00,00',
            'NN:01': 'NN:01,FP-I/O-0804-3   ,01.10,04,08,00,00,00,00,00,00',
            'NN:02': 'NN:02,FP-I/O-1616-3   ,01.10,10,10,00,00,00,00,00,00',
            'NN:03': 'NN:03,FP-I/O-0024-3   ,01.10,08,18,00,00,00,00,00,00',

            # All 104 switches are initialized, even if they do not exist in the MPF config
            "SL:00,01,04,04": "SL:P",
            "SL:01,01,04,04": "SL:P",
            "SL:02,01,04,04": "SL:P",
            "SL:03,02,04,04": "SL:P",
            "SL:04,01,04,04": "SL:P",
            "SL:05,02,04,04": "SL:P",
            "SL:06,01,04,04": "SL:P",
            "SL:07,01,02,02": "SL:P",
            "SL:08,01,04,04": "SL:P",
            "SL:09,01,05,1A": "SL:P",
            "SL:0A,00,00,00": "SL:P",
            "SL:0B,00,00,00": "SL:P",
            "SL:0C,00,00,00": "SL:P",
            "SL:0D,00,00,00": "SL:P",
            "SL:0E,00,00,00": "SL:P",
            "SL:0F,00,00,00": "SL:P",
            "SL:10,00,00,00": "SL:P",
            "SL:11,00,00,00": "SL:P",
            "SL:12,00,00,00": "SL:P",
            "SL:13,00,00,00": "SL:P",
            "SL:14,00,00,00": "SL:P",
            "SL:15,00,00,00": "SL:P",
            "SL:16,00,00,00": "SL:P",
            "SL:17,00,00,00": "SL:P",
            "SL:18,00,00,00": "SL:P",
            "SL:19,00,00,00": "SL:P",
            "SL:1A,00,00,00": "SL:P",
            "SL:1B,00,00,00": "SL:P",
            "SL:1C,00,00,00": "SL:P",
            "SL:1D,00,00,00": "SL:P",
            "SL:1E,00,00,00": "SL:P",
            "SL:1F,00,00,00": "SL:P",
            "SL:20,00,00,00": "SL:P",
            "SL:21,00,00,00": "SL:P",
            "SL:22,00,00,00": "SL:P",
            "SL:23,00,00,00": "SL:P",
            "SL:24,00,00,00": "SL:P",
            "SL:25,00,00,00": "SL:P",
            "SL:26,00,00,00": "SL:P",
            "SL:27,00,00,00": "SL:P",
            "SL:28,01,04,04": "SL:P",
            "SL:29,00,00,00": "SL:P",
            "SL:2A,00,00,00": "SL:P",
            "SL:2B,00,00,00": "SL:P",
            "SL:2C,00,00,00": "SL:P",
            "SL:2D,00,00,00": "SL:P",
            "SL:2E,00,00,00": "SL:P",
            "SL:2F,00,00,00": "SL:P",
            "SL:30,00,00,00": "SL:P",
            "SL:31,00,00,00": "SL:P",
            "SL:32,00,00,00": "SL:P",
            "SL:33,00,00,00": "SL:P",
            "SL:34,00,00,00": "SL:P",
            "SL:35,00,00,00": "SL:P",
            "SL:36,00,00,00": "SL:P",
            "SL:37,00,00,00": "SL:P",
            "SL:38,01,04,04": "SL:P",
            "SL:39,00,00,00": "SL:P",
            "SL:3A,00,00,00": "SL:P",
            "SL:3B,00,00,00": "SL:P",
            "SL:3C,00,00,00": "SL:P",
            "SL:3D,00,00,00": "SL:P",
            "SL:3E,00,00,00": "SL:P",
            "SL:3F,00,00,00": "SL:P",
            "SL:40,00,00,00": "SL:P",
            "SL:41,00,00,00": "SL:P",
            "SL:42,00,00,00": "SL:P",
            "SL:43,00,00,00": "SL:P",
            "SL:44,00,00,00": "SL:P",
            "SL:45,00,00,00": "SL:P",
            "SL:46,00,00,00": "SL:P",
            "SL:47,00,00,00": "SL:P",
            "SL:48,00,00,00": "SL:P",
            "SL:49,00,00,00": "SL:P",
            "SL:4A,00,00,00": "SL:P",
            "SL:4B,00,00,00": "SL:P",
            "SL:4C,00,00,00": "SL:P",
            "SL:4D,00,00,00": "SL:P",
            "SL:4E,00,00,00": "SL:P",
            "SL:4F,00,00,00": "SL:P",
            "SL:50,00,00,00": "SL:P",
            "SL:51,00,00,00": "SL:P",
            "SL:52,00,00,00": "SL:P",
            "SL:53,00,00,00": "SL:P",
            "SL:54,00,00,00": "SL:P",
            "SL:55,00,00,00": "SL:P",
            "SL:56,00,00,00": "SL:P",
            "SL:57,00,00,00": "SL:P",
            "SL:58,00,00,00": "SL:P",
            "SL:59,00,00,00": "SL:P",
            "SL:5A,00,00,00": "SL:P",
            "SL:5B,00,00,00": "SL:P",
            "SL:5C,00,00,00": "SL:P",
            "SL:5D,00,00,00": "SL:P",
            "SL:5E,00,00,00": "SL:P",
            "SL:5F,00,00,00": "SL:P",
            "SL:60,00,00,00": "SL:P",
            "SL:61,00,00,00": "SL:P",
            "SL:62,00,00,00": "SL:P",
            "SL:63,00,00,00": "SL:P",
            "SL:64,00,00,00": "SL:P",
            "SL:65,00,00,00": "SL:P",
            "SL:66,00,00,00": "SL:P",
            "SL:67,00,00,00": "SL:P",

            # Drivers from the config will be initialized with their specific settings
            "DL:00,81,00,10,0A,FF,00,00,00": "DL:P",
            "DL:01,81,00,10,0A,FF,00,FF,00": "DL:P",
            "DL:02,81,00,10,17,AA,00,00,00": "DL:P",
            "DL:05,81,00,10,0A,FF,00,00,1B": "DL:P",
            "DL:06,81,00,70,0A,FF,14,EE,00": "DL:P",
            "DL:07,81,00,10,0A,FF,00,88,00": "DL:P",
            "DL:08,81,00,70,0A,FF,C8,EE,00": "DL:P",
            "DL:0A,81,00,10,18,FE,14,AA,00": "DL:P",
            "DL:0B,81,00,10,14,AA,14,AA,00": "DL:P",
            "DL:0D,81,00,10,0A,FF,00,00,00": "DL:P",
            "DL:0E,81,00,10,0A,FF,00,FF,00": "DL:P",
            "DL:0F,81,00,10,0E,FF,00,01,00": "DL:P",
            "DL:10,81,00,10,0A,FF,00,00,00": "DL:P",
            "DL:11,81,00,10,0A,FF,00,00,00": "DL:P",
            "DL:12,81,00,10,0F,FF,00,00,00": "DL:P",
            "DL:13,81,00,10,0A,FF,00,FF,00": "DL:P",
            }

        self.net_cpu .expected_commands.update(net_commands_from_this_config)

    def test_test_coils(self):
        # The default expected commands will verify all the coils are configured properly.
        # We just need to ensure things get enabled properly.
        self.confirm_commands()

        self._test_pulse()
        self._test_long_pulse()
        self._test_timed_enable()
        self._test_default_timed_enable()
        self._test_enable_exception()
        self._test_allow_enable()

        # test hardware scan
        info_str = (
            'NET: FP-CPU-2000 v02.13\n'
            '\n'
            'I/O Boards:\n'
            'Board 0 - Model: FP-I/O-3208, Firmware: 01.10, Switches: 32, Drivers: 8\n'
            'Board 1 - Model: FP-I/O-0804, Firmware: 01.10, Switches: 8, Drivers: 4\n'
            'Board 2 - Model: FP-I/O-1616, Firmware: 01.10, Switches: 16, Drivers: 16\n'
            'Board 3 - Model: FP-I/O-0024, Firmware: 01.10, Switches: 24, Drivers: 8\n'
            )

        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_pulse(self):

        coil = self.machine.coils["c_baseline"]

        # pulse based on its initial config
        self.net_cpu .expected_commands = {"TL:00,01": "TL:P"}
        coil.pulse()
        self.confirm_commands()

        # pulse with a non-standard pulse_ms, trigger 89 also pulses now
        self.net_cpu .expected_commands = {'DL:00,89,00,10,32,FF,00,00,00': 'DL:P'}
        coil.pulse(50)
        self.confirm_commands()

        # Pulse again and it should just use a TL since the coil is already configured
        self.net_cpu .expected_commands = {"TL:00,01": "TL:P"}
        coil.pulse(50)
        self.confirm_commands()

        # Pulse default and it should reconfigure to default
        self.net_cpu .expected_commands = {'DL:00,89,00,10,0A,FF,00,00,00': 'DL:P'}
        coil.pulse()
        self.confirm_commands()

        # pulse with non-standard ms and power
        self.net_cpu .expected_commands = {'DL:00,89,00,10,64,92,00,00,00': 'DL:P'}
        coil.pulse(100, 0.375)
        self.confirm_commands()

        # Do that same pulse again and it should just use a TL since the coil is already configured
        self.net_cpu .expected_commands = {"TL:00,01": "TL:P"}
        coil.pulse(100, 0.375)
        self.confirm_commands()

    def _test_long_pulse(self):

        coil = self.machine.coils["c_long_pwm2"]

        # pulse based on its initial config
        self.net_cpu .expected_commands = {"TL:06,01": "TL:P"}
        coil.pulse()
        self.confirm_commands()

        self.advance_time_and_run(21)
        # pulse it again, but disable it partway through

        self.net_cpu .expected_commands = {"TL:06,01": "TL:P",
                                                             "TL:06,02": "TL:P",
                                                            }

        coil.pulse()
        self.advance_time_and_run(1)
        coil.disable()
        self.confirm_commands()

    def _test_timed_enable(self):

        coil = self.machine.coils["c_long_pwm2"]  # DL:06,81,00,70,0A,FF,14,EE,00

        # timed_enable based on its current config
        self.net_cpu .expected_commands = {"TL:06,01": "TL:P"}
        coil.timed_enable()
        self.confirm_commands()

        self.net_cpu .expected_commands = {"DL:06,89,00,70,0F,FF,0A,88,00": "DL:P"}
        coil.timed_enable(1000, 0.25, 15, 1.0)
        self.confirm_commands()

    def _test_default_timed_enable(self):
        # test that a regular pulse() command will use the long pulse config
        coil = self.machine.coils["c_longer_pwm2"]  # DL:08,81,00,70,0A,FF,C8,EE,00

        # timed_enable based on its current config
        self.net_cpu .expected_commands = {"TL:08,01": "TL:P"}
        coil.pulse()
        self.confirm_commands()

    def _test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils["c_baseline"].enable()
            self.advance_time_and_run(.1)

    def _test_allow_enable(self):
        self.net_cpu .expected_commands = {
            "DL:01,C1,00,18,0A,FF,FF,00,00": "DL:P"
        }
        self.machine.coils["c_allow_enable"].enable()
        self.advance_time_and_run(.1)
        self.assertFalse(self.net_cpu .expected_commands)

    def test_test_autofire_rules(self):
        self._test_pulse_rules()
        self._test_pulse_rules_inverted_switch()
        self._test_long_pulse_rules()
        self._test_enable_exception_hw_rule()
        self._test_manual_action_during_active_rule()

    def _test_pulse_rules(self):
        # Basic pulse rule
        # DL:10,81,00,10,0A,FF,00,00,00
        # SL:28,01,04,04

        # Enable, should just update existing rule via TL but add the switch ID
        self.net_cpu .expected_commands = {"TL:10,00,28": "TL:P"}
        self.machine.autofire_coils["ac_baseline"].enable()
        self.confirm_commands()

        # Disable, should update existing rule via TL
        self.net_cpu .expected_commands = {"TL:10,02": "TL:P"}
        self.machine.autofire_coils["ac_baseline"].disable()
        self.confirm_commands()

        # Re-enable, should update existing rule via TL
        self.net_cpu .expected_commands = {"TL:10,00": "TL:P"}
        self.machine.autofire_coils["ac_baseline"].enable()
        self.confirm_commands()

    def _test_pulse_rules_inverted_switch(self):
        # Basic pulse rule with inverted switch
        # DL:11,81,00,10,0A,FF,00,00,00
        # SL:05,02,04,04

        # Inverted switch, should send a new rule
        self.net_cpu .expected_commands = {"DL:11,11,05,10,0A,FF,00,00,00": "DL:P"}
        self.machine.autofire_coils["ac_inverted_switch"].enable()
        self.confirm_commands()

        # Disable, should update existing rule via TL
        self.net_cpu .expected_commands = {"TL:11,02": "TL:P"}
        self.machine.autofire_coils["ac_inverted_switch"].disable()
        self.confirm_commands()

        # Re-enable, should update existing rule via TL
        self.net_cpu .expected_commands = {"TL:11,00": "TL:P"}
        self.machine.autofire_coils["ac_inverted_switch"].enable()
        self.confirm_commands()

    def _test_long_pulse_rules(self):
        # Pulse rules with long pulse (Mode 70)
        driver = self.machine.coils["c_long_pwm2"].hw_driver
        switch = self.machine.switches["s_debounce_auto"].hw_switch

        # Verify current configs
        self.assertEqual(driver.get_current_config(), 'DL:06,81,00,70,0A,FF,14,EE,00')
        self.assertEqual(switch.get_current_config(), 'SL:06,01,04,04')

        # Enable, should just update existing rule via TL but add the switch ID
        self.net_cpu .expected_commands = {"TL:06,00,06": "TL:P"}
        self.machine.autofire_coils["ac_2_stage_pwm"].enable()
        self.confirm_commands()

        # Enable again, no new commands should be sent
        self.machine.autofire_coils["ac_2_stage_pwm"].enable()
        self.confirm_commands()

        # Disable, should update existing rule via TL
        self.net_cpu .expected_commands = {"TL:06,02": "TL:P"}
        self.machine.autofire_coils["ac_2_stage_pwm"].disable()
        self.confirm_commands()

        # Disable again, no new commands should be sent
        self.machine.autofire_coils["ac_2_stage_pwm"].disable()
        self.confirm_commands()

        # Re-enable, should update existing rule via TL, want to ensure it keeps mode 70
        self.net_cpu .expected_commands = {"TL:06,00": "TL:P"}
        self.machine.autofire_coils["ac_2_stage_pwm"].enable()
        self.confirm_commands()

        self.assertEqual(driver.get_current_config(), 'DL:06,01,06,70,0A,FF,14,EE,00')

    def _test_enable_exception_hw_rule(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.flippers["f_single_wound"].config['main_coil_overwrite']['hold_power'] = 1.0
            self.machine.flippers["f_single_wound"].enable()

        self.machine.flippers["f_single_wound"].config['main_coil_overwrite']['hold_power'] = None

    def _test_manual_action_during_active_rule(self):
        driver = self.machine.coils["c_pwm2"].hw_driver
        switch = self.machine.switches["s_debounce_quick"].hw_switch

        # Verify current configs
        self.assertEqual(driver.get_current_config(), 'DL:0B,81,00,10,14,AA,14,AA,00')
        self.assertEqual(switch.get_current_config(), 'SL:07,01,02,02')

        # Enable, should just update existing rule via TL but add the switch ID
        self.net_cpu .expected_commands = {"TL:0B,00,07": "TL:P"}
        self.machine.autofire_coils["ac_test_action"].enable()
        self.confirm_commands()

        # Manually pulse the coil, should not affect the rule
        self.net_cpu .expected_commands = {"TL:0B,01": "TL:P"}
        self.machine.coils["c_pwm2"].pulse()
        self.confirm_commands()

        # Disable, should update existing rule via TL
        self.net_cpu .expected_commands = {"TL:0B,02": "TL:P"}
        self.machine.autofire_coils["ac_test_action"].disable()
        self.confirm_commands()

        # Manually pulse the coil, should not affect the rule
        self.net_cpu .expected_commands = {"TL:0B,01": "TL:P"}
        self.machine.coils["c_pwm2"].pulse()
        self.confirm_commands()

        # Re-enable, should update existing rule via TL
        self.net_cpu .expected_commands = {"TL:0B,00": "TL:P"}
        self.machine.autofire_coils["ac_test_action"].enable()
        self.confirm_commands()

        # Disabled the rule
        self.net_cpu .expected_commands = {"TL:0B,02": "TL:P"}
        self.machine.autofire_coils["ac_test_action"].disable()
        self.confirm_commands()

        # Manually pulse the coil with non-standard pulse
        # trigger 89 = bit 0 driver enable + bit 3 one_shot + bit 7 disable switch
        # switch is disabled since the rule is disabled
        self.net_cpu .expected_commands = {"DL:0B,89,07,10,64,AA,14,AA,00": "DL:P"}
        self.machine.coils["c_pwm2"].pulse(100)
        self.confirm_commands()

        # Enable the rule, should send new config since last pulse was non-standard
        self.net_cpu .expected_commands = {"DL:0B,01,07,10,14,AA,14,AA,00": "DL:P"}
        self.machine.autofire_coils["ac_test_action"].enable()
        self.confirm_commands()

        # Send non-standard pulse. Rule is enabled so a second DL command should be sent to reset the rule
        # to the proper config
        # trigger 09 = bit 0 driver enable + bit 3 one_shot, bit 7 is cleared since rule is active
        self.net_cpu .expected_commands = {"DL:0B,09,07,10,FA,AA,14,AA,00": "DL:P"}
        self.machine.coils["c_pwm2"].pulse(250)
        self.confirm_commands()  # This also moves the clock 100ms

        # Jump ahead 251ms and make sure the rule was put back
        self.net_cpu .expected_commands = {"DL:0B,01,07,10,14,AA,14,AA,00": "DL:P"}
        self.advance_time_and_run(0.051) # +51ms
        self.confirm_commands()  # +100ms, 251ms total since manual pulse, so this command should have been sent

        # hold a device on manually, then cancel it, make sure autofire comes back
        # mode 18 (pulse + hold), trigger C1 (bit 7 disable switch, bit 6 manual, bit 1 enable)
        self.net_cpu .expected_commands = {"DL:0B,C1,07,18,14,AA,AA,00,00": "DL:P"}
        self.machine.coils["c_pwm2"].enable()
        self.confirm_commands()

        # Make sure nothing else was sent
        self.advance_time_and_run(2)
        self.confirm_commands()

        # Turn off the hold and make sure the rule comes back
        # Need to ensure we switch from mode 18 back to 10
        self.net_cpu .expected_commands = {"DL:0B,01,07,10,14,AA,14,AA,00": "DL:P"}
        self.machine.coils["c_pwm2"].disable()
        self.confirm_commands

        # Make sure nothing else was sent
        self.advance_time_and_run(2)
        self.confirm_commands()

        # Send a series of manual pulses during an autofire and make sure the rule comes back, but not until
        # the last pulse is done

        # Previous command already re-enabled the autofire
        self.assertEqual(driver.get_current_config(), 'DL:0B,01,07,10,14,AA,14,AA,00')

        # Pulse with manual pulse time
        self.net_cpu .expected_commands = {"DL:0B,09,07,10,C8,AA,14,AA,00": "DL:P"}
        self.machine.coils["c_pwm2"].pulse(200)
        self.confirm_commands()  # +100ms

        # Pulse again before the first pulse is done, TL this time since it's the same pulse as last time
        self.net_cpu .expected_commands = {"TL:0B,01": "TL:P"}
        self.machine.coils["c_pwm2"].pulse(200)
        self.confirm_commands()  # +100ms
        self.net_cpu .expected_commands = {"TL:0B,01": "TL:P"}
        self.machine.coils["c_pwm2"].pulse(200)
        self.confirm_commands()  # +100ms

        # Last pulse will reset the rule after 201ms, so jump past that and verify the rule is back
        self.net_cpu .expected_commands = {"DL:0B,01,07,10,14,AA,14,AA,00": "DL:P"}
        self.advance_time_and_run(0.002)
        self.confirm_commands()

    def _switch_hit_cb(self, **kwargs):
        self.switch_hit = True

    def test_test_switches(self):
        # Default startup SL commands test / confirm all the variations of the switch configs
        self._test_startup_switches()
        self._test_bad_switch_configs()
        self._test_switch_changes()
        self._test_switch_changes_nc()
        self._test_receiving_sa()

    def _test_startup_switches(self):
        self.assertSwitchState("s_baseline", 1)
        self.assertSwitchState("s_flipper", 0)
        self.assertSwitchState("s_test_nc", 0)  # NC which SA reports active should be inactive

    def _test_bad_switch_configs(self):
        # invalid switch
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('io3208-32', SwitchConfig(name="", debounce='auto', invert=0), {})

        # invalid board
        with self.assertRaises(AssertionError):
            self.machine.default_platform.configure_switch('brian-0', SwitchConfig(name="", debounce='auto', invert=0), {})

    def _test_switch_changes(self):
        self.assertSwitchState("s_flipper", 0)

        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertSwitchState("s_flipper_eos", 0)
        self.assertFalse(self.switch_hit)

        self.machine.events.add_handler("s_flipper_eos_active", self._switch_hit_cb)
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"-L:02\r")
        self.advance_time_and_run(1)

        self.assertTrue(self.switch_hit)
        self.assertSwitchState("s_flipper_eos", 1)
        self.switch_hit = False

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_flipper_eos", 1)

        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"/L:02\r")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_flipper_eos", 0)

    def _test_switch_changes_nc(self):
        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertSwitchState("s_test_nc", 0)
        self.assertFalse(self.switch_hit)

        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"-L:05\r")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertSwitchState("s_test_nc", 1)

        self.machine.events.add_handler("s_test_nc_inactive", self._switch_hit_cb)
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"/L:05\r")
        self.advance_time_and_run(1)

        self.assertSwitchState("s_test_nc", 0)
        self.assertTrue(self.switch_hit)
        self.switch_hit = False

    def _test_receiving_sa(self):
        # Receive a random SA command during normal operation with an unexpected switch
        # state and ensure it's processed properly

        # Show s_cab_flipper 0x38 switch on
        self.net_cpu .expected_commands = {
            "SA:" : "SA:0E,2900000000000001000000000000"}

        self.assertSwitchState("s_cab_flipper", 0)

        # Send an SA:
        self.loop.run_until_complete(self.machine.default_platform.get_hw_switch_states(True))
        self.advance_time_and_run()

        self.assertSwitchState("s_cab_flipper", 1)

        # Process a random SA coming in (this shouldn't happen but should work in non async mode)
        # Switch 0x09 is also now active
        self.assertSwitchState("s_debounce_custom", 0)
        self.machine.default_platform.serial_connections['net'].parse_incoming_raw_bytes(b"SA:0E,2902000000000001000000000000\r")
        self.advance_time_and_run()
        self.assertSwitchState("s_debounce_custom", 1)

    def test_test_flipper_single_coil(self):
        coil = self.machine.coils["c_flipper_single_wound"]
        hw_driver = coil.hw_driver
        switch = self.machine.switches["s_flipper_opto"].hw_switch
        flipper = self.machine.flippers["f_single_wound"]

        self.assertEqual(hw_driver.get_current_config(), 'DL:0F,81,00,10,0E,FF,00,01,00')
        self.assertEqual(switch.get_current_config(), 'SL:03,02,04,04')

        # flipper rule enable
        # Trigger 11 (bit 0 enable, bit 4 invert switch since it's an opto)
        self.net_cpu .expected_commands = {"DL:0F,11,03,18,0E,FF,01,00,00": "DL:P",}
        flipper.enable()
        self.confirm_commands()

        # manual flip while rule is active
        self.net_cpu .expected_commands = {"TL:0F,01": "TL:P"}
        coil.pulse()
        self.confirm_commands()

        # disable rule (tilt)
        self.net_cpu .expected_commands = {"TL:0F,02": "TL:P"}
        flipper.disable()
        self.confirm_commands()

        # enable again, config has already been sent
        self.net_cpu .expected_commands = {"TL:0F,00": "TL:P"}
        flipper.enable()
        self.confirm_commands()

    def test_test_flipper_two_coils(self):
        main_coil = self.machine.coils["c_flipper_main"]
        hold_coil = self.machine.coils["c_flipper_hold"]
        main_hw_driver = main_coil.hw_driver
        hold_hw_driver = hold_coil.hw_driver
        switch = self.machine.switches["s_flipper"].hw_switch
        flipper = self.machine.flippers["f_dual_wound"]

        self.assertEqual(main_hw_driver.get_current_config(), 'DL:0D,81,00,10,0A,FF,00,00,00')
        self.assertEqual(hold_hw_driver.get_current_config(), 'DL:0E,81,00,10,0A,FF,00,FF,00')
        self.assertEqual(switch.get_current_config(), 'SL:01,01,04,04')

        # flipper rule enable
        # Trigger 1 (bit 0 enable)
        self.net_cpu .expected_commands = {"DL:0D,01,01,18,0A,FF,00,00,00": "DL:P",
                                                             "DL:0E,01,01,18,0A,FF,FF,00,00": "DL:P",}
        flipper.enable()
        self.confirm_commands()

        # manual flip while rule is active
        self.net_cpu .expected_commands = {"TL:0D,01": "TL:P"}
        main_coil.pulse()
        self.confirm_commands()

        # disable rule (tilt)
        self.net_cpu .expected_commands = {"TL:0D,02": "TL:P",
                                                             "TL:0E,02": "TL:P",}
        flipper.disable()
        self.confirm_commands()

        # enable again, config has already been sent
        self.net_cpu .expected_commands = {"TL:0D,00": "TL:P",
                                                             "TL:0E,00": "TL:P",}
        flipper.enable()
        self.confirm_commands()

    def test_test_flipper_two_coils_with_eos(self):
        main_coil = self.machine.coils["c_flipper2_main"]
        hold_coil = self.machine.coils["c_flipper2_hold"]
        main_hw_driver = main_coil.hw_driver
        hold_hw_driver = hold_coil.hw_driver
        switch = self.machine.switches["s_cab_flipper"].hw_switch
        eos_switch = self.machine.switches["s_flipper_eos"].hw_switch
        flipper = self.machine.flippers["f_test_hold_eos"]

        self.assertEqual(main_hw_driver.get_current_config(), 'DL:12,81,00,10,0F,FF,00,00,00')
        self.assertEqual(hold_hw_driver.get_current_config(), 'DL:13,81,00,10,0A,FF,00,FF,00')
        self.assertEqual(switch.get_current_config(), 'SL:38,01,04,04')

        # flipper rule enable
        # Trigger 1 (bit 0 enable), Mode 75 (pulse+hold w/cancel), EOS switch 38
        self.net_cpu .expected_commands = {"DL:12,01,38,75,02,0F,00,00,00": "DL:P",
                                                             "DL:13,01,38,18,0A,FF,FF,00,00": "DL:P",}
        flipper.enable()
        self.confirm_commands()

        # manual flip while rule is active, this will send a new DL (since mode 75 isn't a normal pulse mode)
        # followed by another DL after a delay to reconfigure it back to the autofire rule
        self.net_cpu .expected_commands = {"DL:12,09,38,10,0F,FF,00,00,00": "DL:P",
                                                             "DL:12,01,38,75,02,0F,00,00,00": "DL:P",}
        main_coil.pulse()
        self.confirm_commands()

        # disable rule (tilt)
        self.net_cpu .expected_commands = {"TL:12,02": "TL:P",
                                                             "TL:13,02": "TL:P",}
        flipper.disable()
        self.confirm_commands()

        # enable again, config has already been sent
        self.net_cpu .expected_commands = {"TL:12,00": "TL:P",
                                                             "TL:13,00": "TL:P",}
        flipper.enable()
        self.confirm_commands()

    def test_machine_reset(self):

        # Set the commands that will respond to the query on reset. Some of these are
        # changed from the default so we can simulate the machine in a dir

        self.net_cpu .expected_commands = {
            "SL:00": "SL:00,01,04,04",
            "SL:01": "SL:01,01,04,04",
            "SL:02": "SL:02,01,04,04",
            "SL:03": "SL:03,02,04,04",
            "SL:04": "SL:04,01,04,04",
            "SL:05": "SL:05,02,04,04",
            "SL:06": "SL:06,01,04,04",
            "SL:07": "SL:07,01,02,02",
            "SL:08": "SL:08,01,04,04",
            "SL:09": "SL:09,01,05,1A",
            "SL:0A": "SL:0A,00,00,00",
            "SL:0B": "SL:0B,00,00,00",
            "SL:0C": "SL:0C,00,00,00",
            "SL:0D": "SL:0D,00,00,00",
            "SL:0E": "SL:0E,02,00,00",
            "SL:0F": "SL:0F,00,00,00",
            "SL:10": "SL:10,00,02,00",
            "SL:11": "SL:11,00,00,00",
            "SL:12": "SL:12,00,22,00",
            "SL:13": "SL:13,00,00,00",
            "SL:14": "SL:14,00,00,00",
            "SL:15": "SL:15,00,00,00",
            "SL:16": "SL:16,00,00,00",
            "SL:17": "SL:17,00,00,00",
            "SL:18": "SL:18,00,00,00",
            "SL:19": "SL:19,00,00,00",
            "SL:1A": "SL:1A,00,00,00",
            "SL:1B": "SL:1B,00,00,00",
            "SL:1C": "SL:1C,00,00,00",
            "SL:1D": "SL:1D,00,00,00",
            "SL:1E": "SL:1E,00,00,00",
            "SL:1F": "SL:1F,00,00,00",
            "SL:20": "SL:20,00,00,00",
            "SL:21": "SL:21,00,00,00",
            "SL:22": "SL:22,00,00,00",
            "SL:23": "SL:23,00,00,00",
            "SL:24": "SL:24,00,00,00",
            "SL:25": "SL:25,00,00,00",
            "SL:26": "SL:26,00,00,00",
            "SL:27": "SL:27,00,00,00",
            "SL:28": "SL:28,01,04,04",
            "SL:29": "SL:29,00,00,00",
            "SL:2A": "SL:2A,00,00,00",
            "SL:2B": "SL:2B,00,00,00",
            "SL:2C": "SL:2C,00,00,00",
            "SL:2D": "SL:2D,00,00,00",
            "SL:2E": "SL:2E,00,00,00",
            "SL:2F": "SL:2F,00,00,00",
            "SL:30": "SL:30,00,00,00",
            "SL:31": "SL:31,00,00,00",
            "SL:32": "SL:32,00,00,00",
            "SL:33": "SL:33,00,00,00",
            "SL:34": "SL:34,00,00,00",
            "SL:35": "SL:35,00,00,00",
            "SL:36": "SL:36,00,00,00",
            "SL:37": "SL:37,00,00,00",
            "SL:38": "SL:38,01,04,04",
            "SL:39": "SL:39,00,00,00",
            "SL:3A": "SL:3A,00,00,00",
            "SL:3B": "SL:3B,00,00,00",
            "SL:3C": "SL:3C,00,00,00",
            "SL:3D": "SL:3D,00,00,00",
            "SL:3E": "SL:3E,00,00,00",
            "SL:3F": "SL:3F,00,00,00",
            "SL:40": "SL:40,00,00,00",
            "SL:41": "SL:41,00,00,00",
            "SL:42": "SL:42,00,00,00",
            "SL:43": "SL:43,00,00,00",
            "SL:44": "SL:44,00,00,00",
            "SL:45": "SL:45,00,00,00",
            "SL:46": "SL:46,00,00,00",
            "SL:47": "SL:47,00,00,00",
            "SL:48": "SL:48,00,00,00",
            "SL:49": "SL:49,00,00,00",
            "SL:4A": "SL:4A,00,00,00",
            "SL:4B": "SL:4B,00,00,00",
            "SL:4C": "SL:4C,00,00,00",
            "SL:4D": "SL:4D,00,00,00",
            "SL:4E": "SL:4E,00,00,00",
            "SL:4F": "SL:4F,00,00,00",
            "SL:50": "SL:50,00,00,00",
            "SL:51": "SL:51,00,00,00",
            "SL:52": "SL:52,00,00,00",
            "SL:53": "SL:53,00,00,00",
            "SL:54": "SL:54,00,00,00",
            "SL:55": "SL:55,00,00,00",
            "SL:56": "SL:56,00,00,00",
            "SL:57": "SL:57,00,00,00",
            "SL:58": "SL:58,00,00,00",
            "SL:59": "SL:59,00,00,00",
            "SL:5A": "SL:5A,00,00,00",
            "SL:5B": "SL:5B,00,00,00",
            "SL:5C": "SL:5C,00,00,00",
            "SL:5D": "SL:5D,00,00,00",
            "SL:5E": "SL:5E,00,00,00",
            "SL:5F": "SL:5F,00,00,00",
            "SL:60": "SL:60,00,00,00",
            "SL:61": "SL:61,00,00,00",
            "SL:62": "SL:62,00,00,00",
            "SL:63": "SL:63,00,00,00",
            "SL:64": "SL:64,00,00,00",
            "SL:65": "SL:65,00,00,00",
            "SL:66": "SL:66,00,00,00",
            "SL:67": "SL:67,00,00,00",

            # Here's the cleanup from these
            "SL:0E,00,00,00": "SL:P",
            "SL:10,00,00,00": "SL:P",
            "SL:12,00,00,00": "SL:P",

            # Here are the DL queries, some are dirty
            "DL:00": "DL:00,81,00,10,0A,FF,00,00,00",
            "DL:01": "DL:01,81,00,10,0A,FF,00,FF,00",
            "DL:02": "DL:02,81,00,10,17,AA,00,00,00",
            "DL:03": "DL:03,00,00,00,00,00,00,00,00",
            "DL:04": "DL:04,00,00,00,00,00,00,00,00",
            "DL:05": "DL:05,81,00,10,0A,FF,00,00,1B",
            "DL:06": "DL:06,81,00,70,0A,FF,14,EE,00",
            "DL:07": "DL:07,81,00,10,0A,FF,00,88,00",
            "DL:08": "DL:08,81,00,70,0A,FF,C8,EE,00",
            "DL:09": "DL:09,00,00,00,00,00,00,00,00",
            "DL:0A": "DL:0A,81,00,10,18,FE,14,AA,00",
            "DL:0B": "DL:0B,81,00,10,14,AA,14,AA,00",
            "DL:0C": "DL:0C,00,00,00,00,00,00,00,00",
            "DL:0D": "DL:0D,01,01,18,0A,FF,00,00,00",
            "DL:0E": "DL:0E,81,00,10,0A,FF,00,FF,00",
            "DL:0F": "DL:0F,11,03,18,0E,FF,01,00,00",
            "DL:10": "DL:10,81,00,10,0A,FF,00,00,00",
            "DL:11": "DL:11,81,00,10,0A,FF,00,00,00",
            "DL:12": "DL:12,81,00,10,0F,FF,00,00,00",
            "DL:13": "DL:13,81,00,10,0A,FF,00,FF,00",
            "DL:14": "DL:14,00,00,00,00,00,00,00,00",
            "DL:15": "DL:15,00,00,00,00,00,00,00,00",
            "DL:16": "DL:16,00,00,00,00,00,00,00,00",
            "DL:17": "DL:17,00,00,00,00,00,00,00,00",
            "DL:18": "DL:18,00,00,00,00,00,00,00,00",
            "DL:19": "DL:19,00,00,00,00,00,00,00,00",
            "DL:1A": "DL:1A,00,00,00,00,00,00,00,00",
            "DL:1B": "DL:1B,00,00,00,00,00,00,0A,00",
            "DL:1C": "DL:1C,00,00,00,00,00,00,00,00",
            "DL:1D": "DL:1D,00,00,00,00,00,00,00,00",
            "DL:1E": "DL:1E,00,00,00,00,00,00,00,00",
            "DL:1F": "DL:1F,00,00,00,00,00,00,00,00",
            "DL:20": "DL:20,00,00,00,00,00,00,00,00",
            "DL:21": "DL:21,00,00,00,00,00,00,00,00",
            "DL:22": "DL:22,00,00,00,00,00,00,00,00",
            "DL:23": "DL:23,00,00,00,00,00,00,00,00",
            "DL:24": "DL:24,00,00,00,00,00,00,00,00",
            "DL:25": "DL:25,00,00,00,00,00,00,00,00",
            "DL:26": "DL:26,00,00,00,00,00,00,00,00",
            "DL:27": "DL:27,00,00,00,00,00,00,00,00",
            "DL:28": "DL:28,00,00,00,00,00,00,00,00",
            "DL:29": "DL:29,00,00,00,00,00,00,00,00",
            "DL:2A": "DL:2A,00,00,00,00,00,00,00,00",
            "DL:2B": "DL:2B,00,00,00,00,00,00,00,00",
            "DL:2C": "DL:2C,00,00,00,00,00,00,00,00",
            "DL:2D": "DL:2D,00,00,00,00,00,00,00,00",
            "DL:2E": "DL:2E,00,00,00,00,00,00,00,00",
            "DL:2F": "DL:2F,00,00,00,00,00,00,00,00",

            # Cleaning up the dirty ones
            "DL:0D,81,00,10,0A,FF,00,00,00": "DL:P",
            "DL:0F,81,00,10,0E,FF,00,01,00": "DL:P",
            "DL:1B,00,00,00,00,00,00,00,00": "DL:P",
            }

        # reset the machine and ensure all the dirty devices get reset
        self.loop.run_until_complete(self.machine.reset())
        self.advance_time_and_run()

    # def test_dmd_update(self):

    #     # test configure
    #     dmd = self.machine.default_platform.configure_dmd()

    #     # test set frame to buffer
    #     frame = bytearray()
    #     for i in range(4096):
    #         frame.append(64 + i % 192)

    #     frame = bytes(frame)

    #     # test draw
    #     self.serial_connections['dmd'].expected_commands = {
    #         b'BM:' + frame: False
    #     }
    #     dmd.update(frame)

    #     self.advance_time_and_run(.1)

    #     self.assertFalse(self.serial_connections['dmd'].expected_commands)

    # @expect_startup_error()
    # @test_config("error_lights.yaml")
    # def test_light_errors(self):
    #     self.assertIsInstance(self.startup_error, ConfigFileError)
    #     self.assertEqual(7, self.startup_error.get_error_no())
    #     self.assertEqual("light.test_led", self.startup_error.get_logger_name())
    #     self.assertIsInstance(self.startup_error.__cause__, ConfigFileError)
    #     self.assertEqual(9, self.startup_error.__cause__.get_error_no())
    #     self.assertEqual("FAST", self.startup_error.__cause__.get_logger_name())
    #     self.assertEqual("Light syntax is number-channel (but was \"3\") for light test_led.",
    #                      self.startup_error.__cause__._message)
