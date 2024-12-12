from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallDevicesHoldCoil(MpfTestCase):
    def get_config_file(self):
        return 'test_hold_coil.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def setUp(self):
        super().setUp()
        self.machine.ball_controller.num_balls_known = 99
        self.machine.playfield.balls = 10
        self.machine.playfield.available_balls = 10

    def test_holdcoil_with_direct_release(self):
        self.machine.coils['hold_coil'].enable = MagicMock()
        self.machine.coils['hold_coil'].disable = MagicMock()
        # after hold switch was posted it should enable the hold_coil
        self.machine.events.post('test_hold_event')
        self.advance_time_and_run(0.1)
        self.machine.coils['hold_coil'].enable.assert_called_once_with()
        assert not self.machine.coils['hold_coil'].disable.called

        # wait some more. coil should stay active
        self.advance_time_and_run(300)
        self.machine.coils['hold_coil'].enable.assert_called_once_with()
        assert not self.machine.coils['hold_coil'].disable.called

        # we trigger entrance switch
        self.assertEqual(0, self.machine.ball_devices['test'].balls)
        self.machine.coils['hold_coil'].enable = MagicMock()
        self.machine.coils['hold_coil'].disable = MagicMock()
        self.machine.switch_controller.process_switch(name='s_entrance', state=1)
        self.machine.switch_controller.process_switch(name='s_entrance', state=0)

        self.advance_time_and_run(300)
        self.assertEqual(0, self.machine.ball_devices['test'].balls)

        # the device should eject the ball right away because nobody claimed it
        self.machine.coils['hold_coil'].disable.assert_called_once_with()
        assert not self.machine.coils['hold_coil'].enable.called

    def test_holdcoil_which_keeps_ball(self):
        # add one ball
        self.assertEqual(0, self.machine.ball_devices['test2'].balls)
        self.machine.coils['hold_coil2'].enable = MagicMock()
        self.machine.coils['hold_coil2'].disable = MagicMock()
        self.machine.events.post('test_hold_event2')
        self.machine.switch_controller.process_switch(name='s_entrance2', state=1)
        self.machine.switch_controller.process_switch(name='s_entrance2', state=0)

        self.advance_time_and_run(300)
        self.machine.coils['hold_coil2'].enable.assert_called_once_with()
        assert not self.machine.coils['hold_coil2'].disable.called
        self.assertEqual(1, self.machine.ball_devices['test2'].balls)

        # add a second ball
        self.machine.coils['hold_coil2'].enable = MagicMock()
        self.machine.coils['hold_coil2'].disable = MagicMock()
        self.machine.events.post('test_hold_event2')
        self.machine.switch_controller.process_switch(name='s_entrance2', state=1)
        self.machine.switch_controller.process_switch(name='s_entrance2', state=0)
        self.advance_time_and_run(300)
        self.machine_run()
        self.machine.coils['hold_coil2'].enable.assert_called_once_with()
        assert not self.machine.coils['hold_coil2'].disable.called
        self.assertEqual(2, self.machine.ball_devices['test2'].balls)

        # eject one ball
        self.machine.coils['hold_coil2'].enable = MagicMock()
        self.machine.coils['hold_coil2'].disable = MagicMock()
        self.machine.ball_devices['test2'].eject()
        self.advance_time_and_run(0.2)
        self.machine.coils['hold_coil2'].disable.assert_called_once_with()
        assert not self.machine.coils['hold_coil2'].enable.called

        # it should reenable the hold coil after 1s because there is a second ball
        self.machine.coils['hold_coil2'].enable = MagicMock()
        self.machine.coils['hold_coil2'].disable = MagicMock()
        self.advance_time_and_run(2)
        assert not self.machine.coils['hold_coil2'].disable.called
        self.machine.coils['hold_coil2'].enable.assert_called_once_with()
        self.assertEqual(1, self.machine.ball_devices['test2'].balls)

    def test_holdcoil_which_keeps_ball_multiple_entries(self):
        # add one ball
        self.machine.ball_devices['test2'].ball_count_handler.counter._last_count = 1
        self.machine.ball_devices['test2'].available_balls = 1
        self.machine.ball_devices['test2'].ball_count_handler._set_ball_count(1)

        # eject one ball
        self.machine.coils['hold_coil2'].enable = MagicMock()
        self.machine.coils['hold_coil2'].disable = MagicMock()
        self.machine.ball_devices['test2'].eject()
        self.advance_time_and_run(0.2)
        self.machine.coils['hold_coil2'].disable.assert_called_once_with()
        assert not self.machine.coils['hold_coil2'].enable.called

        # during the hold add another ball. it should not enable hold now
        self.machine.coils['hold_coil2'].enable = MagicMock()
        self.machine.coils['hold_coil2'].disable = MagicMock()
        self.machine.events.post('test_hold_event2')
        self.machine.switch_controller.process_switch(name='s_entrance2', state=1)
        self.machine.switch_controller.process_switch(name='s_entrance2', state=0)
        self.advance_time_and_run(0.2)
        assert not self.machine.coils['hold_coil2'].disable.called
        assert not self.machine.coils['hold_coil2'].enable.called

        # it should reenable the hold coil after 1s because there is a second ball
        self.machine.coils['hold_coil2'].enable = MagicMock()
        self.machine.coils['hold_coil2'].disable = MagicMock()
        self.advance_time_and_run(2)
        assert not self.machine.coils['hold_coil2'].disable.called
        self.machine.coils['hold_coil2'].enable.assert_called_once_with()
        self.assertEqual(1, self.machine.ball_devices['test2'].balls)

        # eject that ball. coil should stay off
        self.machine.coils['hold_coil2'].enable = MagicMock()
        self.machine.coils['hold_coil2'].disable = MagicMock()
        self.machine.ball_devices['test2'].eject()
        self.advance_time_and_run(300)
        self.machine.coils['hold_coil2'].disable.assert_called_once_with()
        assert not self.machine.coils['hold_coil2'].enable.called
        self.assertEqual(0, self.machine.ball_devices['test2'].balls)

    def test_holdcoil_with_hold_and_entry_switch(self):
        # add one ball
        self.assertEqual(0, self.machine.ball_devices['test3'].balls)
        self.machine.coils['hold_coil3'].enable = MagicMock()
        self.machine.coils['hold_coil3'].disable = MagicMock()
        self.machine.switch_controller.process_switch(name='s_entrance_and_hold3', state=1)
        self.machine.switch_controller.process_switch(name='s_entrance_and_hold3', state=0)

        self.advance_time_and_run(300)
        self.machine.coils['hold_coil3'].enable.assert_called_once_with()
        assert not self.machine.coils['hold_coil3'].disable.called
        self.assertEqual(1, self.machine.ball_devices['test3'].balls)

        # add a second ball
        self.machine.coils['hold_coil3'].enable = MagicMock()
        self.machine.coils['hold_coil3'].disable = MagicMock()
        self.machine.switch_controller.process_switch(name='s_entrance_and_hold3', state=1)
        self.machine.switch_controller.process_switch(name='s_entrance_and_hold3', state=0)
        self.advance_time_and_run(300)
        self.machine_run()
        self.machine.coils['hold_coil3'].enable.assert_called_once_with()
        assert not self.machine.coils['hold_coil3'].disable.called
        self.assertEqual(2, self.machine.ball_devices['test3'].balls)

        # eject one ball
        self.machine.coils['hold_coil3'].enable = MagicMock()
        self.machine.coils['hold_coil3'].disable = MagicMock()
        self.machine.ball_devices['test3'].eject()
        self.advance_time_and_run(0.2)
        self.machine.coils['hold_coil3'].disable.assert_called_once_with()
        assert not self.machine.coils['hold_coil3'].enable.called

        # it should reenable the hold coil after 1s because there is a second ball
        self.machine.coils['hold_coil3'].enable = MagicMock()
        self.machine.coils['hold_coil3'].disable = MagicMock()
        self.advance_time_and_run(2)
        assert not self.machine.coils['hold_coil3'].disable.called
        self.machine.coils['hold_coil3'].enable.assert_called_once_with()
        self.assertEqual(1, self.machine.ball_devices['test3'].balls)

        # eject another ball
        self.machine.coils['hold_coil3'].enable = MagicMock()
        self.machine.coils['hold_coil3'].disable = MagicMock()
        self.machine.ball_devices['test3'].eject()
        self.advance_time_and_run(0.2)
        self.machine.coils['hold_coil3'].disable.assert_called_once_with()
        assert not self.machine.coils['hold_coil3'].enable.called
        self.assertEqual(0, self.machine.ball_devices['test3'].balls)

        # coil should not reenable
        self.machine.coils['hold_coil3'].enable = MagicMock()
        self.machine.coils['hold_coil3'].disable = MagicMock()
        self.advance_time_and_run(30)
        assert not self.machine.coils['hold_coil3'].enable.called

    def test_holdcoil_with_ball_switches(self):
        # add one ball
        self.assertEqual(0, self.machine.ball_devices['test4'].balls)
        self.machine.coils['hold_coil4'].enable = MagicMock()
        self.machine.coils['hold_coil4'].disable = MagicMock()
        self.machine.switch_controller.process_switch(name='s_ball4_1', state=1)

        self.advance_time_and_run(300)
        self.machine.coils['hold_coil4'].enable.assert_called_once_with()
        assert not self.machine.coils['hold_coil4'].disable.called
        self.assertEqual(1, self.machine.ball_devices['test4'].balls)

        # add a second ball
        self.machine.coils['hold_coil4'].enable = MagicMock()
        self.machine.coils['hold_coil4'].disable = MagicMock()
        self.machine.switch_controller.process_switch(name='s_ball4_2', state=1)
        self.advance_time_and_run(300)
        self.machine_run()
        self.machine.coils['hold_coil4'].enable.assert_called_once_with()
        assert not self.machine.coils['hold_coil4'].disable.called
        self.assertEqual(2, self.machine.ball_devices['test4'].balls)

        # eject one ball
        self.machine.coils['hold_coil4'].enable = MagicMock()
        self.machine.coils['hold_coil4'].disable = MagicMock()
        self.machine.ball_devices['test4'].eject()
        self.advance_time_and_run(0.2)
        self.machine.coils['hold_coil4'].disable.assert_called_once_with()
        assert not self.machine.coils['hold_coil4'].enable.called
        self.machine.switch_controller.process_switch(name='s_ball4_1', state=0)
        self.machine.switch_controller.process_switch(name='s_ball4_2', state=0)
        self.machine.switch_controller.process_switch(name='s_ball4_1', state=1)

        # it should reenable the hold coil after 1s because there is a second ball
        self.machine.coils['hold_coil4'].enable = MagicMock()
        self.machine.coils['hold_coil4'].disable = MagicMock()
        self.advance_time_and_run(2)
        assert not self.machine.coils['hold_coil4'].disable.called
        self.machine.coils['hold_coil4'].enable.assert_called_once_with()
        self.assertEqual(1, self.machine.ball_devices['test4'].balls)

    def test_holdcoil_with_ball_switches_eject_fail(self):
        # add one ball
        self.assertEqual(0, self.machine.ball_devices['test4'].balls)
        self.machine.coils['hold_coil4'].enable = MagicMock()
        self.machine.coils['hold_coil4'].disable = MagicMock()
        self.machine.switch_controller.process_switch(name='s_ball4_1', state=1)

        self.advance_time_and_run(300)
        self.machine.coils['hold_coil4'].enable.assert_called_once_with()
        assert not self.machine.coils['hold_coil4'].disable.called
        self.assertEqual(1, self.machine.ball_devices['test4'].balls)

        # eject one ball
        self.machine.coils['hold_coil4'].enable = MagicMock()
        self.machine.coils['hold_coil4'].disable = MagicMock()
        self.machine.ball_devices['test4'].eject()
        self.advance_time_and_run(0.2)
        self.machine.coils['hold_coil4'].disable.assert_called_once_with()
        assert not self.machine.coils['hold_coil4'].enable.called
        self.machine.coils['hold_coil4'].disable = MagicMock()

        # after 2s the coil should get enabled again because there is still a ball in the device
        self.advance_time_and_run(2)
        self.machine.coils['hold_coil4'].enable.assert_called_once_with()
        assert not self.machine.coils['hold_coil4'].disable.called
        self.machine.coils['hold_coil4'].enable = MagicMock()

        # no ball switches change. eject should fail
        self.advance_time_and_run(8)

        # it ejects again
        self.machine.coils['hold_coil4'].disable.assert_called_once_with()
        assert not self.machine.coils['hold_coil4'].enable.called

        # ball leaves
        self.machine.switch_controller.process_switch(name='s_ball4_1', state=0)
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.ball_devices['test4'].balls)
        self.advance_time_and_run(10)
        self.assertEqual("idle", self.machine.ball_devices['test4']._state)
        assert not self.machine.coils['hold_coil4'].enable.called

