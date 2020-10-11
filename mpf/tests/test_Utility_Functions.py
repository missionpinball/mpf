import unittest
from mpf.core.utility_functions import Util


class TestUtil(unittest.TestCase):

    def test_string_to_ms(self):
        self.assertEqual(86400000, Util.string_to_ms('1d'))
        self.assertEqual(3600000, Util.string_to_ms('1h'))
        self.assertEqual(60000, Util.string_to_ms('1m'))
        self.assertEqual(1000, Util.string_to_ms('1s'))
        self.assertEqual(1, Util.string_to_ms('1ms'))
        self.assertEqual(0, Util.string_to_ms(None))
        self.assertEqual(0, Util.string_to_ms(False))

    def test_keys_to_lower(self):
        inner_dict = dict(key1=1, Key2=2)
        outer_dict = dict(key3=1, Key4=2, Key5=inner_dict)

        # Test that keys become lower, including in nested dicts
        self.assertIn('Key2', inner_dict)
        self.assertIn('Key4', outer_dict)
        self.assertIn('Key5', outer_dict)
        transformed_dict = Util.keys_to_lower(outer_dict)
        self.assertIn('key4', transformed_dict)
        self.assertIn('key2', transformed_dict['key5'])

        # Test that empty non-dicts work
        transformed_dict = Util.keys_to_lower(None)
        self.assertIs(type(transformed_dict), dict)

        # Test that lists of dicts convert keys to lower
        my_list = Util.keys_to_lower([inner_dict, outer_dict])
        self.assertIn('key2', my_list[0])
        self.assertIn('key4', my_list[1])

    def test_string_to_list(self):
        my_string = '0, 1, 2, 3, 4, 5'
        result = Util.string_to_event_list(my_string)
        self.assertEqual(type(result), list)
        self.assertEqual(result[5], '5')

        my_string = ['0', '1', '2', '3', '4', '5']
        result = Util.string_to_event_list(my_string)
        self.assertEqual(type(result), list)
        self.assertEqual(result[5], '5')

        my_string = None
        result = Util.string_to_event_list(my_string)
        self.assertEqual(type(result), list)
        self.assertFalse(result)

        my_string = '0, 1, 2{not, split here}, 3, 4, 5'
        result = Util.string_to_event_list(my_string)
        self.assertEqual(type(result), list)
        self.assertEqual(result[1], '1')
        self.assertEqual(result[2], '2{not, split here}')
        self.assertEqual(result[3], '3')

    def test_list_of_lists(self):
        my_list = ['1, 2, 3, 4, 5', 'a, b, c, d, e']
        result = Util.list_of_lists(my_list)
        self.assertEqual(type(result), list)
        self.assertEqual(result[0][0], '1')
        self.assertEqual(result[1][4], 'e')

    def test_dict_merge(self):
        dict_a = dict(key1='val1', key2='val2', list1=[1, 2, 3])
        dict_b = dict(key3='val3', key4='val4', list1=[4, 5, 6])

        result = Util.dict_merge(dict_a, dict_b, combine_lists=True)
        self.assertEqual(result['key1'], 'val1')
        self.assertEqual(result['key2'], 'val2')
        self.assertEqual(result['key3'], 'val3')
        self.assertEqual(result['key4'], 'val4')
        self.assertEqual(result['list1'], [1, 2, 3, 4, 5, 6])

        result = Util.dict_merge(dict_a, dict_b, combine_lists=False)
        self.assertEqual(result['key1'], 'val1')
        self.assertEqual(result['key2'], 'val2')
        self.assertEqual(result['key3'], 'val3')
        self.assertEqual(result['key4'], 'val4')
        self.assertEqual(result['list1'], [4, 5, 6])

    def test_hex_to_string_list(self):
        result = Util.hex_string_to_list('00ff88')
        self.assertEqual(result, [0, 255, 136])

        result = Util.hex_string_to_list('00FF88')
        self.assertEqual(result, [0, 255, 136])

        result = Util.hex_string_to_list('00ff88aa')
        self.assertEqual(result, [0, 255, 136])

        result = Util.hex_string_to_list('00ff88', 4)
        self.assertEqual(result, [0, 0, 255, 136])

        self.assertRaises(ValueError, Util.hex_string_to_list, 'g0')

    def test_hex_string_to_int(self):
        result = Util.hex_string_to_int('ff')
        self.assertEqual(result, 255)

        result = Util.hex_string_to_int('ff', maxvalue=128)
        self.assertEqual(result, 128)

    def test_event_config_to_dict(self):
        config = dict()
        config['test_events_1'] = dict()
        config['test_events_1']['event1'] = '1s'
        config['test_events_1']['event2'] = '100ms'
        config['test_events_2'] = dict()
        config['test_events_2']['event3'] = '1s'
        config['test_events_2']['event4'] = '100ms'
        results = Util.event_config_to_dict(config)
        self.assertEqual(results['test_events_1']['event1'], '1s')

        # should config string to dict with vals of 0
        config = 'event1, event2'
        results = Util.event_config_to_dict(config)
        self.assertEqual(results['event1'], 0)

        # should config list to dict with vals of 0
        config = ['event1', 'event2']
        results = Util.event_config_to_dict(config)
        self.assertEqual(results['event1'], 0)

    def test_int_to_hex_string(self):
        result = Util.int_to_hex_string(255)
        self.assertEqual(result, 'FF')

        self.assertRaises(ValueError, Util.int_to_hex_string, 256)

    def test_pwm8_to_hex_string(self):
        self.assertEqual(Util.pwm8_to_hex_string(0), '00')
        self.assertEqual(Util.pwm8_to_hex_string(4), 'AA')
        self.assertRaises(ValueError, Util.pwm8_to_hex_string, 9)

    def test_pwm32_to_hex_string(self):
        self.assertEqual(Util.pwm32_to_hex_string(0), '00000000')
        self.assertEqual(Util.pwm32_to_hex_string(4), '02020202')
        self.assertRaises(ValueError, Util.pwm32_to_hex_string, 33)

    def test_pwm8_to_int(self):
        self.assertEqual(Util.pwm8_to_int(0), 0)
        self.assertEqual(Util.pwm8_to_int(4), 170)
        self.assertRaises(ValueError, Util.pwm8_to_int, 9)

    def test_pwm32_to_int(self):
        self.assertEqual(Util.pwm32_to_int(0), 0)
        self.assertEqual(Util.pwm32_to_int(4), 33686018)
        self.assertRaises(ValueError, Util.pwm32_to_int, 33)

    def test_power_to_on_off(self):
        self.assertEqual(Util.power_to_on_off(0), (0, 0))
        self.assertEqual(Util.power_to_on_off(0.1), (1, 9))
        self.assertEqual(Util.power_to_on_off(0.15), (3, 17))
        self.assertEqual(Util.power_to_on_off(0.5), (1, 1))
        self.assertEqual(Util.power_to_on_off(1), (1, 0))
        self.assertRaises(ValueError, Util.power_to_on_off, 9)

    def test_normalize_hex_string(self):
        result = Util.normalize_hex_string('ff00', 4)
        self.assertEqual(result, 'FF00')

        result = Util.normalize_hex_string('ff00', 6)
        self.assertEqual(result, '00FF00')

        result = Util.normalize_hex_string('c')
        self.assertEqual(result, '0C')

        result = Util.normalize_hex_string('4')
        self.assertEqual(result, '04')

    def test_bin_str_to_hex_str(self):
        result = Util.bin_str_to_hex_str('1111', 2)
        self.assertEqual(result, '0F')

    def test_is_hex_string(self):
        self.assertTrue(Util.is_hex_string('ff1234'))
        self.assertTrue(Util.is_hex_string('123456'))
        self.assertTrue(Util.is_hex_string('aabb00'))
        self.assertFalse(Util.is_hex_string('ffaagg'))
        self.assertFalse(Util.is_hex_string('hello'))
        self.assertFalse(Util.is_hex_string([1, 2, 3]))

    def test_get_from_dict(self):
        a = dict()
        a['b'] = dict()
        a['b']['c'] = dict()
        a['b']['c']['d'] = 1

        self.assertEqual(Util.get_from_dict(a, ['b', 'c', 'd']), 1)

    def test_set_in_dict(self):
        a = dict()
        a['b'] = dict()
        a['b']['c'] = dict()

        Util.set_in_dict(a, ['b', 'c'], 1)
        self.assertEqual(a['b']['c'], 1)

    def test_power_of_2(self):
        self.assertTrue(Util.is_power2(2))
        self.assertTrue(Util.is_power2(256))
        self.assertFalse(Util.is_power2(3))
        self.assertFalse(Util.is_power2(222))
