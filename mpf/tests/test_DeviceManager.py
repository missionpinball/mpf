import inspect

from mpf.core.utility_functions import Util
from mpf.tests.MpfTestCase import MpfTestCase


class TestDeviceManager(MpfTestCase):

    def test_control_events_arguments(self):
        for device_type in self.machine.config['mpf']['device_modules']:

            device_cls = Util.string_to_class("mpf.devices." + device_type)

            config_spec = self.machine.config_validator.config_spec[device_cls.config_section]

            for k in config_spec:
                if not k.endswith('_events'):
                    continue
                method_name = k[:-7]
                method = getattr(device_cls, method_name, None)
                self.assertIsNotNone(method, "Method {}.{} is missing for {}".format(device_type, method_name, k))

                argspec = inspect.getargspec(method)

                self.assertEqual("self", argspec.args[0], "Method {}.{} is missing self. Argspec: {}".format(
                    device_type, method_name, argspec))

                self.assertTrue(argspec.keywords, "Method {}.{} is missing kwargs. Argspec: {}".format(
                    device_type, method_name, argspec))
