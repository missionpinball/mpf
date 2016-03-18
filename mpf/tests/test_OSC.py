from mpf.plugins import osc
from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import patch, MagicMock


class TestOSC(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/osc/'

    def setUp(self):
        osc.import_success = True
        osc.OSCmodule = MagicMock()

        self.machine_config_patches['mpf']['plugins'] = ['mpf.plugins.osc.OSC']
        super().setUp()

        self.osc = self.machine.plugins[0]
        self.assertIsInstance(self.osc, osc.OSC)

    def test_switch(self):
        self.mock_event("switch1_active")
        self.mock_event("switch1_inactive")

        # switch active
        self.osc.process_message("/sw/switch1", [], ["1"], "123")
        self.machine_run()
        self.assertEqual(1, self._events["switch1_active"])
        self.assertEqual(0, self._events["switch1_inactive"])

        # switch inactive
        self.osc.process_message("/sw/switch1", [], ["0"], "123")
        self.machine_run()
        self.assertEqual(1, self._events["switch1_active"])
        self.assertEqual(1, self._events["switch1_inactive"])

    def test_event(self):
        self.mock_event("test_event")

        # trigger event
        self.osc.process_message("/ev/test_event", [], [], "123")
        self.machine_run()
        self.assertEqual(1, self._events["test_event"])

    def test_coil(self):
        self.machine.coils.coil1.pulse = MagicMock()

        self.osc.process_message("/coil/coil1", [], [], "123")
        self.machine_run()
        self.machine.coils.coil1.pulse.assert_called_once_with()

    def test_light(self):
        # put light on 10%
        self.machine.lights.light1.on = MagicMock()
        self.osc.process_message("/light/light1", [], [0.1], "123")
        self.machine_run()
        self.machine.lights.light1.on.assert_called_once_with(25)

        # put light on 100%
        self.machine.lights.light1.on = MagicMock()
        self.osc.process_message("/light/light1", [], [1], "123")
        self.machine_run()
        self.machine.lights.light1.on.assert_called_once_with(255)

    def test_flipper(self):
        self.machine.coils.c_flipper.enable = MagicMock()
        self.machine.coils.c_flipper.disable = MagicMock()

        self.osc.process_message("/flipper/flipper_left", [], [1], "123")
        self.machine_run()
        self.machine.coils.c_flipper.enable.assert_called_once_with()
        assert not self.machine.coils.c_flipper.disable.called

        self.machine.coils.c_flipper.enable = MagicMock()
        self.osc.process_message("/flipper/flipper_left", [], [0], "123")
        self.machine_run()
        self.machine.coils.c_flipper.disable.assert_called_once_with()
        assert not self.machine.coils.c_flipper.enable.called
