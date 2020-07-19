from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallDevicePulseEject(MpfTestCase):

    def get_config_file(self):
        return 'test_pulse_eject.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def test_pulse_eject_strength(self):
        self.hit_switch_and_run("s_ball1", 0)
        self.hit_switch_and_run("s_ball2", 0)
        self.hit_switch_and_run("s_ball3", 0)
        self.hit_switch_and_run("s_ball4", 5)
        self.assertEqual("idle", self.machine.ball_devices["test"].state)

        self.machine.playfield.add_ball()
        self.advance_time_and_run(.1)

        self.assertEqual("pulsed_15", self.machine.coils["eject_coil"].hw_driver.state)

        self.release_switch_and_run("s_ball4", 1)

        self.assertEqual("ball_left", self.machine.ball_devices["test"].state)
        self.advance_time_and_run(10)

        self.assertEqual("idle", self.machine.ball_devices["test"].state)

        self.machine.playfield.add_ball()
        self.advance_time_and_run(.1)

        self.assertEqual("pulsed_15", self.machine.coils["eject_coil"].hw_driver.state)

        self.release_switch_and_run("s_ball3", 1)

        self.assertEqual("ball_left", self.machine.ball_devices["test"].state)
        self.advance_time_and_run(10)

        self.assertEqual("idle", self.machine.ball_devices["test"].state)

        self.machine.playfield.add_ball()
        self.advance_time_and_run(.1)

        self.assertEqual("pulsed_20", self.machine.coils["eject_coil"].hw_driver.state)

        self.release_switch_and_run("s_ball2", 1)

        self.assertEqual("ball_left", self.machine.ball_devices["test"].state)
        self.advance_time_and_run(10)

        self.assertEqual("idle", self.machine.ball_devices["test"].state)

        self.machine.playfield.add_ball()
        self.advance_time_and_run(.1)

        self.assertEqual("pulsed_40", self.machine.coils["eject_coil"].hw_driver.state)

        self.release_switch_and_run("s_ball1", 1)

        self.assertEqual("ball_left", self.machine.ball_devices["test"].state)
        self.advance_time_and_run(10)

        self.assertEqual("idle", self.machine.ball_devices["test"].state)
