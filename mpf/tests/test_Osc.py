from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from mpf.tests.MpfTestCase import MagicMock, patch, call


class TestOsc(MpfFakeGameTestCase):

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
        # test lights
        self.client_instance.send_message = MagicMock()
        self.machine.lights["test_light1"].color("red")
        self.advance_time_and_run(.1)
        self.client_instance.send_message.assert_has_calls([
            call('/light/light1/blue', 0.0),
            call('/light/light1/green', 0.0),
            call('/light/light1/red', 1.0)], any_order=True)

        self.client_instance.send_message = MagicMock()
        self.machine.lights["test_light1"].color("blue")
        self.advance_time_and_run(.1)
        self.client_instance.send_message.assert_has_calls([
            call('/light/light1/blue', 1.0),
            call('/light/light1/green', 0.0),
            call('/light/light1/red', 0.0)], any_order=True)

        self.client_instance.send_message = MagicMock()
        self.machine.lights["test_light1"].color("white")
        self.advance_time_and_run(.1)
        self.client_instance.send_message.assert_has_calls([
            call('/light/light1/blue', 1.0),
            call('/light/light1/green', 1.0),
            call('/light/light1/red', 1.0)], any_order=True)

        self.client_instance.send_message = MagicMock()
        self.machine.lights["test_light2"].color("white")
        self.advance_time_and_run(.1)
        self.client_instance.send_message.assert_has_calls([
            call('/light/light2/blue', 1.0),
            call('/light/light2/green', 1.0),
            call('/light/light2/red', 1.0)], any_order=True)

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

        # test outgoing events
        self.client_instance.send_message = MagicMock()
        self.post_event_with_params("my_test_event", a=100, b=True)
        self.advance_time_and_run(.1)
        self.client_instance.send_message.assert_has_calls([
            call('/event/my_test_event', ['a', 100, 'b', True])
        ], any_order=True)

        self.client_instance.send_message = MagicMock()
        self.post_event("my_other_test_event")
        self.advance_time_and_run(.1)
        self.client_instance.send_message.assert_has_calls([
            call('/event/my_other_test_event', [])
        ], any_order=True)

        # test incoming events
        self.mock_event("test_event")
        self.machine.default_platform._handle_event("/event/test_event", "a", 200, "b", "asd")
        self.advance_time_and_run(.1)
        self.assertEventCalledWith("test_event", a=200, b="asd")

        self.start_game()
        self.advance_time_and_run()

        self.client_instance.send_message.assert_has_calls([
            call('/event/player_turn_started', ['number', 1, 'player', '<Player 1>'])
        ], any_order=True)
