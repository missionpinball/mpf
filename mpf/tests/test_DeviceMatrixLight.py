from mpf.devices.light import Light

from mpf.tests.MpfTestCase import MpfTestCase


class TestDeviceMatrixLight(MpfTestCase):

    def getConfigFile(self):
        return 'matrix_lights.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/light/'

    def _synchronise_light_update(self):
        ts = Light._updater_task.get_next_call_time()
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
        self.assertLightChannel("light_01", 0)
        self.assertLightChannel("light_02", 0)

        light1.on(128)
        self.advance_time_and_run(1)
        self.assertEqual([128, 128, 128], light1.get_color())
        self.assertAlmostEqual(self.machine.clock.get_time() - 1,
                               light1.stack[0]['start_time'])
        self.assertLightChannel("light_01", 128)
        self.assertEqual(0, light1.stack[0]['priority'])

        light2.on(255)
        self.advance_time_and_run(1)
        self.assertLightChannel("light_02", 255)
        self.assertEqual([255, 255, 255], light2.get_color())
        self.assertAlmostEqual(self.machine.clock.get_time() - 1,
                               light2.stack[0]['start_time'])
        self.assertEqual(0, light2.stack[0]['priority'])

        # Turn the lights off
        light1.off()
        self.advance_time_and_run(1)
        self.assertEqual([0, 0, 0], light1.get_color())
        self.assertAlmostEqual(self.machine.clock.get_time() - 1,
                               light1.stack[0]['start_time'])
        self.assertLightChannel("light_01", 0)
        self.assertEqual(0, light1.stack[0]['priority'])

        light2.off()
        self.advance_time_and_run(1)
        self.assertEqual([0, 0, 0], light2.get_color())
        self.assertAlmostEqual(self.machine.clock.get_time() - 1,
                               light2.stack[0]['start_time'])
        self.assertLightChannel("light_02", 0)
        self.assertEqual(0, light2.stack[0]['priority'])
