from mpf.devices.matrix_light import MatrixLight

from mpf.tests.MpfTestCase import MpfTestCase


class TestDeviceMatrixLight(MpfTestCase):

    def getConfigFile(self):
        return 'test_shows.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/shows/'

    def get_platform(self):
        return 'smart_virtual'

    def _synchronise_light_update(self):
        ts = MatrixLight._updater_task.get_next_call_time()
        self.assertTrue(ts)
        self.advance_time_and_run(ts - self.machine.clock.get_time())
        self.advance_time_and_run(0.01)

    def testBasicOnAndOff(self):
        """Tests setting some light brightness levels (using default arguments)"""

        # Make sure hardware devices have been configured for tests
        self.assertIn('light_01', self.machine.lights)
        self.assertIn('light_02', self.machine.lights)

        light1 = self.machine.lights.light_01
        light2 = self.machine.lights.light_02

        self.advance_time_and_run(10)

        # Lights should start out off (current brightness is 0)
        self.assertEqual(0, light1.hw_driver.current_brightness)
        self.assertEqual(0, light2.hw_driver.current_brightness)

        light1.on(128)
        self.advance_time_and_run(1)
        self.assertEqual(128, light1.stack[0]['brightness'])
        self.assertAlmostEqual(self.machine.clock.get_time() - 1,
                               light1.stack[0]['start_time'])
        self.assertEqual(128, light1.hw_driver.current_brightness)
        self.assertEqual(0, light1.stack[0]['priority'])

        light2.on(255)
        self.advance_time_and_run(1)
        self.assertEqual(255, light2.hw_driver.current_brightness)
        self.assertEqual(255, light2.stack[0]['brightness'])
        self.assertAlmostEqual(self.machine.clock.get_time() - 1,
                               light2.stack[0]['start_time'])
        self.assertEqual(255, light2.hw_driver.current_brightness)
        self.assertEqual(0, light2.stack[0]['priority'])

        # Turn the lights off
        light1.off()
        self.advance_time_and_run(1)
        self.assertEqual(0, light1.stack[0]['brightness'])
        self.assertAlmostEqual(self.machine.clock.get_time() - 1,
                               light1.stack[0]['start_time'])
        self.assertEqual(0, light1.hw_driver.current_brightness)
        self.assertEqual(0, light1.stack[0]['priority'])

        light2.off()
        self.advance_time_and_run(1)
        self.assertEqual(0, light2.hw_driver.current_brightness)
        self.assertEqual(0, light2.stack[0]['brightness'])
        self.assertAlmostEqual(self.machine.clock.get_time() - 1,
                               light2.stack[0]['start_time'])
        self.assertEqual(0, self.machine.lights.light_02.hw_driver.current_brightness)
        self.assertEqual(0, light2.stack[0]['priority'])

    def testOneSecondFadeUp(self):
        """One second fade from off (0) to full brightness (255)"""

        # Matrix light should start out off (current brightness is 0)

        light = self.machine.lights.light_01

        self.advance_time_and_run(1)
        self.assertEqual(0, light.hw_driver.current_brightness)

        self._synchronise_light_update()
        light.on(255, fade_ms=1000)
        fade_start_time = self.machine.clock.get_time()

        self.assertEqual(0, light.stack[0]['brightness'])
        self.assertEqual(0, light.stack[0]['start_brightness'])
        self.assertEqual(255, light.stack[0]['dest_brightness'])
        self.assertAlmostEqual(self.machine.clock.get_time(), light.stack[0]['start_time'])
        self.assertAlmostEqual(self.machine.clock.get_time() + 1, light.stack[0]['dest_time'])
        self.assertEqual(0, light.hw_driver.current_brightness)
        self.assertEqual(0, light.stack[0]['priority'])
        self.assertFalse(light.fade_in_progress)
        self.assertEqual(0, light.stack[0]['brightness'])
        self.assertEqual(255, light.stack[0]['dest_brightness'])
        self.assertEqual(0, light.stack[0]['start_brightness'])
        self.assertAlmostEqual(fade_start_time, light.stack[0]['start_time'])
        self.assertAlmostEqual(fade_start_time + 1, light.stack[0]['dest_time'])
        self.assertEqual(0, light.stack[0]['priority'])

        # Advance time 25% of the fade and check brightness
        self.advance_time_and_run(0.26)
        self.assertTrue(light.fade_in_progress)
        self.assertEqual(63, light.stack[0]['brightness'])
        self.assertEqual(0, light.stack[0]['start_brightness'])
        self.assertEqual(255, light.stack[0]['dest_brightness'])
        self.assertEqual(63, light.hw_driver.current_brightness)

        # Advance time another 25% of the fade and check brightness
        self.advance_time_and_run(0.24)
        self.assertEqual(124, light.stack[0]['brightness'])
        self.assertEqual(0, light.stack[0]['start_brightness'])
        self.assertEqual(255, light.stack[0]['dest_brightness'])
        self.assertEqual(124, light.hw_driver.current_brightness)

        # Advance time another 25% of the fade and check brightness
        self.advance_time_and_run(0.26)
        self.assertEqual(191, light.stack[0]['brightness'])
        self.assertEqual(0, light.stack[0]['start_brightness'])
        self.assertEqual(255, light.stack[0]['dest_brightness'])
        self.assertEqual(191, light.hw_driver.current_brightness)

        # Advance time the last 25% of the fade and check brightness (should be done)
        self.advance_time_and_run(0.26)
        self.assertEqual(255, light.stack[0]['brightness'])
        self.assertEqual(0, light.stack[0]['start_brightness'])
        self.assertEqual(255, light.stack[0]['dest_brightness'])
        self.assertEqual(255, light.hw_driver.current_brightness)
        self.machine_run()
        self.assertFalse(light.fade_in_progress)

        light = self.machine.lights.light_03
        light.clear_stack()
        self.assertEqual(1000, light.default_fade_ms)

        self.advance_time_and_run(1)
        self.assertEqual(0, light.hw_driver.current_brightness)
        self._synchronise_light_update()
        light.on()
        self.advance_time_and_run(.52)
        self.assertEqual(130, light.hw_driver.current_brightness)
        self.advance_time_and_run(.5)
        self.assertEqual(255, light.hw_driver.current_brightness)

    def testInterruptFadeOut(self):
        """Interrupt (kill) a one second fade from white to off"""

        # Matrix light should start out on (current brightness is 255)

        light = self.machine.lights.light_01
        light.on()
        self.advance_time_and_run()

        self.assertEqual(255, light.hw_driver.current_brightness)

        self._synchronise_light_update()
        light.on(0, fade_ms=1000)
        fade_start_time = self.machine.clock.get_time()
        self.assertEqual(255, light.stack[0]['brightness'])
        self.assertEqual(255, light.stack[0]['start_brightness'])
        self.assertEqual(0, light.stack[0]['dest_brightness'])

        # Advance time 50% of the fade and check brightness
        self.advance_time_and_run(0.5)
        self.assertEqual(fade_start_time, light.stack[0]['start_time'])
        self.assertEqual(131, light.stack[0]['brightness'])
        self.assertEqual(255, light.stack[0]['start_brightness'])
        self.assertEqual(0, light.stack[0]['dest_brightness'])
        self.assertEqual(131, light.hw_driver.current_brightness)

        # Now interrupt the fade
        light._end_fade()

        # advance the time past when the fade would have ended
        self.advance_time_and_run(2)

        # Fade should have been completed when ended
        self.assertEqual(131, light.hw_driver.current_brightness)
        self.assertFalse(light.fade_in_progress)

    def test_gamma_correct(self):
        """Test that we can dim the machine."""
        light1 = self.machine.lights.light_01

        light1.on(200)
        self.advance_time_and_run()
        self.assertEqual(200, light1.hw_driver.current_brightness)

        self.machine.create_machine_var("brightness", 0.8)
        light1.on(200)
        self.advance_time_and_run()
        self.assertEqual(160, light1.hw_driver.current_brightness)
