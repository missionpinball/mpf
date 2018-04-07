from mpf.platforms.virtual import VirtualDriver, VirtualLight

from mpf.tests.MpfTestCase import MpfTestCase


class TestDigitalOutputs(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/digital_output/'

    def test_enable_disable(self):
        light = self.machine.digital_outputs["light_output"].hw_driver
        driver = self.machine.digital_outputs["driver_output"].hw_driver
        self.assertIsInstance(driver, VirtualDriver)
        self.assertIsInstance(light, VirtualLight)
        self.assertEqual("1", driver.number)
        self.assertEqual("test_subtype-1", light.number)
        self.assertEqual("disabled", driver.state)
        self.machine.digital_outputs["driver_output"].enable()
        self.assertEqual("enabled", driver.state)
        self.machine.digital_outputs["driver_output"].disable()
        self.assertEqual("disabled", driver.state)

        self.assertEqual(0.0, light.current_brightness)
        self.machine.digital_outputs["light_output"].enable()
        self.assertEqual(1.0, light.current_brightness)
        self.machine.digital_outputs["light_output"].disable()
        self.assertEqual(0.0, light.current_brightness)
