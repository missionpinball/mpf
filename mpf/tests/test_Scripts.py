import ruamel.yaml as yaml

from mpf.tests.MpfTestCase import MpfTestCase
from mpf.core.script_controller import Script


class TestScripts(MpfTestCase):
    def getConfigFile(self):
        return 'test_scripts.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/scripts/'

    def test_script_to_show(self):
        pass

    def test_led_in_script(self):

        self.assertIn('leds_basic',
                      self.machine.script_controller.registered_scripts)
        self.assertIn('leds_basic_fade',
                      self.machine.script_controller.registered_scripts)
        self.assertIn('leds_color_token',
                      self.machine.script_controller.registered_scripts)
        self.assertIn('leds_extended',
                      self.machine.script_controller.registered_scripts)
        self.assertIn('lights_basic',
                      self.machine.script_controller.registered_scripts)
        self.assertIn('multiple_tokens',
                      self.machine.script_controller.registered_scripts)


    def test_tokens(self):

        data = '''
                - time: 0
                  "%leds%": red
                - time: +1
                  "%leds%": off
                - time: +1
                  '%leds%':
                    some: setting
                    "%other%": setting
                    this: "%foo%"
            '''

        data = yaml.load(data)
        script = Script(data)

        self.assertIn('leds', script.token_keys)
        self.assertIn('other', script.token_keys)
        self.assertIn('foo', script.token_values)

        self.assertIn([0], script.token_keys['leds'])
        self.assertIn([1], script.token_keys['leds'])
        self.assertIn([2], script.token_keys['leds'])

        self.assertIn([2, '%leds%', 'this'], script.token_values['foo'])

        test_script = script._replace_tokens(foo='hello')
        self.assertEqual(test_script[2]['%leds%']['this'], 'hello')

        test_script = script._replace_tokens(leds='hello')
        self.assertIn('hello', test_script[0])
        self.assertIn('hello', test_script[1])
        self.assertIn('hello', test_script[2])

        # test multiples at the same time
        test_script = script._replace_tokens(leds='hello', other='other',
                                             foo='hello')
        self.assertEqual('hello', test_script[2]['hello']['this'])
        self.assertIn('hello', test_script[0])
        self.assertIn('hello', test_script[1])
        self.assertIn('hello', test_script[2])
