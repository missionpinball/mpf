# mpf.tests.test_Fast_Exp

from mpf.tests.test_Fast import TestFastBase
from mpf.tests.MpfTestCase import test_config

class TestFastAudio(TestFastBase):
    """Tests the FAST Audio Interface boards."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['aud']

    def get_config_file(self):
        return 'audio.yaml'

    def create_expected_commands(self):

        if self._testMethodName == 'test_machine_var_loading':
            self.serial_connections['aud'].expected_commands = {'AM:0F':'AM:0F',  # all 3 amps enabled, hp is line level
                                                                'AV:2D':'AV:2D',  # 45
                                                                'AS:0F':'AS:0F',  # 15
                                                                'AH:36':'AH:36',}  # 54

        else:
            self.serial_connections['aud'].expected_commands = {'AM:0B':'AM:0B',
                                                                'AV:11':'AV:11',
                                                                'AS:17':'AS:17',
                                                                'AH:28':'AH:28',}

    def test_audio_basics(self):

        fast_audio = self.machine.default_platform.audio_interface
        # 31 steps, 0-63
        main_list = [0, 3, 5, 7, 9, 11, 13, 15, 17, 19,
                     22, 24, 26, 28, 30, 32, 34, 36, 38, 40,
                     43, 45, 47, 49, 51, 53, 55, 57, 59, 61, 63]

        # 21 steps, 0-50
        sub_list = [0, 3, 5, 8, 10, 13, 15, 18, 20, 23,
                    25, 28, 30, 33, 35, 38, 40, 43, 45, 48, 50]

        # 11 steps, 0-40
        headphones_list = [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40]

        self.assertEqual(main_list, fast_audio.amps['main']['levels_list'])
        self.assertEqual(sub_list, fast_audio.amps['sub']['levels_list'])
        self.assertEqual(headphones_list, fast_audio.amps['headphones']['levels_list'])

        self.assertEqual(8, self.machine.variables.get_machine_var('fast_audio_main_volume'))
        self.assertEqual(9, self.machine.variables.get_machine_var('fast_audio_sub_volume'))
        self.assertEqual(10, self.machine.variables.get_machine_var('fast_audio_headphones_volume'))

        self.assertEqual(8, fast_audio.get_volume('main'))
        self.assertEqual(9, fast_audio.get_volume('sub'))
        self.assertEqual(10, fast_audio.get_volume('headphones'))

        self.assertEqual(17, fast_audio.get_hw_volume('main'))
        self.assertEqual(23, fast_audio.get_hw_volume('sub'))
        self.assertEqual(40, fast_audio.get_hw_volume('headphones'))

        self.assertEqual('11', self.aud_cpu.main_volume)
        self.assertEqual('17', self.aud_cpu.sub_volume)
        self.assertEqual('28', self.aud_cpu.headphones_volume)

        self.assertTrue(fast_audio.communicator.amps['main']['enabled'])
        self.assertTrue(fast_audio.communicator.amps['sub']['enabled'])
        self.assertTrue(fast_audio.communicator.amps['headphones']['enabled'])

        self.assertTrue(fast_audio.amps['main']['link_to_main'])
        self.assertFalse(fast_audio.amps['sub']['link_to_main'])
        self.assertFalse(fast_audio.amps['headphones']['link_to_main'])

        # Change the volume var and make sure it's reflected in the hardware
        self.aud_cpu.expected_commands['AV:13'] = 'AV:13'
        self.machine.variables.set_machine_var('fast_audio_main_volume', 9)
        self.advance_time_and_run(1)
        self.assertEqual('13', self.aud_cpu.main_volume)
        self.assertEqual(9, fast_audio.get_volume('main'))
        self.assertEqual(19, fast_audio.get_hw_volume('main'))

        # Test machine var player events work from config
        self.aud_cpu.expected_commands['AV:16'] = 'AV:16'
        self.post_event('increase_main_volume', 1)
        self.assertEqual('16', self.aud_cpu.main_volume)
        self.assertEqual(10, fast_audio.get_volume('main'))
        self.assertEqual(22, fast_audio.get_hw_volume('main'))

        # test ducking / restore
        self.assertEqual('16', fast_audio.communicator.amps['main']['volume'])
        self.aud_cpu.expected_commands['AV:20'] = 'AV:20'
        self.post_event('fast_audio_temp_volume', amp='main', change=5)
        self.advance_time_and_run(1)
        self.assertEqual('20', fast_audio.communicator.amps['main']['volume'])
        self.assertEqual(10, self.machine.variables.get_machine_var('fast_audio_main_volume'))

        self.aud_cpu.expected_commands['AV:16'] = 'AV:16'
        self.post_event('fast_audio_restore', amp='main')
        self.advance_time_and_run(1)
        self.assertEqual('16', fast_audio.communicator.amps['main']['volume'])

    def test_control_pins(self):
        self.aud_cpu.expected_commands['XO:01,63'] = 'XO:P'
        self.post_event('fast_audio_pulse_lcd_pin', pin=2)
        self.advance_time_and_run(1)
        self.aud_cpu.expected_commands['XO:06,62'] = 'XO:P'
        self.post_event('fast_audio_pulse_power_pin',1)
        self.aud_cpu.expected_commands['XO:07,61'] = 'XO:P'
        self.post_event('fast_audio_pulse_reset_pin',1)

    @test_config('audio2.yaml')
    def test_machine_var_loading(self):
        self.assertEqual(15, self.machine.variables.get_machine_var('fast_audio_main_volume'))
        # sub is linked to main, so it will be 15 even though the machine var is 2
        self.assertEqual(15, self.machine.variables.get_machine_var('fast_audio_sub_volume'))
        self.assertEqual(17, self.machine.variables.get_machine_var('fast_audio_headphones_volume'))