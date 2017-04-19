from unittest.mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase


class TestInfoLights(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        self.machine_config_patches['mpf']['plugins'] = ["mpf.plugins.info_lights.InfoLights"]

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/info_lights/'

    def start_game(self):
        # shots only work in games so we have to do this a lot
        self.machine.playfield.add_ball = MagicMock()
        self.machine.ball_controller.num_balls_known = 3
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertEqual(2, self.machine.game.num_players)
        self.assertIsNotNone(self.machine.game)

    def stop_game(self):
        # stop game
        self.assertIsNotNone(self.machine.game)
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertIsNone(self.machine.game)

    def test_info_lights(self):
        # machine starts at gameover
        self.advance_time_and_run(.1)
        self.assertLightColor("gameOver", [0, 0, 0])
        self.advance_time_and_run(1)
        self.assertLightColor("gameOver", [255, 255, 255])
        self.advance_time_and_run(1)
        self.assertLightColor("gameOver", [0, 0, 0])

        self.start_game()

        # no more game over
        self.assertLightColor("gameOver", [0, 0, 0])
        self.advance_time_and_run(1)
        self.assertLightColor("gameOver", [0, 0, 0])

        # ball one
        self.assertLightChannel("bip1", 255)
        self.assertLightChannel("bip2", 0)
        self.assertLightChannel("bip3", 0)
        # no tilt
        self.assertLightColor("tilt", [0, 0, 0])
        # two players
        self.assertLightChannel("player1", 255)
        self.assertLightChannel("player2", 255)

        self.machine.game.balls_in_play = 0
        self.advance_time_and_run()

        # ball one
        self.assertLightChannel("bip1", 255)
        self.assertLightChannel("bip2", 0)
        self.assertLightChannel("bip3", 0)
        # no tils
        self.assertLightColor("tilt", [0, 0, 0])

        self.machine.game.balls_in_play = 0
        self.advance_time_and_run()

        # ball two
        self.assertLightChannel("bip1", 0)
        self.assertLightChannel("bip2", 255)
        self.assertLightChannel("bip3", 0)
        # no tilt
        self.assertLightColor("tilt", [0, 0, 0])

        self.stop_game()
        self.advance_time_and_run(.5)

        # gameover
        self.assertLightColor("gameOver", [0, 0, 0])
        self.advance_time_and_run(1)
        self.assertLightColor("gameOver", [255, 255, 255])
        self.advance_time_and_run(1)
        self.assertLightColor("gameOver", [0, 0, 0])

        self.start_game()
        self.advance_time_and_run()

        self.post_event("tilt")
        self.advance_time_and_run()

        # no ball
        self.assertLightChannel("bip1", 255)
        self.assertLightChannel("bip2", 0)
        self.assertLightChannel("bip3", 0)
        # tilt
        self.assertLightColor("tilt", [255, 255, 255])

        self.assertLightChannel("player1", 255)
        self.assertLightChannel("player2", 255)

