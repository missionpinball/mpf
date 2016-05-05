from mpf.tests.MpfTestCase import MpfTestCase
from mpf.core.bcp import decode_command_string, encode_command_string


class TestBcp(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        # remove config patch which disables bcp
        del self.machine_config_patches['bcp']

    def test_decode_command_string(self):
        # test strings
        string_in = 'play?some_value=7&another_value=2'
        command = 'play'
        kwargs = dict(some_value='7', another_value='2')

        actual_command, actual_kwargs = decode_command_string(string_in)

        self.assertEqual(command, actual_command)
        self.assertEqual(kwargs, actual_kwargs)

        # test ints, floats, bools, and none
        string_in = 'play?some_int=int:7&some_float=float:2.0&some_none' \
                    '=NoneType:&some_true=bool:True&some_false=bool:False'
        command = 'play'
        kwargs = dict(some_int=7, some_float=2.0, some_none=None,
                      some_true=True, some_false=False)

        actual_command, actual_kwargs = decode_command_string(string_in)

        self.assertEqual(command, actual_command)
        self.assertEqual(kwargs, actual_kwargs)

    def test_encode_command_string(self):
        # test strings
        command = 'play'
        kwargs = dict(some_value='7', another_value='2')
        expected_strings = ('play?some_value=7&another_value=2',
                            'play?another_value=2&some_value=7')

        actual_string = encode_command_string(command, **kwargs)

        self.assertIn(actual_string, expected_strings)

        # test ints, floats, bools, and none
        command = 'play'
        kwargs = dict(some_int=7, some_float=2.0, some_none=None,
                      some_true=True, some_false=False)
        expected_snippets = ('play?',
                             'some_int=int:7',
                             'some_float=float:2.0',
                             'some_none=NoneType:',
                             'some_true=bool:True',
                             'some_false=bool:False')

        actual_string = encode_command_string(command, **kwargs)

        for snippet in expected_snippets:
            self.assertIn(snippet, actual_string)

    def test_json_encoding_decoding(self):
        # test with dicts
        command = 'play'
        kwargs = dict()
        kwargs['dict1'] = dict(key1='value1', key2='value2')
        kwargs['dict2'] = dict(key3='value3', key4='value4')

        encoded_string = encode_command_string(command, **kwargs)
        decoded_command, decoded_dict = decode_command_string(encoded_string)

        self.assertEqual('play', decoded_command)
        self.assertIn('dict1', decoded_dict)
        self.assertIn('dict2', decoded_dict)
        self.assertEqual(decoded_dict['dict1']['key1'], 'value1')
        self.assertEqual(decoded_dict['dict1']['key2'], 'value2')
        self.assertEqual(decoded_dict['dict2']['key3'], 'value3')
        self.assertEqual(decoded_dict['dict2']['key4'], 'value4')

        # test with list
        command = 'play'
        kwargs = dict()
        kwargs['dict1'] = dict(key1='value1', key2='value2')
        kwargs['dict2'] = list()
        kwargs['dict2'].append(dict(key3='value3', key4='value4'))
        kwargs['dict2'].append(dict(key3='value5', key4='value6'))

        encoded_string = encode_command_string(command, **kwargs)
        decoded_command, decoded_dict = decode_command_string(encoded_string)

        self.assertEqual('play', decoded_command)
        self.assertIn('dict1', decoded_dict)
        self.assertIn('dict2', decoded_dict)
        self.assertEqual(decoded_dict['dict1']['key1'], 'value1')
        self.assertEqual(decoded_dict['dict1']['key2'], 'value2')
        self.assertEqual(decoded_dict['dict2'][0],
                         dict(key3='value3', key4='value4'))
        self.assertEqual(decoded_dict['dict2'][1],
                         dict(key3='value5', key4='value6'))

    def test_receive_register_trigger(self):
        self.machine.bcp.receive_queue.put(('register_trigger',
                                            {'event': 'test_event'}, None))
        self.advance_time_and_run()

        self.assertIn('test_event', self.machine.bcp.registered_trigger_events)
