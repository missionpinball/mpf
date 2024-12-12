from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallDevicesEnableCoil(MpfTestCase):
    def get_config_file(self):
        return 'test_enable_coil.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def test_enable_coil_eject(self):
        self.hit_switch_and_run("s_ball1", 0)
        self.hit_switch_and_run("s_ball2", 5)
        self.assertEqual("idle", self.machine.ball_devices["test"].state)

        self.machine.playfield.add_ball()
        self.advance_time_and_run(.1)

        self.assertEqual("enabled", self.machine.coils["eject_coil"].hw_driver.state)
        self.advance_time_and_run(.4)
        self.assertEqual("disabled", self.machine.coils["eject_coil"].hw_driver.state)

        self.release_switch_and_run("s_ball2", 1)

        self.assertEqual("ball_left", self.machine.ball_devices["test"].state)
        self.advance_time_and_run(10)

        self.assertEqual("idle", self.machine.ball_devices["test"].state)

class TestBallDevicesEnableCoilMultiple(MpfTestCase):
    def get_config_file(self):
        return 'test_enable_coil_multiple.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def test_enable_coil_eject_times(self):
        self.hit_switch_and_run("s_ball1", 0)
        self.hit_switch_and_run("s_ball2", 5)
        self.assertEqual("idle", self.machine.ball_devices["test"].state)

        self.machine.playfield.add_ball()
        self.advance_time_and_run(.1)

        self.assertEqual("enabled", self.machine.coils["eject_coil"].hw_driver.state)
        self.advance_time_and_run(.2)
        self.assertEqual("disabled", self.machine.coils["eject_coil"].hw_driver.state)

        self.release_switch_and_run("s_ball2", 1)

        self.assertEqual("ball_left", self.machine.ball_devices["test"].state)
        self.advance_time_and_run(10)

        self.assertEqual("idle", self.machine.ball_devices["test"].state)

        self.machine.playfield.add_ball()
        self.advance_time_and_run(.1)
        self.assertEqual("enabled", self.machine.coils["eject_coil"].hw_driver.state)
        self.advance_time_and_run(.4)
        self.assertEqual("enabled", self.machine.coils["eject_coil"].hw_driver.state)
        self.advance_time_and_run(.2)
        self.assertEqual("disabled", self.machine.coils["eject_coil"].hw_driver.state)

        self.release_switch_and_run("s_ball1", 1)
        self.assertEqual("ball_left", self.machine.ball_devices["test"].state)
        self.advance_time_and_run(10)

        self.assertEqual("idle", self.machine.ball_devices["test"].state)
