from mpf.tests.MpfTestCase import MpfTestCase, MagicMock, patch, call


class TestOsc(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/osc/'

    def get_platform(self):
        # no force platform
        return False

    async def _start_serve(self):
        return MagicMock(), None

    def setUp(self):
        client_class = patch('mpf.platforms.osc.SimpleUDPClient')
        self.client_class = client_class.start()
        self.client_instance = MagicMock()
        self.client_class.return_value = self.client_instance

        dispatcher_class = patch('mpf.platforms.osc.Dispatcher')
        self.dispatcher_class = dispatcher_class.start()
        self.dispatcher_instance = MagicMock()
        self.dispatcher_class.return_value = self.dispatcher_instance

        server_class = patch('mpf.platforms.osc.AsyncIOOSCUDPServer')
        self.server_class = server_class.start()
        self.server_instance = MagicMock()
        self.server_instance.create_serve_endpoint = self._start_serve
        self.server_class.return_value = self.server_instance

        self.addCleanup(self.client_class.stop)
        self.addCleanup(self.dispatcher_class.stop)
        self.addCleanup(self.server_class.stop)
        super().setUp()

    def test_osc_platform(self):
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

        # send switch hits
        self.assertSwitchState("switch_abc", False)
        self.machine.default_platform._handle_switch("/sw/abc", True)
        self.advance_time_and_run(.1)
        self.assertSwitchState("switch_abc", True)
        self.machine.default_platform._handle_switch("/sw/abc", False)
        self.advance_time_and_run(.1)
        self.assertSwitchState("switch_abc", False)

        self.assertSwitchState("switch_1", False)
        self.machine.default_platform._handle_switch("/sw/1", True)
        self.advance_time_and_run(.1)
        self.assertSwitchState("switch_1", True)
        self.machine.default_platform._handle_switch("/sw/1", False)
        self.advance_time_and_run(.1)
        self.assertSwitchState("switch_1", False)
