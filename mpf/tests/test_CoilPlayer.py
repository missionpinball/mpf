from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings
from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestCoilPlayer(MpfTestCase):

    def get_config_file(self):
        return 'coil_player.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/coil_player/'

    def get_platform(self):
        return "smart_virtual"

    def test_express_config(self):
        # coil with allow_enable set
        coil = self.machine.coils['coil_1']
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()

        self.machine.events.post('event1')
        self.advance_time_and_run()

        coil.hw_driver.pulse.assert_called_with(PulseSettings(power=1.0, duration=10))
        assert not coil.hw_driver.enable.called

        # coil without allow_enable
        coil = self.machine.coils['coil_2']
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()

        self.machine.events.post('event6')
        self.advance_time_and_run()

        coil.hw_driver.pulse.assert_called_with(PulseSettings(power=1.0, duration=10))
        assert not coil.hw_driver.enable.called

        coil = self.machine.coils['coil_3']
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()
        coil.hw_driver.disable = MagicMock()

        self.post_event("event7")
        self.advance_time_and_run()
        coil.hw_driver.enable.assert_called_with(PulseSettings(power=1.0, duration=10), HoldSettings(power=0.5))
        assert not coil.hw_driver.disable.called
        assert not coil.hw_driver.pulse.called
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()
        coil.hw_driver.disable = MagicMock()

        self.post_event("event8")
        self.advance_time_and_run()
        coil.hw_driver.disable.assert_called_with()
        assert not coil.hw_driver.enable.called
        assert not coil.hw_driver.pulse.called
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()
        coil.hw_driver.disable = MagicMock()

        self.post_event("event9")
        self.advance_time_and_run()
        coil.hw_driver.pulse.assert_called_with(PulseSettings(power=1.0, duration=30))
        assert not coil.hw_driver.disable.called
        assert not coil.hw_driver.enable.called

    def test_pulse(self):
        coil = self.machine.coils['coil_1']
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()

        # coil without allow_enable
        coil2 = self.machine.coils['coil_2']
        coil2.hw_driver.pulse = MagicMock()
        coil2.hw_driver.enable = MagicMock()

        self.machine.events.post('event2')
        self.advance_time_and_run()

        coil.hw_driver.pulse.assert_called_with(PulseSettings(power=1.0, duration=10))
        assert not coil.hw_driver.enable.called

        coil2.hw_driver.pulse.assert_called_with(PulseSettings(power=0.5, duration=10))
        assert not coil2.hw_driver.enable.called

        # post same event again
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()
        coil2.hw_driver.pulse = MagicMock()
        coil2.hw_driver.enable = MagicMock()
        self.machine.events.post('event2')
        self.advance_time_and_run()

        coil.hw_driver.pulse.assert_called_with(PulseSettings(power=1.0, duration=10))
        assert not coil.hw_driver.enable.called

        coil2.hw_driver.pulse.assert_called_with(PulseSettings(power=0.5, duration=10))
        assert not coil2.hw_driver.enable.called

    def test_pulse_with_attributes(self):
        coil = self.machine.coils['coil_1']
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()

        self.machine.events.post('event3')
        self.advance_time_and_run()

        coil.hw_driver.pulse.assert_called_with(PulseSettings(power=1.0, duration=49))
        assert not coil.hw_driver.enable.called

    def test_enable_and_disable(self):
        coil = self.machine.coils['coil_1']
        coil.hw_driver.enable = MagicMock()
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.disable = MagicMock()

        self.machine.events.post('event4')
        self.advance_time_and_run()

        coil.hw_driver.enable.assert_called_with(PulseSettings(power=1.0, duration=10), HoldSettings(power=1.0))
        assert not coil.hw_driver.pulse.called

        self.machine.events.post('event5')
        self.advance_time_and_run()

        coil.hw_driver.disable.assert_called_with()

        # same again but use on and off instead of enable and disable
        coil.hw_driver.enable = MagicMock()
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.disable = MagicMock()

        self.machine.events.post('event10')
        self.advance_time_and_run()

        coil.hw_driver.enable.assert_called_with(PulseSettings(power=1.0, duration=10), HoldSettings(power=1.0))
        assert not coil.hw_driver.pulse.called

        self.machine.events.post('event11')
        self.advance_time_and_run()

        coil.hw_driver.disable.assert_called_with()

    def test_coil_player_in_mode(self):
        coil = self.machine.coils['coil_3']
        coil.hw_driver.enable = MagicMock()
        coil.hw_driver.disable = MagicMock()

        # start mode
        self.post_event("start_mode1", 1)
        self.assertFalse(coil.hw_driver.enable.called)
        self.assertFalse(coil.hw_driver.disable.called)

        # enable coil
        self.post_event("event1_mode", 1)
        coil.hw_driver.enable.assert_called_with(PulseSettings(power=1.0, duration=10), HoldSettings(power=1.0))
        coil.hw_driver.enable = MagicMock()
        self.assertFalse(coil.hw_driver.disable.called)

        # on mode stop the coil player should disable the coil
        self.post_event("stop_mode1", 1)
        self.assertFalse(coil.hw_driver.enable.called)
        coil.hw_driver.disable.assert_called_with()

    def test_max_wait_ms(self):
        coil = self.machine.coils['coil_1']
        self.post_event("pulse_1_100")
        self.advance_time_and_run(.05)
        self.assertEqual("pulsed_100", coil.hw_driver.state)
        self.post_event("pulse_1_50_max_wait_ms")
        # still the same
        self.assertEqual("pulsed_100", coil.hw_driver.state)
        # after pulse end
        self.advance_time_and_run(.06)
        self.assertEqual("pulsed_50", coil.hw_driver.state)
