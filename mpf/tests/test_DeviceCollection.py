from mpf.devices.light import Light
from mpf.tests.MpfTestCase import MpfTestCase


class TestDeviceCollection(MpfTestCase):
    def getConfigFile(self):
        return 'test_device_collection.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/device_collection/'

    def test_accessing_devices(self):

        led1 = self.machine.lights['led1']
        led2 = self.machine.lights['led2']
        led3 = self.machine.lights['led3']
        led4 = self.machine.lights['led4']

        self.assertTrue(isinstance(led1, Light))
        self.assertTrue(isinstance(led2, Light))
        self.assertTrue(isinstance(led3, Light))
        self.assertTrue(isinstance(led4, Light))

        self.assertEqual(self.machine.lights.led1, led1)
        self.assertEqual(self.machine.lights.led2, led2)
        self.assertEqual(self.machine.lights.led3, led3)
        self.assertEqual(self.machine.lights.led4, led4)

    def test_tags(self):
        led1 = self.machine.lights['led1']
        led2 = self.machine.lights['led2']
        led3 = self.machine.lights['led3']
        led4 = self.machine.lights['led4']

        self.assertEqual([], self.machine.lights.items_tagged('fake_tag'))

        self.assertIn(led1, self.machine.lights.items_tagged('tag1'))
        self.assertIn(led2, self.machine.lights.items_tagged('tag1'))
        self.assertNotIn(led3, self.machine.lights.items_tagged('tag1'))
        self.assertNotIn(led4, self.machine.lights.items_tagged('tag1'))

    def test_number(self):
        led1 = self.machine.lights['led1']
        led2 = self.machine.lights['led2']
        led3 = self.machine.lights['led3']
        led4 = self.machine.lights['led4']

        self.assertEqual(led1, self.machine.lights.number('1'))
        self.assertEqual(led2, self.machine.lights.number('2'))
        self.assertEqual(led3, self.machine.lights.number('3'))
        self.assertEqual(led4, self.machine.lights.number('4'))
