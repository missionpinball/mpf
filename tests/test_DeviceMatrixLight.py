from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
import time


class TestDeviceMatrixLight(MpfTestCase):

    def getConfigFile(self):
        return 'test_shows.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/show_controller/'

    def get_platform(self):
        return 'smart_virtual'

    def testBasicOnAndOff(self):
        """Tests setting some light brightness levels (using default arguments)"""

        # Make sure hardware devices have been configured for tests
        self.assertIn('light_01', self.machine.lights)
        self.assertIn('light_02', self.machine.lights)

        self.advance_time_and_run(10)

        # LEDs should start out off (current brightness is 0)
        self.assertEqual(0, self.machine.lights.light_01.state['brightness'])
        self.assertEqual(0, self.machine.lights.light_02.state['brightness'])

        self.machine.lights.light_01.on(128)
        self.assertEqual(128, self.machine.lights.light_01.state['brightness'])
        self.assertEqual(128, self.machine.lights.light_01.cache['brightness'])
        self.assertEqual(time.time(), self.machine.lights.light_01.cache['start_time'])
        self.assertEqual(128, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(0, self.machine.lights.light_01.state['priority'])
        self.machine.lights.light_02.on(255)
        self.assertEqual(255, self.machine.lights.light_02.state['brightness'])
        self.assertEqual(255, self.machine.lights.light_02.cache['brightness'])
        self.assertEqual(time.time(), self.machine.lights.light_02.cache['start_time'])
        self.assertEqual(255, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(0, self.machine.lights.light_02.state['priority'])

        # Turn the LEDs off
        self.machine.lights.light_01.on(0)
        self.assertEqual(0, self.machine.lights.light_01.state['brightness'])
        self.assertEqual(0, self.machine.lights.light_01.cache['brightness'])
        self.assertEqual(time.time(), self.machine.lights.light_01.cache['start_time'])
        self.assertEqual(0, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(0, self.machine.lights.light_01.state['priority'])
        self.machine.lights.light_02.on(0)
        self.assertEqual(0, self.machine.lights.light_02.state['brightness'])
        self.assertEqual(0, self.machine.lights.light_02.cache['brightness'])
        self.assertEqual(time.time(), self.machine.lights.light_02.cache['start_time'])
        self.assertEqual(0, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(0, self.machine.lights.light_02.state['priority'])

    def testOneSecondFadeUp(self):
        """One second fade from off (0) to full brightness (255)"""

        # Matrix light should start out off (current brightness is 0)
        self.machine.lights.light_01.off()
        self.assertEqual(0, self.machine.lights.light_01.state['brightness'])

        self.machine.lights.light_01.on(255, fade_ms=1000)
        fade_start_time = time.time()
        self.assertEqual(0, self.machine.lights.light_01.state['brightness'])
        self.assertEqual(0, self.machine.lights.light_01.state['start_brightness'])
        self.assertEqual(255, self.machine.lights.light_01.state['destination_brightness'])
        self.assertEqual(time.time(), self.machine.lights.light_01.state['start_time'])
        self.assertEqual(time.time() + 1, self.machine.lights.light_01.state['destination_time'])
        self.assertEqual(0, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertEqual(0, self.machine.lights.light_01.state['priority'])
        self.assertIsNotNone(self.machine.lights.light_01.fade_task)
        self.assertEqual(255, self.machine.lights.light_01.cache['brightness'])
        self.assertEqual(255, self.machine.lights.light_01.cache['destination_brightness'])
        self.assertEqual(0, self.machine.lights.light_01.cache['start_brightness'])
        self.assertEqual(fade_start_time, self.machine.lights.light_01.cache['start_time'])
        self.assertEqual(fade_start_time + 1, self.machine.lights.light_01.cache['destination_time'])
        self.assertEqual(1000, self.machine.lights.light_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.lights.light_01.cache['priority'])

        self.machine_run()

        # Advance time 25% of the fade and check brightness
        self.advance_time_and_run(0.25)
        self.assertEqual(63, self.machine.lights.light_01.state['brightness'])
        self.assertEqual(0, self.machine.lights.light_01.state['start_brightness'])
        self.assertEqual(255, self.machine.lights.light_01.state['destination_brightness'])
        self.assertEqual(63, self.machine.lights.light_01.hw_driver.current_brightness)

        # Check cache (should not have changed)
        self.assertEqual(255, self.machine.lights.light_01.cache['brightness'])
        self.assertEqual(255, self.machine.lights.light_01.cache['destination_brightness'])
        self.assertEqual(0, self.machine.lights.light_01.cache['start_brightness'])
        self.assertEqual(fade_start_time, self.machine.lights.light_01.cache['start_time'])
        self.assertEqual(fade_start_time + 1, self.machine.lights.light_01.cache['destination_time'])
        self.assertEqual(1000, self.machine.lights.light_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.lights.light_01.cache['priority'])

        # Advance time another 25% of the fade and check brightnesss
        self.advance_time_and_run(0.25)
        self.assertEqual(127, self.machine.lights.light_01.state['brightness'])
        self.assertEqual(0, self.machine.lights.light_01.state['start_brightness'])
        self.assertEqual(255, self.machine.lights.light_01.state['destination_brightness'])
        self.assertEqual(127, self.machine.lights.light_01.hw_driver.current_brightness)

        # Check cache (should not have changed)
        self.assertEqual(255, self.machine.lights.light_01.cache['brightness'])
        self.assertEqual(255, self.machine.lights.light_01.cache['destination_brightness'])
        self.assertEqual(0, self.machine.lights.light_01.cache['start_brightness'])
        self.assertEqual(fade_start_time, self.machine.lights.light_01.cache['start_time'])
        self.assertEqual(fade_start_time + 1, self.machine.lights.light_01.cache['destination_time'])
        self.assertEqual(1000, self.machine.lights.light_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.lights.light_01.cache['priority'])

        # Advance time another 25% of the fade and check brightnesss
        self.advance_time_and_run(0.25)
        self.assertEqual(191, self.machine.lights.light_01.state['brightness'])
        self.assertEqual(0, self.machine.lights.light_01.state['start_brightness'])
        self.assertEqual(255, self.machine.lights.light_01.state['destination_brightness'])
        self.assertEqual(191, self.machine.lights.light_01.hw_driver.current_brightness)

        # Check cache (should not have changed)
        self.assertEqual(255, self.machine.lights.light_01.cache['brightness'])
        self.assertEqual(255, self.machine.lights.light_01.cache['destination_brightness'])
        self.assertEqual(0, self.machine.lights.light_01.cache['start_brightness'])
        self.assertEqual(fade_start_time, self.machine.lights.light_01.cache['start_time'])
        self.assertEqual(fade_start_time + 1, self.machine.lights.light_01.cache['destination_time'])
        self.assertEqual(1000, self.machine.lights.light_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.lights.light_01.cache['priority'])

        # Advance time the last 25% of the fade and check brightness (should be done)
        self.advance_time_and_run(0.25)
        self.assertEqual(255, self.machine.lights.light_01.state['brightness'])
        self.assertEqual(0, self.machine.lights.light_01.state['start_brightness'])
        self.assertEqual(255, self.machine.lights.light_01.state['destination_brightness'])
        self.assertEqual(255, self.machine.lights.light_01.hw_driver.current_brightness)
        self.machine_run()
        self.assertIsNone(self.machine.lights.light_01.fade_task)

        # Check cache (should have been updated)
        self.assertEqual(255, self.machine.lights.light_01.cache['brightness'])
        self.assertEqual(255, self.machine.lights.light_01.cache['destination_brightness'])
        self.assertEqual(0, self.machine.lights.light_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.lights.light_01.cache['priority'])

    def testInterruptFadeOut(self):
        """Interrupt (kill) a one second fade from white to off"""

        # Matrix light should start out on (current brightness is 255)
        self.machine.lights.light_01.on()
        self.assertEqual(255, self.machine.lights.light_01.state['brightness'])

        self.machine.lights.light_01.on(0, fade_ms=1000)
        fade_start_time = time.time()
        self.assertEqual(255, self.machine.lights.light_01.state['brightness'])
        self.assertEqual(255, self.machine.lights.light_01.state['start_brightness'])
        self.assertEqual(0, self.machine.lights.light_01.state['destination_brightness'])
        self.machine_run()

        # Advance time 50% of the fade and check brightnesss
        self.advance_time_and_run(0.5)
        self.assertEqual(128, self.machine.lights.light_01.state['brightness'])
        self.assertEqual(255, self.machine.lights.light_01.state['start_brightness'])
        self.assertEqual(0, self.machine.lights.light_01.state['destination_brightness'])
        self.assertEqual(128, self.machine.lights.light_01.hw_driver.current_brightness)

        # Check cache (should not have changed)
        self.assertEqual(0, self.machine.lights.light_01.cache['brightness'])
        self.assertEqual(0, self.machine.lights.light_01.cache['destination_brightness'])
        self.assertEqual(255, self.machine.lights.light_01.cache['start_brightness'])
        self.assertEqual(fade_start_time, self.machine.lights.light_01.cache['start_time'])
        self.assertEqual(fade_start_time + 1, self.machine.lights.light_01.cache['destination_time'])
        self.assertEqual(1000, self.machine.lights.light_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.lights.light_01.cache['priority'])

        # Now interrupt the fade
        self.machine.lights.light_01._kill_fade()
        self.machine_run()

        # Fade should have been completed when killed
        self.assertEqual(0, self.machine.lights.light_01.state['brightness'])
        self.assertEqual(255, self.machine.lights.light_01.state['start_brightness'])
        self.assertEqual(0, self.machine.lights.light_01.state['destination_brightness'])
        self.assertEqual(0, self.machine.lights.light_01.hw_driver.current_brightness)
        self.assertIsNone(self.machine.lights.light_01.fade_task)

        # Check cache (should have been updated)
        self.assertEqual(0, self.machine.lights.light_01.cache['brightness'])
        self.assertEqual(0, self.machine.lights.light_01.cache['destination_brightness'])
        self.assertEqual(0, self.machine.lights.light_01.cache['fade_ms'])
        self.assertEqual(0, self.machine.lights.light_01.cache['priority'])

        # TODO: Add priority/force and cache restore tests

