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
        coil.pulse = MagicMock()
        coil.enable = MagicMock()

        self.machine.events.post('event1')
        self.advance_time_and_run()

        coil.pulse.assert_called_with(power=1.0, priority=0)
        assert not coil.enable.called

        # coil without allow_enable
        coil = self.machine.coils['coil_2']
        coil.pulse = MagicMock()
        coil.enable = MagicMock()

        self.machine.events.post('event6')
        self.advance_time_and_run()

        coil.pulse.assert_called_with(power=1.0, priority=0)
        assert not coil.enable.called

        coil = self.machine.coils['coil_3']
        coil.pulse = MagicMock()
        coil.enable = MagicMock()
        coil.disable = MagicMock()

        self.post_event("event7")
        self.advance_time_and_run()
        coil.enable.assert_called_with(power=1.0, priority=0)
        assert not coil.disable.called
        assert not coil.pulse.called
        coil.pulse = MagicMock()
        coil.enable = MagicMock()
        coil.disable = MagicMock()

        self.post_event("event8")
        self.advance_time_and_run()
        coil.disable.assert_called_with(power=1.0, priority=0)
        assert not coil.enable.called
        assert not coil.pulse.called
        coil.pulse = MagicMock()
        coil.enable = MagicMock()
        coil.disable = MagicMock()

        self.post_event("event9")
        self.advance_time_and_run()
        coil.pulse.assert_called_with(milliseconds=30, power=1.0, priority=0)
        assert not coil.disable.called
        assert not coil.enable.called

    def test_pulse(self):
        coil = self.machine.coils['coil_1']
        coil.pulse = MagicMock()
        coil.enable = MagicMock()

        # coil without allow_enable
        coil2 = self.machine.coils['coil_2']
        coil2.pulse = MagicMock()
        coil2.enable = MagicMock()

        self.machine.events.post('event2')
        self.advance_time_and_run()

        coil.pulse.assert_called_with(power=1.0, priority=0)
        assert not coil.enable.called

        coil2.pulse.assert_called_with(power=1.0, priority=0)
        assert not coil2.enable.called

        # post same event again
        self.machine.events.post('event2')
        self.advance_time_and_run()

        coil.pulse.assert_called_with(power=1.0, priority=0)
        assert not coil.enable.called

        coil2.pulse.assert_called_with(power=1.0, priority=0)
        assert not coil2.enable.called

    def test_pulse_with_attributes(self):
        coil = self.machine.coils['coil_1']
        coil.pulse = MagicMock()
        coil.enable = MagicMock()

        self.machine.events.post('event3')
        self.advance_time_and_run()

        coil.pulse.assert_called_with(power=1.0, ms=49, priority=0)
        assert not coil.enable.called

    def test_enable(self):
        coil = self.machine.coils['coil_1']
        coil.enable = MagicMock()
        coil.pulse = MagicMock()

        self.machine.events.post('event4')
        self.advance_time_and_run()

        coil.enable.assert_called_with(power=1.0, priority=0)
        assert not coil.pulse.called

    def test_disable(self):
        coil = self.machine.coils['coil_1']
        coil.disable = MagicMock()

        self.machine.events.post('event5')
        self.advance_time_and_run()

        coil.disable.assert_called_with(power=1.0, priority=0)
