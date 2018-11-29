import asyncio

from mpf.tests.MpfTestCase import MpfTestCase, MagicMock, patch, call


class TestOsc(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/osc/'

    def get_platform(self):
        # no force platform
        return False

    def setUp(self):
        client_class = patch('mpf.platforms.osc.SimpleUDPClient')
        self.client_class = client_class.start()
        self.client_instance = MagicMock()
        self.client_class.return_value = self.client_instance
        self.addCleanup(self.client_class.stop)
        super().setUp()

    def test_osc_light(self):
        self.client_instance.send_message = MagicMock()
        self.machine.lights["test_light1"].color("red")
        self.advance_time_and_run(.1)
        self.client_instance.send_message.assert_has_calls([
            call('/thing/light/blue/17', 0.0),
            call('/thing/light/green/17', 0.0),
            call('/thing/light/red/17', 1.0)], any_order=True)

        self.client_instance.send_message = MagicMock()
        self.machine.lights["test_light1"].color("blue")
        self.advance_time_and_run(.1)
        self.client_instance.send_message.assert_has_calls([
            call('/thing/light/blue/17', 1.0),
            call('/thing/light/green/17', 0.0),
            call('/thing/light/red/17', 0.0)], any_order=True)

        self.client_instance.send_message = MagicMock()
        self.machine.lights["test_light1"].color("white")
        self.advance_time_and_run(.1)
        self.client_instance.send_message.assert_has_calls([
            call('/thing/light/blue/17', 1.0),
            call('/thing/light/green/17', 1.0),
            call('/thing/light/red/17', 1.0)], any_order=True)
