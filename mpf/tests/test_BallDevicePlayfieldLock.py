from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestBallDevicePlayfieldLock(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'test_playfield_lock.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_device/'

    def get_platform(self):
        return 'smart_virtual'

    def test_entry_during_eject(self):
        self.start_game()
        self.mock_event("balldevice_test_device_ball_eject_failed")
        self.mock_event("balldevice_test_device_ball_eject_success")

        # lock a ball
        self.hit_switch_and_run("s_ball_switch1", 10)
        self.assertEqual(1, self.machine.ball_devices.test_device.available_balls)

        # new ball rolls in
        self.post_event("entrance_event")

        # release ball
        self.post_event("release_test")
        self.advance_time_and_run(.1)
        self.assertEqual(0, self.machine.ball_devices.test_device.available_balls)

        # capture a new ball concurrently
        self.hit_switch_and_run("s_ball_switch2", 20)
        self.assertEventNotCalled("balldevice_test_device_ball_eject_failed")
        self.assertEventCalled("balldevice_test_device_ball_eject_success")
        self.mock_event("balldevice_test_device_ball_eject_failed")
        self.mock_event("balldevice_test_device_ball_eject_success")

        # locked another ball
        self.assertEqual(1, self.machine.ball_devices.test_device.available_balls)

        # release another ball
        self.post_event("release_test")
        self.advance_time_and_run(.1)
        self.assertEqual(0, self.machine.ball_devices.test_device.available_balls)

        # no entrance but a new ball
        self.hit_switch_and_run("s_ball_switch2", 20)
        self.assertEventCalled("balldevice_test_device_ball_eject_failed")
        self.assertEventNotCalled("balldevice_test_device_ball_eject_success")

