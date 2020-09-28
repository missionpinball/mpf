from mpf.tests.MpfTestCase import MpfTestCase, test_config
from unittest.mock import MagicMock


class TestToughEntranceSwitch(MpfTestCase):
    def get_config_file(self):
        return 'trough_entrance_switch_initial_balls.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def test_initial_balls(self):
        """On startup the machine should count three balls."""
        self.assertNumBallsKnown(3)

    @test_config("trough_entrance_switch.yaml")
    def test_ball_settling(self):
        """Test that the trough waits for a ball to settle before ejecting."""
        self.assertNumBallsKnown(0)

        # request a ball to the playfield
        self.machine.playfield.add_ball()

        # add a ball to drain
        self.hit_switch_and_run("s_drain", .1)
        self.assertEqual("disabled", self.machine.coils["c_drain_eject"].hw_driver.state)

        # it waits for the ball to settle and ejects
        self.advance_time_and_run(.5)
        self.assertEqual("pulsed_20", self.machine.coils["c_drain_eject"].hw_driver.state)

        # ball leaves drain switch
        self.release_switch_and_run("s_drain", .5)

        # and enters the trough
        self.assertEqual("disabled", self.machine.coils["c_trough_release"].hw_driver.state)
        self.hit_and_release_switch("s_trough_enter")
        self.advance_time_and_run(.5)

        # it waits for the ball to settle
        self.assertEqual("disabled", self.machine.coils["c_trough_release"].hw_driver.state)
        self.advance_time_and_run(3)
        self.assertEqual("pulsed_20", self.machine.coils["c_trough_release"].hw_driver.state)
