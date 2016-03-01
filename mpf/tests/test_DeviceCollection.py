from mpf.tests.MpfTestCase import MpfTestCase
from mpf.devices.led import Led

class TestDeviceCollection(MpfTestCase):
    def getConfigFile(self):
        return 'test_device_collection.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/device_collection/'

    def test_accessing_devices(self):

        led1 = self.machine.leds['led1']
        led2 = self.machine.leds['led2']
        led3 = self.machine.leds['led3']
        led4 = self.machine.leds['led4']

        self.assertTrue(isinstance(led1, Led))
        self.assertTrue(isinstance(led2, Led))
        self.assertTrue(isinstance(led3, Led))
        self.assertTrue(isinstance(led4, Led))

        self.assertEqual(self.machine.leds.led1, led1)
        self.assertEqual(self.machine.leds.led2, led2)
        self.assertEqual(self.machine.leds.led3, led3)
        self.assertEqual(self.machine.leds.led4, led4)

    def test_tags(self):
        led1 = self.machine.leds['led1']
        led2 = self.machine.leds['led2']
        led3 = self.machine.leds['led3']
        led4 = self.machine.leds['led4']

        self.assertEqual([], self.machine.leds.items_tagged('fake_tag'))

        self.assertIn(led1, self.machine.leds.items_tagged('tag1'))
        self.assertIn(led2, self.machine.leds.items_tagged('tag1'))
        self.assertNotIn(led3, self.machine.leds.items_tagged('tag1'))
        self.assertNotIn(led4, self.machine.leds.items_tagged('tag1'))

        self.assertIn('led1', self.machine.leds.sitems_tagged('tag1'))
        self.assertIn('led2', self.machine.leds.sitems_tagged('tag1'))
        self.assertNotIn('led3', self.machine.leds.sitems_tagged('tag1'))
        self.assertNotIn('led4', self.machine.leds.sitems_tagged('tag1'))

        self.assertNotIn(led1, self.machine.leds.items_not_tagged('tag1'))
        self.assertNotIn(led2, self.machine.leds.items_not_tagged('tag1'))
        self.assertIn(led3, self.machine.leds.items_not_tagged('tag1'))
        self.assertIn(led4, self.machine.leds.items_not_tagged('tag1'))

    def test_is_valid(self):
        self.assertTrue(self.machine.leds.is_valid('led1'))
        self.assertFalse(self.machine.leds.is_valid('fake_name'))

    def test_number(self):
        led1 = self.machine.leds['led1']
        led2 = self.machine.leds['led2']
        led3 = self.machine.leds['led3']
        led4 = self.machine.leds['led4']

        self.assertEqual(led1, self.machine.leds.number('1'))
        self.assertEqual(led2, self.machine.leds.number('2'))
        self.assertEqual(led3, self.machine.leds.number('3'))
        self.assertEqual(led4, self.machine.leds.number('4'))

    def test_multilists(self):
        led1 = self.machine.leds['led1']

        self.assertIn('led1', self.machine.leds.multilist_to_names(
            ['led1']))
        self.assertIn('led1', self.machine.leds.multilist_to_names(
            ['led1', 'led2']))
        self.assertIn('led1', self.machine.leds.multilist_to_names(
            'led1, led2'))
        self.assertIn('led1', self.machine.leds.multilist_to_names(
            'tag1, led3'))

        self.assertIn(led1, self.machine.leds.multilist_to_objects(
            ['led1']))
        self.assertIn(led1, self.machine.leds.multilist_to_objects(
            ['led1', 'led2']))
        self.assertIn(led1, self.machine.leds.multilist_to_objects(
            'led1, led2'))
        self.assertIn(led1, self.machine.leds.multilist_to_objects(
            'tag1, led3'))
