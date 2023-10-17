# mpf.tests.test_Fast_Exp

from mpf.tests.test_Fast import TestFastBase


class TestFastAudio(TestFastBase):
    """Tests the FAST Audio Interface boards."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['aud']

    def get_config_file(self):
        return 'audio.yaml'

    def create_expected_commands(self):
        # These are all the defaults based on the config file for this test.
        # Individual tests can override / add as needed

        self.serial_connections['aud'].expected_commands = {}

    def test_audio(self):
        pass

        # increase_volume(steps=1)
        # decrease_volume(steps=1)
        # set_volume(volume=20)
        # temp_duck_volume(steps=1)
        # restore_volume()

        # increase_main_volume(steps=1)
        # decrease_main_volume(steps=1)
        # set_main_volume(volume=20)
        # temp_duck_main_volume(steps=1)
        # restore_main_volume()

        # increase_sub_volume(steps=1)
        # decrease_sub_volume(steps=1)
        # set_sub_volume(volume=20)
        # temp_duck_sub_volume(steps=1)
        # restore_sub_volume()

        # increase_headphones_volume(steps=1)
        # decrease_headphones_volume(steps=1)
        # set_headphones_volume(volume=20)
        # temp_duck_headphones_volume(steps=1)
        # restore_headphones_volume()

        # pulse_lcd_pin_1(ms=100)
        # pulse_lcd_pin_2(ms=100)
        # pulse_lcd_pin_3(ms=100)
        # pulse_lcd_pin_4(ms=100)
        # pulse_lcd_pin_5(ms=100)
        # pulse_lcd_pin_6(ms=100)