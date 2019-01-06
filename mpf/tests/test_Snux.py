"""Test snux platform."""
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase, MagicMock
from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings


class TestSnux(MpfFakeGameTestCase):
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/snux/'

    def get_platform(self):
        # no force platform. we are testing virtual + snux
        return False

    def _get_snux_platform(self):
        return self.machine.hardware_platforms['snux']

    def _get_a_driver(self, coil):
        for driver in self._get_snux_platform().a_drivers:
            if driver.number + "a" == coil.hw_driver.number:
                return driver
        return False

    def _get_c_driver(self, coil):
        for driver in self._get_snux_platform().c_drivers:
            if driver.number + "c" == coil.hw_driver.number:
                return driver
        return False

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
        c_diag_led_driver = self.machine.coils.c_diag_led_driver
        c_diag_led_driver.pulse = MagicMock()
        self.advance_time_and_run(1)
        c_diag_led_driver.pulse.assert_called_with(250)

        # test if a and c side relays were properly loaded
        self.assertEqual(2, len(self._get_snux_platform().a_drivers))
        self.assertEqual(2, len(self._get_snux_platform().c_drivers))
        c_side_a1 = self._get_a_driver(self.machine.coils.c_side_a1)
        c_side_a2 = self._get_a_driver(self.machine.coils.c_side_a2)
        c_side_c1 = self._get_c_driver(self.machine.coils.c_side_c1)
        c_side_c2 = self._get_c_driver(self.machine.coils.c_side_c2)
        self.assertTrue(c_side_a1)
        self.assertTrue(c_side_a2)
        self.assertTrue(c_side_c1)
        self.assertTrue(c_side_c2)

        c_ac_relay = self.machine.coils.c_ac_relay
        c_ac_relay.enable = MagicMock()
        c_ac_relay.disable = MagicMock()

        c_side_a1.pulse = MagicMock()
        c_side_a2.enable = MagicMock()
        c_side_a2.disable = MagicMock()
        c_side_c1.pulse = MagicMock()
        c_side_c2.enable = MagicMock()
        c_side_c2.disable = MagicMock()

        # a side should be triggered first. c side should wait
        self.machine.coils.c_side_a1.pulse(50)
        self.machine.coils.c_side_c1.pulse(50)
        self.advance_time_and_run(0.001)
        c_side_a1.pulse.assert_called_with(PulseSettings(power=1.0, duration=50))
        c_side_a1.pulse = MagicMock()
        assert not c_side_c1.pulse.called
        assert not c_ac_relay.enable.called

        # after 50ms + 75ms transition c side should get triggered
        self.advance_time_and_run(0.075)
        c_ac_relay.enable.assert_called_with()
        c_ac_relay.enable = MagicMock()
        assert not c_side_a1.pulse.called
        assert not c_side_c1.pulse.called

        # after the relay switches. pulse the other coil
        self.advance_time_and_run(0.075)
        assert not c_side_a1.pulse.called
        c_side_c1.pulse.assert_called_with(PulseSettings(power=1.0, duration=50))

        # it should switch back to a side when idle
        self.advance_time_and_run(0.052)
        c_ac_relay.disable.assert_called_with()
        c_ac_relay.disable = MagicMock()

    def test_ac_switch_and_enable(self):

        c_side_a2 = self._get_a_driver(self.machine.coils.c_side_a2)
        c_side_c2 = self._get_c_driver(self.machine.coils.c_side_c2)

        c_side_a2.enable = MagicMock()
        c_side_a2.disable = MagicMock()
        c_side_c2.enable = MagicMock()
        c_side_c2.disable = MagicMock()

        c_ac_relay = self.machine.coils.c_ac_relay
        c_ac_relay.enable = MagicMock()
        c_ac_relay.disable = MagicMock()

        self.advance_time_and_run(0.10)

        # test enable on c side
        self.machine.coils.c_side_c2.enable()
        self.machine_run()
        c_ac_relay.enable.assert_called_with()
        c_ac_relay.enable = MagicMock()
        assert not c_side_c2.enable.called
        self.advance_time_and_run(0.075)
        c_side_c2.enable.assert_called_with(PulseSettings(power=1.0, duration=10), HoldSettings(power=0.5))

        # a side has preference. it should transition
        self.machine.coils.c_side_a2.enable()
        self.machine_run()
        c_side_c2.disable.assert_called_with()
        c_ac_relay.disable.assert_called_with()
        c_ac_relay.disable = MagicMock()
        assert not c_side_a2.enable.called

        # it should enable a side coils now
        self.advance_time_and_run(0.075)
        c_side_a2.enable.assert_called_with(PulseSettings(power=1.0, duration=10), HoldSettings(power=0.5))

        # disable driver on a side.
        self.machine.coils.c_side_a2.disable()
        self.advance_time_and_run(0.2)
