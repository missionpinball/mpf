from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallDevice(MpfTestCase):
    def __init__(self, test_map):
        super().__init__(test_map)
        self._captured = 0
        self._enter = -1
        self._missing = 0
        self._requesting = 0
        self._queue = False

    def get_config_file(self):
        return 'test_ball_device.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def _missing_ball(self, **kwargs):
        del kwargs
        self._missing += 1

    def test_placeholder(self):
        template = self.machine.placeholder_manager.build_int_template(
            "device.ball_devices.test_launcher.balls", None)
        value, future = template.evaluate_and_subscribe([])
        self.assertEqual(0, value)
        self.assertFalse(future.done())
        self.hit_switch_and_run("s_ball_switch_launcher", 1)
        self.assertTrue(future.done())

    def test_ball_count_during_eject(self):
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        coil2.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)

        self._missing = 0
        self.assertEqual(0, self.machine.playfield.balls)
        self.assertEqual(0, self.machine.playfield.available_balls)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)
        self.assertEqual(1, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, self.machine.playfield.balls)
        self.assertEqual(1, self.machine.playfield.available_balls)

        self.assertTrue(coil2.pulse.called)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)

        self.assertEqual(0, self._missing)
        self.advance_time_and_run(300)
        self.assertEqual(1, self._missing)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, self.machine.playfield.available_balls)

    def _requesting_ball(self, balls, **kwargs):
        del kwargs
        self._requesting += balls

    def test_ball_eject_failed(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        coil2.pulse = MagicMock()

        self.machine.events.add_handler(
            'balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        # launcher should eject
        self.advance_time_and_run(1)
        self.assertTrue(coil2.pulse.called)

        self._captured = 0

        # launcher should retry eject
        self.advance_time_and_run(10)
        self.assertEqual(2, coil2.pulse.call_count)

        self.assertEqual(0, self._requesting)

        # it should not claim a ball which enters the target
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self._captured)

        self.advance_time_and_run(300)

    def test_ball_eject_timeout_and_late_confirm(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        coil2.pulse = MagicMock()
        self._missing = 0

        self.machine.events.add_handler(
            'balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        # launcher should eject
        self.advance_time_and_run(1)
        self.assertTrue(coil2.pulse.called)
        self._captured = 0

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        # but not confirm. eject timeout = 6s
        self.advance_time_and_run(15)
        self.assertTrue(coil2.pulse.called)

        # late confirm
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)

        self.assertEqual(0, self._requesting)
        self.assertEqual(0, self._missing)
        self.assertEqual(0, self._captured)

    def test_ball_left_and_return_failure(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        coil2.pulse = MagicMock()
        self._missing = 0

        self.machine.events.add_handler(
            'balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        # launcher should eject
        self.advance_time_and_run(1)
        self.assertTrue(coil2.pulse.called)
        self._captured = 0

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertTrue(coil2.pulse.called)

        # it comes back (before timeout)
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertTrue(coil2.pulse.called)

        # retry after timeout
        self.advance_time_and_run(5)
        self.assertEqual(2, coil2.pulse.call_count)

        self.assertEqual(0, self._captured)

        # ball did not leave the launcher (it returned). target should capture
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)

        self.assertEqual(0, self._requesting)
        self.assertEqual(0, self._missing)
        self.assertEqual(1, self._captured)

    def test_eject_retry(self):
        self.hit_switch_and_run("s_ball_switch1", 1)
        self.hit_switch_and_run("s_ball_switch2", 1)
        self.assertAvailableBallsOnPlayfield(0)

        coil2 = self.machine.coils['eject_coil2'].hw_driver

        self.mock_event('balldevice_test_launcher_ball_request')
        self.mock_event('balldevice_ball_missing')
        self.mock_event('balldevice_captured_from_playfield')

        # launcher should eject
        self.hit_switch_and_run("s_ball_switch_launcher", 1)
        self.assertEqual("pulsed_10", coil2.state)
        coil2.state = None
        self.assertEventCalled('balldevice_captured_from_playfield')
        self.mock_event('balldevice_captured_from_playfield')

        # it leaves the switch
        self.release_switch_and_run("s_ball_switch_launcher", 1)
        self.assertEqual(None, coil2.state)

        # it comes back (before timeout)
        self.hit_switch_and_run("s_ball_switch_launcher", 1)
        self.assertEqual(None, coil2.state)

        # retry after timeout
        self.advance_time_and_run(5)
        self.assertEqual("pulsed_10", coil2.state)
        coil2.state = None

        # ball leaves launcher
        self.release_switch_and_run("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)

        # arrives at target
        self.hit_switch_and_run("s_ball_switch_target1", 1)

        self.assertEqual(None, coil2.state)

        self.assertEventNotCalled('balldevice_captured_from_playfield')
        self.assertEventNotCalled('balldevice_ball_missing')
        self.assertEventNotCalled('balldevice_test_launcher_ball_request')
        self.assertAvailableBallsOnPlayfield(1)
        self.assertBallsOnPlayfield(0)

    def test_ball_eject_timeout_and_ball_missing(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()
        self._missing = 0
        self._captured = 0
        self._enter = 0

        self.mock_event("balldevice_test_launcher_ball_eject_failed")
        self.mock_event("balldevice_test_launcher_ball_eject_success")

        self.machine.events.add_handler(
            'balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_test_target1_ball_enter',
                                        self._ball_enter)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        # launcher should eject
        self.advance_time_and_run(1)
        self.assertTrue(coil2.pulse.called)
        self.assertEqual(1, self._captured)

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)

        # but not confirm. eject timeout = 6s
        self.advance_time_and_run(15)
        self.assertTrue(coil2.pulse.called)

        self.advance_time_and_run(30)

        self.assertEqual(0, self._requesting)
        self.assertEqual(1, self._missing)
        self.assertEqual(1, playfield.balls)

        self.assertEventNotCalled("balldevice_test_launcher_ball_eject_success")
        self.assertEventCalled("balldevice_test_launcher_ball_eject_failed")

        self._missing = 0
        self._requesting = 0
        self._captured = 0

        # target1 captures a ball since the eject failed
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)

        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)
        self.assertEqual(0, playfield.balls)

        # and ejects it
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, playfield.balls)

        self._captured = 0

        # launcher captures a ball and should retry
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(2, coil2.pulse.call_count)

        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)
        self.assertEqual(0, playfield.balls)

        self._captured = 0

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)

        # and reaches target which claims it
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)

        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)
        self.assertEqual(0, playfield.balls)

    def test_eject_successful_to_playfield(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        playfield = self.machine.ball_devices['playfield']

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request an ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        # target1 receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device3.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        self.assertTrue(coil3.pulse.called)
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device3.balls)

        # a ball hits a playfield switch
        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)

    def _ball_enter(self, new_balls, unclaimed_balls, **kwargs):
        del kwargs
        del new_balls
        if unclaimed_balls < 0:
            raise Exception("Balls went negative")

        self._enter += unclaimed_balls

    def _captured_from_pf(self, balls, **kwargs):
        del kwargs
        self._captured += balls

    def test_eject_successful_to_other_trough(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_test_target2_ball_enter',
                                        self._ball_enter)
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._enter = -1
        self._captured = 0
        self._missing = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self._captured)
        self._captured = -1

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request an ball
        device4.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEqual(-1, self._enter)
        self.assertEqual(-1, self._captured)

        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, self._missing)

    def test_eject_to_pf_and_other_trough(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = -1

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request ball
        device4.request_ball()
        self.advance_time_and_run(1)

        # request an ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)

        # eject of launcher should be confirmed now and the trough should eject
        self.assertEqual(2, coil1.pulse.call_count)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEqual(-1, self._captured)

        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, self._missing)

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertEqual(2, coil1.pulse.call_count)
        self.assertEqual(2, coil2.pulse.call_count)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # ball leaves launcher
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)

        # target1 receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device3.balls)

        self.assertEqual(2, coil1.pulse.call_count)
        self.assertEqual(2, coil2.pulse.call_count)
        self.assertTrue(coil3.pulse.called)
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device3.balls)

        # a ball hits a playfield switch
        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(-1, self._captured)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._missing)

    def test_eject_ok_to_receive(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = -1

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # request an ball to pf
        playfield.add_ball()
        self.advance_time_and_run(1)

        # request a second ball to pf
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        # target1 receives and should eject it right away
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device3.balls)

        # eject of launcher should be confirmed now and trough can eject
        # the next ball
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        self.assertTrue(coil3.pulse.called)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives a ball but cannot send it to target1 because its busy
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        self.assertTrue(coil3.pulse.called)

        self.assertEqual(-1, self._captured)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, self._missing)

        # ball left target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device3.balls)

        # wait for confirm
        self.advance_time_and_run(10)

        # launcher should now eject the second ball
        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        self.assertTrue(coil3.pulse.called)

        # ball leaves launcher
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)

        # target1 receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device3.balls)

        self.assertEqual(1, coil1.pulse.call_count)
        self.assertEqual(1, coil2.pulse.call_count)
        self.assertEqual(2, coil3.pulse.call_count)

        # ball left target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device3.balls)

        # wait for confirm
        self.advance_time_and_run(10)

        self.assertEqual(-1, self._captured)

        self.assertEqual(2, playfield.balls)
        self.assertEqual(0, self._missing)

        # check that timeout behave well
        self.advance_time_and_run(300)

    def test_temporary_missing_ball_idle(self):
        coil1 = self.machine.coils['eject_coil1']
        device1 = self.machine.ball_devices['test_trough']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        self.assertEqual(0, playfield.balls)

        # it should keep the balls
        coil1.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        self.assertEqual(2, device1.available_balls)

        # steal a ball from trough (only for a while)
        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(3)
        assert not coil1.pulse.called
        self.assertEqual(0, self._missing)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, playfield.available_balls)

        # still waiting
        self.assertEqual(2, device1.balls)
        self.assertEqual(2, device1.available_balls)

        # put it back
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        assert not coil1.pulse.called
        self.assertEqual(0, self._missing)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, playfield.available_balls)

        # count should be back
        self.assertEqual(2, device1.balls)
        self.assertEqual(2, device1.available_balls)

        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # steal a ball from trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(6)
        assert not coil1.pulse.called
        self.assertEqual(1, self._missing)
        self.assertEqual(0, self._captured)
        self.assertEqual(1, playfield.balls)
        self.assertEqual(1, playfield.available_balls)

        # count should be on less and one ball missing
        self.assertEqual(1, device1.balls)
        self.assertEqual(1, device1.available_balls)

        # put it back
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        assert not coil1.pulse.called
        self.assertEqual(1, self._missing)
        self.assertEqual(1, self._captured)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, playfield.available_balls)

        # count should be back
        self.assertEqual(2, device1.balls)
        self.assertEqual(2, device1.available_balls)

        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

    def test_missing_ball_idle(self):
        coil1 = self.machine.coils['eject_coil1']
        device1 = self.machine.ball_devices['test_trough']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0

        self.assertEqual(0, playfield.balls)

        # it should keep the balls
        coil1.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        self.assertEqual(2, device1.available_balls)

        # steal a ball from trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(6)
        assert not coil1.pulse.called
        self.assertEqual(1, self._missing)
        self.assertEqual(0, self._captured)
        self.assertEqual(1, playfield.balls)
        self.assertEqual(1, playfield.available_balls)

        # count should be on less and one ball missing
        self.assertEqual(1, device1.balls)
        self.assertEqual(1, device1.available_balls)

        # request an ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # ball randomly reappears
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._missing)
        self.assertEqual(1, self._captured)

    def test_ball_entry_during_eject(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0

        # assume there are more balls in the machine
        self.machine.ball_controller.num_balls_known = 4

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # assume there are already two balls on the playfield
        playfield.balls = 2
        playfield.available_balls = 2

        # request an ball to pf
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called

        # important: ball does not leave launcher here

        # target1 receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device3.balls)

        self.assertEqual(1, coil1.pulse.call_count)
        self.assertEqual(1, coil2.pulse.call_count)
        self.assertEqual(1, coil3.pulse.call_count)

        # ball left target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device3.balls)

        # wait for confirm via timeout
        self.advance_time_and_run(10)

        # target captured one ball because it did not leave the launcher
        self.assertEqual(1, self._captured)

        # there is no new ball on the playfield because the ball is still in the launcher
        self.assertEqual(2, playfield.balls)
        self.assertEqual(0, self._missing)

        # ball disappears from launcher
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        # eject times out
        self.advance_time_and_run(15)
        # ball goes missing and magically the playfield count is right again
        self.advance_time_and_run(40)
        self.assertEqual(1, self._missing)
        self.assertEqual(3, playfield.balls)

        # check that timeout behave well
        self.advance_time_and_run(300)

    def _block_eject(self, queue, **kwargs):
        del kwargs
        self._queue = queue
        queue.wait()

    def test_ball_entry_during_ball_requested(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil5 = self.machine.coils['eject_coil5']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device4 = self.machine.ball_devices['test_target2']
        target3 = self.machine.ball_devices['test_target3']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        coil5.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        # request ball
        target3.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # in the meantime device4 receives a (drained) ball
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 1)
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, device4.balls)
        self.assertEqual(2, self._captured)
        self._captured = 0

        # launcher receives but cannot ejects ball yet
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        # target 2 ejects to target 3
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        self.assertTrue(coil4.pulse.called)
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)

        # still no eject of launcher
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        self.assertTrue(coil4.pulse.called)
        assert not coil5.pulse.called

        # target 3 receives
        self.machine.switch_controller.process_switch("s_ball_switch_target3",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)

        # launcher should eject
        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        self.assertTrue(coil4.pulse.called)
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        self.assertEqual(1, target3.available_balls)

        # request another ball to target3 which already has a ball
        target3.request_ball()
        self.advance_time_and_run(1)
        self.assertEqual(2, target3.available_balls)

    def test_eject_attempt_blocking(self):
        # this test is a bit plastic. we hack get_additional_ball_capacity
        # the launcher device will try to do an eject while device4 is busy.
        # at the moment we cannot trigger this case but it may happen with
        # devices which wait before they eject
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil5 = self.machine.coils['eject_coil5']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device4 = self.machine.ball_devices['test_target2']
        target3 = self.machine.ball_devices['test_target3']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        coil5.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        # request ball
        target3.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # in the meantime target2 receives two (drained) balls
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 1)
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, device4.balls)
        self.assertEqual(2, self._captured)
        self._captured = 0

        # launcher receives but cannot ejects ball yet
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        # however launcher will try to eject because we hacked
        # get_additional_ball_capacity. device4 should block the eject

        # target 2 ejects to target 3
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        self.assertTrue(coil4.pulse.called)
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)

        # still no eject of launcher
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        self.assertTrue(coil4.pulse.called)
        assert not coil5.pulse.called

        # target 3 receives
        self.machine.switch_controller.process_switch("s_ball_switch_target3",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)

        # launcher should eject
        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        self.assertTrue(coil4.pulse.called)
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

    def test_two_concurrent_eject_to_pf_with_no_balls(self):
        coil3 = self.machine.coils['eject_coil3']
        coil5 = self.machine.coils['eject_coil5']
        target1 = self.machine.ball_devices['test_target1']
        target3 = self.machine.ball_devices['test_target3']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)

        coil3.pulse = MagicMock()
        coil5.pulse = MagicMock()

        # add a ball to target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        # add a ball to target3
        self.machine.switch_controller.process_switch("s_ball_switch_target3",
                                                      1)
        self.advance_time_and_run(1)

        self._captured = 0
        self._missing = 0

        # both should eject to pf
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, target1.balls)
        self.assertEqual(1, target3.balls)

        self.assertTrue(coil3.pulse.called)
        self.assertTrue(coil5.pulse.called)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      0)
        # add a ball to target3
        self.machine.switch_controller.process_switch("s_ball_switch_target3",
                                                      0)
        self.advance_time_and_run(1)

        # a ball hits a playfield switch
        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        # it should confirm only one device (no matter which one)
        self.assertEqual(1, playfield.balls)

        # second ball should be confirmed via timeout
        self.advance_time_and_run(10)
        self.assertEqual(2, playfield.balls)

        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

    def test_unstable_switches(self):
        device1 = self.machine.ball_devices['test_trough']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(0.4)
        # however, second switch is unstable
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(0.4)

        self.assertEqual(0, self._captured)
        self.assertEqual(0, device1.balls)
        self.assertEqual(0, playfield.balls)
        self.assertRaises(ValueError, device1.ball_count_handler.counter.count_balls_sync)

        # the the other one
        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(0.4)

        self.assertEqual(0, self._captured)
        self.assertEqual(0, device1.balls)
        self.assertEqual(0, playfield.balls)
        self.assertRaises(ValueError, device1.ball_count_handler.counter.count_balls_sync)

        self.advance_time_and_run(1)
        # but finally both are stable

        self.assertEqual(2, self._captured)
        self.assertEqual(2, device1.balls)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, self._missing)

        self.advance_time_and_run(100)
        self.assertEqual(2, self._captured)
        self.assertEqual(2, device1.balls)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, self._missing)
        #self.assertEqual("idle", device1._state)

    def test_permanent_eject_failure(self):
        coil1 = self.machine.coils['eject_coil1']
        device1 = self.machine.ball_devices['test_trough']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called

        # request ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        coil1.pulse = MagicMock()

        # timeout is 10s and max 3 retries
        # ball leaves (1st)
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # and comes back before timeout
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        # after the timeout it should retry
        self.advance_time_and_run(10)
        self.assertTrue(coil1.pulse.called)
        coil1.pulse = MagicMock()

        # ball leaves (2nd) for more than timeout
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(11)
        self.assertEqual(1, device1.balls)

        # and comes back
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        # trough should retry nearly instantly
        self.advance_time_and_run(1)
        self.assertTrue(coil1.pulse.called)
        coil1.pulse = MagicMock()

        # ball leaves (3rd)
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # and comes back before timeout
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        # after the timeout the device marks itself as broken and will give up
        self.advance_time_and_run(10)
        assert not coil1.pulse.called

        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)
        self.assertEqual("eject_broken", device1._state)

    def test_request_loops(self):
        # nobody has a ball and we request one. then we add a ball in the chain
        trough = self.machine.ball_devices['test_trough']
        launcher = self.machine.ball_devices['test_launcher']
        target1 = self.machine.ball_devices['test_target1']
        playfield = self.machine.ball_devices['playfield']

        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil5 = self.machine.coils['eject_coil5']

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        coil5.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # no initial balls
        # request ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        self.assertEqual(1, len(target1._ball_requests))
        # should not crash

        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        # trough captures2 a ball
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self._captured)
        self._captured = 0

        self.assertEqual(0, len(target1._ball_requests))

        # trough2 eject
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        self.assertTrue(coil4.pulse.called)
        assert not coil5.pulse.called
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 0)
        self.advance_time_and_run(1)

        # ball enters launcher2
        self.machine.switch_controller.process_switch("s_ball_switch_target3",
                                                      1)
        self.advance_time_and_run(1)

        # launcher2 eject
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        self.assertTrue(coil4.pulse.called)
        self.assertTrue(coil5.pulse.called)
        self.machine.switch_controller.process_switch("s_ball_switch_target3",
                                                      0)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        self.assertTrue(coil4.pulse.called)
        self.assertTrue(coil5.pulse.called)

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, trough.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, launcher.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        self.assertTrue(coil4.pulse.called)
        self.assertTrue(coil5.pulse.called)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)

        # target1 receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, target1.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        self.assertTrue(coil3.pulse.called)
        self.assertTrue(coil4.pulse.called)
        self.assertTrue(coil5.pulse.called)

        self.assertEqual(0, playfield.balls)
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      0)
        self.advance_time_and_run(1)
        self.advance_time_and_run(10)

        #self.assertEqual("idle", launcher._state)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)

    def test_unexpected_balls(self):
        launcher = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']

        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # launcher catches a random ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self._captured)
        self._captured = 0

        # trough2 eject
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)

        # ball enters target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)

        # target1 should put it to the playfield
        self.assertTrue(coil2.pulse.called)
        self.assertTrue(coil3.pulse.called)

        self.assertEqual(0, playfield.balls)
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      0)
        self.advance_time_and_run(1)
        self.advance_time_and_run(10)

        #self.assertEqual("idle", launcher._state)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)

    def test_balls_in_device_on_boot(self):
        # The device without the home tag should eject the ball
        # The device with the home tag should not eject the ball

        target1 = self.machine.ball_devices['test_target1']
        target2 = self.machine.ball_devices['test_target2']

        assert 'home' not in target1.tags
        assert 'home' in target2.tags

        # Put balls in both devices
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 1)

        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']

        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()

        self.advance_time_and_run(10)

        self.assertTrue(coil3.pulse.called)
        assert not coil4.pulse.called

    def _collecting_balls_complete_handler(self, **kwargs):
        del kwargs
        self._collecting_balls_complete = 1

    def test_ball_missing_to_pf_and_drain_no_switches(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        trough = self.machine.ball_devices['test_trough']
        launcher = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self.machine.events.add_handler('collecting_balls_complete',
                                        self._collecting_balls_complete_handler)

        self.assertEqual(None, self.machine.game)

        self._enter = 0
        self._captured = 0
        self._missing = 0
        self._collecting_balls_complete = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, playfield.available_balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEqual(2, trough.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # start a game
        self.machine.switch_controller.process_switch("s_start", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)

        # there should be a game
        self.assertNotEqual(None, self.machine.game)

        # playfield should expect to have a ball
        self.assertEqual(1, playfield.available_balls)
        self.assertEqual(0, playfield.balls)

        # trough ejects
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, trough.balls)

        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, launcher.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, launcher.balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(1, playfield.available_balls)
        self.assertEqual(0, playfield.balls)

        # the ball should go to target1. however, it jumps to the pf and drains
        # without hitting a switch on the pf

        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        # game should end
        self.assertEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # playfield has negative balls
        self.assertEqual(-1, playfield.balls)
        # but still expects one ball
        self.assertEqual(0, playfield.available_balls)

        self.advance_time_and_run(30)

        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, playfield.available_balls)

    def test_ball_missing_to_pf_and_drain_with_pf_switch(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        trough = self.machine.ball_devices['test_trough']
        launcher = self.machine.ball_devices['test_launcher']
        target = self.machine.ball_devices['test_target1']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self.machine.events.add_handler('collecting_balls_complete',
                                        self._collecting_balls_complete_handler)

        self.assertEqual(None, self.machine.game)

        self._enter = 0
        self._captured = 0
        self._missing = 0
        self._collecting_balls_complete = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEqual(2, trough.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # start a game
        self.machine.switch_controller.process_switch("s_start", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)

        # there should be a game
        self.assertNotEqual(None, self.machine.game)

        # trough ejects
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, trough.balls)

        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, launcher.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, launcher.balls)

        # the ball should go to target1. however, it jumps to the pf and hits
        # a switch

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # player plays a while
        self.advance_time_and_run(40)
        self.advance_time_and_run(40)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, len(target.incoming_balls_handler._incoming_balls))

        # ball drains
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        # game should end
        self.assertEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        self.advance_time_and_run(30)

        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, playfield.available_balls)

    def test_concurrent_capture_and_eject_unclaimed_balls(self):
        playfield = self.machine.ball_devices['playfield']
        coil5 = self.machine.coils['eject_coil5']
        coil5.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self._captured = 0
        self.machine.ball_controller.num_balls_known = 2
        playfield.available_balls = 2
        playfield.balls = 2

        # device captures two balls
        self.machine.switch_controller.process_switch("s_ball_switch_target3",
                                                      1)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target3_2", 1)
        self.advance_time_and_run(.6)
        self.assertEqual(2, self._captured)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(2, playfield.available_balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self._captured = 0

        # it should eject one
        self.assertTrue(coil5.pulse.called)
        coil5.pulse = MagicMock()
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("s_ball_switch_target3",
                                                      0)

        # wait for confirm
        self.advance_time_and_run(11)
        self.assertEqual(1, playfield.balls)

        # it should eject the second
        self.assertTrue(coil5.pulse.called)
        coil5.pulse = MagicMock()
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target3_2", 0)

        # wait for confirm
        self.advance_time_and_run(11)
        self.assertEqual(2, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(2, playfield.available_balls)

    def test_ball_request_when_device_is_full(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        trough = self.machine.ball_devices['test_trough']
        launcher = self.machine.ball_devices['test_launcher']
        target = self.machine.ball_devices['test_target1']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self.machine.events.add_handler('collecting_balls_complete',
                                        self._collecting_balls_complete_handler)

        self.assertEqual(None, self.machine.game)

        self._enter = 0
        self._captured = 0
        self._missing = 0
        self._collecting_balls_complete = 0

        # add initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEqual(2, trough.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # launcher requests a ball
        launcher.request_ball()
        self.advance_time_and_run(1)

        # trough ejects
        self.assertTrue(coil1.pulse.called)
        coil1.pulse = MagicMock()
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, trough.balls)

        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, launcher.balls)
        self.assertEqual(1, launcher.available_balls)

        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # launcher requests a second ball (but already has one)
        launcher.request_ball()
        self.advance_time_and_run(1)

        # launcher is full so nothing should happen
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        self.assertEqual(1, launcher.balls)
        self.assertEqual(2, launcher.available_balls)

        # target1 requests a ball
        target.request_ball()
        self.advance_time_and_run(1)

        # launcher shoots the ball
        assert not coil1.pulse.called
        self.assertTrue(coil2.pulse.called)
        coil2.pulse = MagicMock()
        assert not coil3.pulse.called

        # ball leaves
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, launcher.balls)

        # no eject of trough yet
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # target receives
        self.machine.switch_controller.process_switch("s_ball_switch_target1",
                                                      1)
        self.advance_time_and_run(1)

        # trough ejects
        self.assertTrue(coil1.pulse.called)
        coil1.pulse = MagicMock()
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, trough.balls)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, launcher.balls)

        self.assertEqual("idle", trough._state)
        self.assertEqual("idle", launcher._state)
        self.assertEqual("idle", target._state)

    def test_entrance_switch_ignore_window(self):
        """Verify that an entrance switch doesn't hit during the ignore window."""
        self.mock_event("balldevice_captured_from_playfield")

        # First call should register the capture
        self.machine.switch_controller.process_switch("s_entrance", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_entrance", 0)
        self.advance_time_and_run(0.1)
        self.assertEventCalled("balldevice_captured_from_playfield", times=1)

        # Second call, 2 seconds later, should be ignored
        self.advance_time_and_run(2)
        self.machine.switch_controller.process_switch("s_entrance", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_entrance", 0)
        self.advance_time_and_run(0.1)
        self.assertEventCalled("balldevice_captured_from_playfield", times=1)

        # Third call, 2 seconds later, should capture
        self.advance_time_and_run(2)
        self.machine.switch_controller.process_switch("s_entrance", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_entrance", 0)
        self.advance_time_and_run(0.1)
        self.assertEventCalled("balldevice_captured_from_playfield", times=2)
