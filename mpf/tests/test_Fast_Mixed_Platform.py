# mpf.tests.test_Fast_Mixed_Platform

from mpf.tests.test_Fast import TestFastBase


class TestFastMixedPlatform(TestFastBase):
    """A FAST coil on a machine whose default platform is virtual."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['net2']

    def get_config_file(self):
        return 'mixed_platform.yaml'

    def create_expected_commands(self):
        super().create_expected_commands()
        net = self.serial_connections['net2'].expected_commands
        net['NN:00'] = 'NN:00,FP-I/O-0804-3   ,01.10,04,08,00,00,00,00,00,00'
        for i in range(104):  # every switch is initialized, configured or not
            net[f'SL:{i:02X},01,00,00'] = 'SL:P'
        # c_fast reaches the board with its FAST platform_settings:
        # pulse 20 ms (14), recycle_ms 30 (1E), pwm2_ms at its default (00)
        net['DL:00,81,00,10,14,FF,00,00,1E'] = 'DL:P'

    def test_fast_coil_under_virtual_default(self):
        coil = self.machine.coils["c_fast"]
        self.assertEqual(self.machine.hardware_platforms['fast'], coil.platform)
        self.assertEqual(self.machine.hardware_platforms['virtual'],
                         self.machine.coils["c_virtual"].platform)
