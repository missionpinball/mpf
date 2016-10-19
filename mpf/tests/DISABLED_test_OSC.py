"""Test OSC."""
from mpf.plugins import osc
from mpf.plugins import auditor
from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class MockMessage:
    def __init__(self, cat):
        self.cat = cat
        self.data = None

    def append(self, data):
        self.data = data


class MockClient(MagicMock):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.messages = []

    def send(self, message):
        self.messages.append(message)


class TestOSC(MpfTestCase):

    def getConfigFile(self):
        if self._testMethodName == "test_audits":
            return "game.yaml"
        elif self._testMethodName in ["test_switch_wpc", "test_light_wpc"]:
            return "wpc.yaml"
        else:
            return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/osc/'

    def get_platform(self):
        return 'smart_virtual'

    def setUp(self):
        osc.import_success = True
        osc.OSCmodule = MagicMock()
        self.client = MockClient()
        osc.OSCmodule.OSCClient = MagicMock(return_value=self.client)
        osc.OSCmodule.OSCMessage = MockMessage
        osc.threading = MagicMock()

        self.machine_config_patches['mpf']['plugins'] = ['mpf.plugins.osc.OSC', 'mpf.plugins.auditor.Auditor']
        super().setUp()

        self.osc = self.machine.plugins[0]
        self.assertIsInstance(self.osc, osc.OSC)
        self.auditor = self.machine.auditor
        self.assertIsInstance(self.auditor, auditor.Auditor)
        # self.auditor.enable()
        # TODO: test audits

    def test_unknown_message(self):
        # should not crash
        self.osc.process_message("/garbage/asd/asd", [], [], "123")
        self.machine_run()

    def test_config(self):
        # currently it does nothing
        self.osc.process_message("/config", [], [], "123")
        self.machine_run()

    def test_refresh(self):
        # should not crash. is a noop
        self.osc.process_message("/refresh", [], [], "123")
        self.machine_run()

    def test_audits(self):

        self.expected_duration = 1.0

        self.osc.process_message("/audits", [], [], "123")
        self.machine_run()

        self.assertEqual(8, len(self.client.messages))
        self.client.messages.sort(key=lambda x: x.cat)

        i = 0
        self.assertEqual("/audits/player/score", self.client.messages[i].cat)
        self.assertEqual({'top': [], 'total': 0, 'average': 0}, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score/average", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score/total", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_ball", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_flipper", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_start", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/switch1", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/switch2", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)
        self.client.messages = []

        # enable auditor
        self.auditor.enable()

        self.osc.process_message("/audits", [], [], "123")
        self.machine_run()

        self.assertEqual(10, len(self.client.messages))
        self.client.messages.sort(key=lambda x: x.cat)
        i = 0
        self.assertEqual("/audits/events/game_ended", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/events/game_started", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score", self.client.messages[i].cat)
        self.assertEqual({'top': [], 'total': 0, 'average': 0}, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score/average", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score/total", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_ball", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_flipper", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_start", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/switch1", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/switch2", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)
        self.client.messages = []

        # hit a switch twice
        self.hit_switch_and_run("switch1", 1)
        self.release_switch_and_run("switch1", 1)
        self.hit_and_release_switch("switch1")
        self.assertEqual(4, len(self.client.messages))
        self.client.messages = []

        self.osc.process_message("/audits", [], [], "123")
        self.machine_run()

        self.assertEqual(10, len(self.client.messages))
        self.client.messages.sort(key=lambda x: x.cat)
        i = 0
        self.assertEqual("/audits/events/game_ended", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/events/game_started", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score", self.client.messages[i].cat)
        self.assertEqual({'top': [], 'total': 0, 'average': 0}, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score/average", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score/total", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_ball", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_flipper", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_start", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/switch1", self.client.messages[i].cat)
        self.assertEqual(2, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/switch2", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)
        self.client.messages = []

        self.machine.ball_controller.num_balls_known = 0
        self.hit_switch_and_run("s_ball", 1)

        # start a game
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run(100)

        # there should be a game
        self.assertNotEqual(None, self.machine.game)

        self.hit_switch_and_run("s_ball", 1)
        self.advance_time_and_run(100)

        self.assertEqual(None, self.machine.game)

        self.client.messages = []
        self.osc.process_message("/audits", [], [], "123")
        self.machine_run()

        self.assertEqual(11, len(self.client.messages))
        self.client.messages.sort(key=lambda x: x.cat)
        i = 0
        self.assertEqual("/audits/events/game_ended", self.client.messages[i].cat)
        self.assertEqual(1, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/events/game_started", self.client.messages[i].cat)
        self.assertEqual(1, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score", self.client.messages[i].cat)
        self.assertEqual({'top': [0], 'total': 1, 'average': 0.0}, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score/average", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score/top/1", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/player/score/total", self.client.messages[i].cat)
        self.assertEqual(1, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_ball", self.client.messages[i].cat)
        self.assertEqual(2, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_flipper", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/s_start", self.client.messages[i].cat)
        self.assertEqual(1, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/switch1", self.client.messages[i].cat)
        self.assertEqual(2, self.client.messages[i].data)

        i += 1
        self.assertEqual("/audits/switches/switch2", self.client.messages[i].cat)
        self.assertEqual(0, self.client.messages[i].data)
        self.client.messages = []

    def test_invalid_switch(self):
        # invalid switch should not crash
        self.client.send = MagicMock()
        self.osc.process_message("/sw/invalid_switch", [], ["1"], "123")
        self.machine_run()

        # should also not report the switch state back
        assert not self.client.send.called

    def test_switch_normal(self):
        self.hit_switch_and_run("s_flipper", 1)

        # set to name mode and get switches
        self.osc.process_message("/sync", [], [1], "123")
        self.machine_run()

        self.assertEqual(3, len(self.client.messages))
        self.client.messages.sort(key=lambda x: x.cat)
        self.assertEqual("/sw/s_flipper", self.client.messages[0].cat)
        self.assertEqual(1, self.client.messages[0].data)

        self.assertEqual("/sw/switch1", self.client.messages[1].cat)
        self.assertEqual(0, self.client.messages[1].data)

        self.assertEqual("/sw/switch2", self.client.messages[2].cat)
        self.assertEqual(0, self.client.messages[2].data)
        self.client.messages = []

        self.mock_event("switch1_active")
        self.mock_event("switch1_inactive")
        self.client.send = MagicMock()

        # switch active
        self.osc.process_message("/sw/switch1", [], ["1"], "123")
        self.machine_run()
        self.assertEqual(1, self._events["switch1_active"])
        self.assertEqual(0, self._events["switch1_inactive"])

        osc.OSCmodule.OSCClient.assert_called_once_with()
        self.client.connect.assert_called_once_with(('1', 8000))

        self.assertEqual(1, self.osc.osc_message.data)
        self.assertEqual("/sw/switch1", self.osc.osc_message.cat)
        self.client.send.assert_called_once_with(self.osc.osc_message)
        self.client.send = MagicMock()

        # switch inactive
        self.osc.process_message("/sw/switch1", [], ["0"], "123")
        self.machine_run()
        self.assertEqual(1, self._events["switch1_active"])
        self.assertEqual(1, self._events["switch1_inactive"])

        self.assertEqual(0, self.osc.osc_message.data)
        self.assertEqual("/sw/switch1", self.osc.osc_message.cat)
        self.client.send.assert_called_once_with(self.osc.osc_message)
        self.client.send = MagicMock()

        self.hit_switch_and_run("switch2", 1)
        self.assertEqual(1, self.osc.osc_message.data)
        self.assertEqual("/sw/switch2", self.osc.osc_message.cat)
        self.client.send.assert_called_once_with(self.osc.osc_message)

    def test_switch_wpc(self):
        self.hit_switch_and_run("s_flipper", 1)

        # set to wpc mode and get switches
        self.osc.process_message("/wpcsync", [], [1], "123")
        self.machine_run()

        self.assertEqual(3, len(self.client.messages))
        self.client.messages.sort(key=lambda x: x.cat)
        self.assertEqual("/sw/s1", self.client.messages[0].cat)
        self.assertEqual(0, self.client.messages[0].data)

        self.assertEqual("/sw/s2", self.client.messages[1].cat)
        self.assertEqual(0, self.client.messages[1].data)

        self.assertEqual("/sw/s3", self.client.messages[2].cat)
        self.assertEqual(1, self.client.messages[2].data)
        self.client.messages = []

        self.mock_event("switch1_active")
        self.mock_event("switch1_inactive")
        self.client.send = MagicMock()

        # switch active
        self.osc.process_message("/sw/1", [], ["1"], "123")
        self.machine_run()
        self.assertEqual(1, self._events["switch1_active"])
        self.assertEqual(0, self._events["switch1_inactive"])

        osc.OSCmodule.OSCClient.assert_called_once_with()
        self.client.connect.assert_called_once_with(('1', 8000))

        self.assertEqual(1, self.osc.osc_message.data)
        self.assertEqual("/sw/s1", self.osc.osc_message.cat)
        self.client.send.assert_called_once_with(self.osc.osc_message)
        self.client.send = MagicMock()

        # switch inactive (also works with name)
        self.osc.process_message("/sw/switch1", [], ["0"], "123")
        self.machine_run()
        self.assertEqual(1, self._events["switch1_active"])
        self.assertEqual(1, self._events["switch1_inactive"])

        self.assertEqual(0, self.osc.osc_message.data)
        self.assertEqual("/sw/s1", self.osc.osc_message.cat)
        self.client.send.assert_called_once_with(self.osc.osc_message)
        self.client.send = MagicMock()

        self.hit_switch_and_run("switch2", 1)
        self.assertEqual(1, self.osc.osc_message.data)
        self.assertEqual("/sw/s2", self.osc.osc_message.cat)
        self.client.send.assert_called_once_with(self.osc.osc_message)

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

    def test_invalid_light(self):
        # should not crash
        self.osc.process_message("/light/invalid_light", [], [0.1], "123")
        self.machine_run()

    def test_light_normal(self):
        self.assertFalse(self.osc.wpc)
        self.client.send = MagicMock()
        # put light on 10%
        self.machine.lights.light1.hw_driver.on = MagicMock()
        self.osc.process_message("/light/light1", [], [0.1], "123")
        self.advance_time_and_run(.02)
        self.machine.lights.light1.hw_driver.on.assert_called_once_with(25)

        self.advance_time_and_run(1)

        self.assertAlmostEqual(0.1, self.osc.osc_message.data, delta=0.05)
        self.assertEqual("/light/light1", self.osc.osc_message.cat)
        self.client.send.assert_called_once_with(self.osc.osc_message)
        self.client.send = MagicMock()

        # put light on 100%
        self.machine.lights.light1.hw_driver.on = MagicMock()
        self.osc.process_message("/light/light1", [], [1], "123")
        self.advance_time_and_run(.02)
        self.machine.lights.light1.hw_driver.on.assert_called_once_with(255)

        self.assertAlmostEqual(1.0, self.osc.osc_message.data, delta=0.05)
        self.assertEqual("/light/light1", self.osc.osc_message.cat)
        self.client.send.assert_called_once_with(self.osc.osc_message)

    def test_light_wpc(self):
        # set client to wpc mode. currently machine + client have to be WPC (unlike for switches)
        self.osc.process_message("/wpcsync", [], [1], "123")
        self.machine_run()

        self.assertTrue(self.osc.wpc)
        self.client.send = MagicMock()
        # put light on 10%
        self.machine.lights.light1.hw_driver.on = MagicMock()
        self.osc.process_message("/light/l77", [], [0.1], "123")
        self.advance_time_and_run(.02)
        self.machine.lights.light1.hw_driver.on.assert_called_once_with(25)

        self.advance_time_and_run(1)

        self.assertAlmostEqual(0.1, self.osc.osc_message.data, delta=0.05)
        self.assertEqual("/light/l77", self.osc.osc_message.cat)
        self.client.send.assert_called_once_with(self.osc.osc_message)
        self.client.send = MagicMock()

        # put light on 100% (should still work with name)
        self.machine.lights.light1.hw_driver.on = MagicMock()
        self.osc.process_message("/light/light1", [], [1], "123")
        self.advance_time_and_run(.02)
        self.machine.lights.light1.hw_driver.on.assert_called_once_with(255)

        self.assertAlmostEqual(1.0, self.osc.osc_message.data, delta=0.05)
        self.assertEqual("/light/l77", self.osc.osc_message.cat)
        self.client.send.assert_called_once_with(self.osc.osc_message)

        self.client.send = MagicMock()
        # put light2 on 100%. we skip the starting 0
        self.machine.lights.light2.hw_driver.on = MagicMock()
        self.osc.process_message("/light/2", [], [1], "123")
        self.advance_time_and_run(.02)
        self.machine.lights.light2.hw_driver.on.assert_called_once_with(255)

        self.assertAlmostEqual(1.0, self.osc.osc_message.data, delta=0.05)
        self.assertEqual("/light/02", self.osc.osc_message.cat)
        self.client.send.assert_called_once_with(self.osc.osc_message)

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
