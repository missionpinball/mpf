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
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertEqual(2, self.machine.game.num_players)
        self.assertIsNotNone(self.machine.game)

    def stop_game(self):
        # stop game
        self.assertIsNotNone(self.machine.game)
        self.machine.game.game_ending()
        self.advance_time_and_run()
        self.assertIsNone(self.machine.game)

    def test_info_lights(self):
        # machine starts at gameover
        self.advance_time_and_run(.1)
        self.assertEqual([0, 0, 0], self.machine.leds['gameOver'].hw_driver.current_color)
        self.advance_time_and_run(1)
        self.assertEqual([255, 255, 255], self.machine.leds['gameOver'].hw_driver.current_color)
        self.advance_time_and_run(1)
        self.assertEqual([0, 0, 0], self.machine.leds['gameOver'].hw_driver.current_color)

        self.start_game()

        # no more game over
        self.assertEqual([0, 0, 0], self.machine.leds['gameOver'].hw_driver.current_color)
        self.advance_time_and_run(1)
        self.assertEqual([0, 0, 0], self.machine.leds['gameOver'].hw_driver.current_color)

        # ball one
        self.assertTrue(self.machine.lights['bip1'].hw_driver.current_brightness)
        self.assertFalse(self.machine.lights['bip2'].hw_driver.current_brightness)
        self.assertFalse(self.machine.lights['bip3'].hw_driver.current_brightness)
        # no tilt
        self.assertEqual([0, 0, 0], self.machine.leds['tilt'].hw_driver.current_color)
        # two players
        self.assertTrue(self.machine.lights['player1'].hw_driver.current_brightness)
        self.assertTrue(self.machine.lights['player2'].hw_driver.current_brightness)

        self.machine.game.balls_in_play = 0
        self.advance_time_and_run()

        # ball one
        self.assertTrue(self.machine.lights['bip1'].hw_driver.current_brightness)
        self.assertFalse(self.machine.lights['bip2'].hw_driver.current_brightness)
        self.assertFalse(self.machine.lights['bip3'].hw_driver.current_brightness)
        # no tils
        self.assertEqual([0, 0, 0], self.machine.leds['tilt'].hw_driver.current_color)

        self.machine.game.balls_in_play = 0
        self.advance_time_and_run()

        # ball two
        self.assertFalse(self.machine.lights['bip1'].hw_driver.current_brightness)
        self.assertTrue(self.machine.lights['bip2'].hw_driver.current_brightness)
        self.assertFalse(self.machine.lights['bip3'].hw_driver.current_brightness)
        # no tilt
        self.assertEqual([0, 0, 0], self.machine.leds['tilt'].hw_driver.current_color)

        self.stop_game()
        self.advance_time_and_run(.5)

        # gameover
        self.assertEqual([0, 0, 0], self.machine.leds['gameOver'].hw_driver.current_color)
        self.advance_time_and_run(1)
        self.assertEqual([255, 255, 255], self.machine.leds['gameOver'].hw_driver.current_color)
        self.advance_time_and_run(1)
        self.assertEqual([0, 0, 0], self.machine.leds['gameOver'].hw_driver.current_color)

        self.start_game()
        self.advance_time_and_run()

        self.post_event("tilt")
        self.advance_time_and_run()

        # no ball
        self.assertTrue(self.machine.lights['bip1'].hw_driver.current_brightness)
        self.assertFalse(self.machine.lights['bip2'].hw_driver.current_brightness)
        self.assertFalse(self.machine.lights['bip3'].hw_driver.current_brightness)
        # tilt
        self.assertEqual([255, 255, 255], self.machine.leds['tilt'].hw_driver.current_color)

        self.assertTrue(self.machine.lights['player1'].hw_driver.current_brightness)
        self.assertTrue(self.machine.lights['player2'].hw_driver.current_brightness)

