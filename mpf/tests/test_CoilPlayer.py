from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestCoilPlayer(MpfTestCase):

    def getConfigFile(self):
        return 'coil_player.yaml'

    def getMachinePath(self):
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

        self.assertTrue(coil.hw_driver.pulse.called)
        assert not coil.hw_driver.enable.called

        # coil without allow_enable
        coil = self.machine.coils['coil_2']
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()

        self.machine.events.post('event6')
        self.advance_time_and_run()

        self.assertTrue(coil.hw_driver.pulse.called)
        assert not coil.hw_driver.enable.called

        coil = self.machine.coils['coil_3']
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()
        coil.hw_driver.disable = MagicMock()

        self.post_event("event7")
        self.advance_time_and_run()
        self.assertTrue(coil.hw_driver.enable.called)
        assert not coil.hw_driver.disable.called
        assert not coil.hw_driver.pulse.called
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()
        coil.hw_driver.disable = MagicMock()

        self.post_event("event8")
        self.advance_time_and_run()
        self.assertTrue(coil.hw_driver.disable.called)
        assert not coil.hw_driver.enable.called
        assert not coil.hw_driver.pulse.called
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()
        coil.hw_driver.disable = MagicMock()

        self.post_event("event9")
        self.advance_time_and_run()
        self.assertTrue(coil.hw_driver.pulse.called)
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

        self.assertTrue(coil.hw_driver.pulse.called)
        assert not coil.hw_driver.enable.called

        self.assertTrue(coil2.hw_driver.pulse.called)
        assert not coil2.hw_driver.enable.called

        # post same event again
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()
        coil2.hw_driver.pulse = MagicMock()
        coil2.hw_driver.enable = MagicMock()
        self.machine.events.post('event2')
        self.advance_time_and_run()

        self.assertTrue(coil.hw_driver.pulse.called)
        assert not coil.hw_driver.enable.called

        self.assertTrue(coil2.hw_driver.pulse.called)
        assert not coil2.hw_driver.enable.called

    def test_pulse_with_attributes(self):
        coil = self.machine.coils['coil_1']
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.enable = MagicMock()

        self.machine.events.post('event3')
        self.advance_time_and_run()

        self.assertTrue(coil.hw_driver.pulse.called)
        assert not coil.hw_driver.enable.called

    def test_enable_and_disable(self):
        coil = self.machine.coils['coil_1']
        coil.hw_driver.enable = MagicMock()
        coil.hw_driver.pulse = MagicMock()
        coil.hw_driver.disable = MagicMock()

        self.machine.events.post('event4')
        self.advance_time_and_run()

        self.assertTrue(coil.hw_driver.enable.called)
        assert not coil.hw_driver.pulse.called

        self.machine.events.post('event5')
        self.advance_time_and_run()

        self.assertTrue(coil.hw_driver.disable.called)

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
        self.assertTrue(coil.hw_driver.enable.called)
        coil.hw_driver.enable = MagicMock()
        self.assertFalse(coil.hw_driver.disable.called)

        # on mode stop the coil player should disable the coil
        self.post_event("stop_mode1", 1)
        self.assertFalse(coil.hw_driver.enable.called)
        self.assertTrue(coil.hw_driver.disable.called)
