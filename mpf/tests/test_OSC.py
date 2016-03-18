from mpf.plugins import osc
from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import patch, MagicMock


class MockMessage:
    def __init__(self, cat):
        self.cat = cat
        self.data = None

    def append(self, data):
        self.data = data


class TestOSC(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/osc/'

    def setUp(self):
        osc.import_success = True
        osc.OSCmodule = MagicMock()
        self.client = MagicMock()
        osc.OSCmodule.OSCClient = MagicMock(return_value=self.client)
        osc.OSCmodule.OSCMessage = MockMessage

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

        osc.OSCmodule.OSCClient.assert_called_once_with()
        self.client.connect.assert_called_once_with(('1', 8000))

        self.assertEqual(1, self.osc.OSC_message.data)
        self.assertEqual("/sw/switch1", self.osc.OSC_message.cat)
        self.client.send.assert_called_once_with(self.osc.OSC_message)
        self.client.send = MagicMock()

        # switch inactive
        self.osc.process_message("/sw/switch1", [], ["0"], "123")
        self.machine_run()
        self.assertEqual(1, self._events["switch1_active"])
        self.assertEqual(1, self._events["switch1_inactive"])

        self.assertEqual(0, self.osc.OSC_message.data)
        self.assertEqual("/sw/switch1", self.osc.OSC_message.cat)
        self.client.send.assert_called_once_with(self.osc.OSC_message)
        self.client.send = MagicMock()

        self.hit_switch_and_run("switch2", 1)
        self.assertEqual(1, self.osc.OSC_message.data)
        self.assertEqual("/sw/switch2", self.osc.OSC_message.cat)
        self.client.send.assert_called_once_with(self.osc.OSC_message)

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
        self.machine.lights.light1.hw_driver.on = MagicMock()
        self.osc.process_message("/light/light1", [], [0.1], "123")
        self.machine_run()
        self.machine.lights.light1.hw_driver.on.assert_called_once_with(25)

        self.advance_time_and_run(1)

        self.assertAlmostEqual(0.1, self.osc.OSC_message.data, delta=0.05)
        self.assertEqual("/light/light1", self.osc.OSC_message.cat)
        self.client.send.assert_called_once_with(self.osc.OSC_message)
        self.client.send = MagicMock()

        # put light on 100%
        self.machine.lights.light1.hw_driver.on = MagicMock()
        self.osc.process_message("/light/light1", [], [1], "123")
        self.machine_run()
        self.machine.lights.light1.hw_driver.on.assert_called_once_with(255)

        self.assertAlmostEqual(1.0, self.osc.OSC_message.data, delta=0.05)
        self.assertEqual("/light/light1", self.osc.OSC_message.cat)
        self.client.send.assert_called_once_with(self.osc.OSC_message)

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
