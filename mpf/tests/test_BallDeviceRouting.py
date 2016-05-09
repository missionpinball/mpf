from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallDeviceRouting(MpfTestCase):
    def __init__(self, test_map):
        super().__init__(test_map)
        self._captured = 0
        self._missing = 0

    def getConfigFile(self):
        return 'test_ball_device_routing.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_device/'

    def _missing_ball(self):
        self._missing += 1

    def _captured_from_pf(self, balls, **kwargs):
        del kwargs
        self._captured += balls

    def test_routing_to_pf_on_capture(self):
        c_launcher = self.machine.coils['c_launcher']
        c_launcher.pulse = MagicMock()
        trough1 = self.machine.ball_devices['test_trough1']
        trough2 = self.machine.ball_devices['test_trough2']
        launcher = self.machine.ball_devices['test_launcher']
        target1 = self.machine.ball_devices['test_target1']

        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)

        self._missing = 0
        self._captured = 0

        self.machine.switch_controller.process_switch("s_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, launcher.balls)
        self.assertEqual(1, self._captured)
        self._captured = 0

        c_launcher.pulse.assert_called_once_with()
        self.assertEqual(0, len(trough1.eject_queue))
        self.assertEqual(1, len(trough2.eject_queue))
        self.assertEqual(0, len(target1.eject_queue))
        self.assertEqual("ejecting", launcher._state)
        self.assertEqual(trough2, launcher.eject_in_progress_target)

        self.machine.switch_controller.process_switch("s_launcher", 0)
        self.advance_time_and_run(1)

        self.assertEqual(0, self._missing)

    def test_drain_routing(self):
        trough2 = self.machine.ball_devices['test_trough2']
        drain1 = self.machine.ball_devices['test_drain']
        c_drain1 = self.machine.coils['c_drain1']
        c_drain1.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)

        self._missing = 0
        self._captured = 0

        self.machine.switch_controller.process_switch("s_drain1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, drain1.balls)
        self.assertEqual(1, self._captured)
        self._captured = 0
        c_drain1.pulse.assert_called_once_with()

        self.assertEqual(0, len(trough2.eject_queue))
        self.assertEqual("ejecting", drain1._state)
        self.assertEqual(trough2, drain1.eject_in_progress_target)

        self.machine.switch_controller.process_switch("s_drain1", 0)
        self.advance_time_and_run(1)

        self.assertEqual(0, self._missing)
