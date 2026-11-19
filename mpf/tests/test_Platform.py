from unittest.mock import patch

from mpf.tests.MpfTestCase import MpfTestCase


class TestPlatform(MpfTestCase):

    def get_config_file(self):
        return 'test_platform.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/platform/'

    def get_platform(self):
        return False

    def test_platform_from_device(self):
        # tests that a platform can be added by a device, even if it's not
        # specified in the hardware section

        self.assertEqual(self.machine.switches["switch1"].platform,
                         self.machine.hardware_platforms['smart_virtual'])

        self.assertEqual(self.machine.switches["switch2"].platform,
                         self.machine.hardware_platforms['virtual'])

    def test_platform_settings_validated_by_device_platform(self):
        # a device which names its own platform must have its
        # platform_settings validated by that platform, not by the default
        default = self.machine.hardware_platforms['smart_virtual']
        own = self.machine.hardware_platforms['virtual']

        for device, method in ((self.machine.coils["coil2"], "validate_coil_section"),
                               (self.machine.switches["switch2"], "validate_switch_section")):
            with patch.object(own, method, return_value={}) as own_validate, \
                    patch.object(default, method, return_value={}) as default_validate:
                device.validate_and_parse_config({"number": 2, "platform": "virtual"}, False)

            own_validate.assert_called_once()
            default_validate.assert_not_called()
