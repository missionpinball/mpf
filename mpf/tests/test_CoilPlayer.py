from mpf.tests.MpfTestCase import MpfTestCase
from mock import MagicMock


class TestCoilPlayer(MpfTestCase):

    def getConfigFile(self):
        return 'coil_player.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/coil_player/'

    def get_platform(self):
        return "smart_virtual"

    def test_express_config(self):
        coil = self.machine.coils['coil_1']
        coil.pulse = MagicMock()

        self.machine.events.post('event1')
        self.advance_time_and_run()

        coil.pulse.assert_called_with(power=1.0, priority=0)

    def test_pulse(self):
        coil = self.machine.coils['coil_1']
        coil.pulse = MagicMock()

        self.machine.events.post('event2')
        self.advance_time_and_run()

        coil.pulse.assert_called_with(power=1.0, priority=0)

    def test_pulse_with_attributes(self):
        coil = self.machine.coils['coil_1']
        coil.pulse = MagicMock()

        self.machine.events.post('event3')
        self.advance_time_and_run()

        coil.pulse.assert_called_with(power=1.0, ms=49, priority=0)

    def test_enable(self):
        coil = self.machine.coils['coil_1']
        coil.enable = MagicMock()

        self.machine.events.post('event4')
        self.advance_time_and_run()

        coil.enable.assert_called_with(power=1.0, priority=0)

    def test_disable(self):
        coil = self.machine.coils['coil_1']
        coil.disable = MagicMock()

        self.machine.events.post('event5')
        self.advance_time_and_run()

        coil.disable.assert_called_with(power=1.0, priority=0)
