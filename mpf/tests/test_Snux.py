"""Test snux platform."""
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase, MagicMock
from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings


class TestSnux(MpfFakeGameTestCase):
    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/snux/'

    def get_platform(self):
        # no force platform. we are testing virtual + snux
        return False

    def _get_snux_platform(self):
        return self.machine.hardware_platforms['snux']

    def _get_driver(self, number):
        return self._get_snux_platform().drivers[number]

    def test_ac_relay_default(self):
        # outside game it should be default off
        c_ac_relay = self.machine.coils["c_ac_relay"]
        self.assertEqual("disabled", c_ac_relay.hw_driver.state)

        self.start_game()
        # during a game it should be default on to allow fast flashers
        self.assertEqual("enabled", c_ac_relay.hw_driver.state)

        # after the game ended it should turn back to default off
        self.drain_all_balls()
        self.drain_all_balls()
        self.drain_all_balls()
        self.assertGameIsNotRunning()
        self.assertEqual("disabled", c_ac_relay.hw_driver.state)

    def test_ac_switch_and_pulse(self):
        # test diag led flashing. otherwise snux is not running
        c_diag_led_driver = self.machine.coils["c_diag_led_driver"]
        c_diag_led_driver.pulse = MagicMock()
        self.advance_time_and_run(1)
        c_diag_led_driver.pulse.assert_called_with(250)

        # test if a and c side relays were properly loaded
        self.assertEqual(2, len(self._get_snux_platform().drivers))
        driver_11 = self._get_driver("c11")
        driver_12 = self._get_driver("c12")

        c_ac_relay = self.machine.coils["c_ac_relay"]
        c_ac_relay.enable = MagicMock()
        c_ac_relay.disable = MagicMock()

        driver_11.pulse = MagicMock(return_value=0)
        driver_11.enable = MagicMock()
        driver_11.disable = MagicMock()
        driver_12.pulse = MagicMock(return_value=0)
        driver_12.enable = MagicMock()
        driver_12.disable = MagicMock()

        # a side should be triggered first. c side should wait
        self.machine.coils["c_side_a1"].pulse(50)
        self.machine.coils["c_side_c1"].pulse(50)
        self.advance_time_and_run(0.001)
        driver_11.pulse.assert_called_with(PulseSettings(power=1.0, duration=50))
        driver_11.pulse = MagicMock()
        assert not driver_12.pulse.called
        assert not c_ac_relay.enable.called

        # after 50ms + 75ms transition c side should get triggered
        self.advance_time_and_run(0.075)
        c_ac_relay.enable.assert_called_with()
        c_ac_relay.enable = MagicMock()
        assert not driver_11.pulse.called

        # after the relay switches. pulse the other coil
        self.advance_time_and_run(0.075)
        driver_11.pulse.assert_called_with(PulseSettings(power=1.0, duration=50))

        # it should switch back to a side when idle
        self.advance_time_and_run(0.052)
        c_ac_relay.disable.assert_called_with()
        c_ac_relay.disable = MagicMock()

    def test_ac_switch_and_enable(self):

        driver_12 = self._get_driver("c12")
        driver_12.enable = MagicMock()
        driver_12.disable = MagicMock()

        c_ac_relay = self.machine.coils["c_ac_relay"].hw_driver
        c_ac_relay.enable = MagicMock()
        c_ac_relay.disable = MagicMock()

        self.advance_time_and_run(0.10)

        # test enable on c side
        self.machine.coils["c_side_c2"].enable()
        self.machine_run()
        c_ac_relay.enable.assert_called_with(PulseSettings(power=1.0, duration=10), HoldSettings(power=1.0, duration=None))
        c_ac_relay.enable = MagicMock()
        assert not driver_12.enable.called
        self.advance_time_and_run(0.1)
        driver_12.enable.assert_called_with(PulseSettings(power=1.0, duration=10), HoldSettings(power=0.5, duration=None))
        driver_12.enable = MagicMock()

        # a side has preference. it should transition
        self.machine.coils["c_side_a2"].enable()
        self.machine_run()
        driver_12.disable.assert_called_with()
        c_ac_relay.disable.assert_called_with()
        c_ac_relay.disable = MagicMock()
        assert not driver_12.enable.called

        # it should enable a side coils now
        self.advance_time_and_run(0.075)
        driver_12.enable.assert_called_with(PulseSettings(power=1.0, duration=10), HoldSettings(power=0.5, duration=None))

        # disable driver on a side.
        self.machine.coils["c_side_a2"].disable()
        self.advance_time_and_run(0.2)

    def test_flippers(self):
        self.machine.flippers["f_test_single"].enable()
