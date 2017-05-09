import inspect

from mpf.core.utility_functions import Util
from mpf.tests.MpfTestCase import MpfTestCase


class TestDeviceManager(MpfTestCase):

    def test_control_events_arguments(self):
        for device_type in self.machine.config['mpf']['device_modules']:

            device_cls = Util.string_to_class(device_type)

            config_spec = self.machine.config_validator.config_spec[device_cls.config_section]

            for k in config_spec:
                if not k.endswith('_events') or k == "control_events":
                    continue
                method_name = k[:-7]
                method = getattr(device_cls, method_name, None)
                self.assertIsNotNone(method, "Method {}.{} is missing for {}".format(device_type, method_name, k))

                sig = inspect.signature(method)

                self.assertTrue(sig.parameters['self'],
                    "Method {}.{} is missing self. Actual signature: {}".format(
                    device_type, method_name, sig))

                self.assertTrue('kwargs' in sig.parameters,
                    "Method {}.{} is missing **kwargs. Actual signature: {}".format(
                    device_type, method_name, sig))

                self.assertEqual(sig.parameters['kwargs'].kind, inspect._VAR_KEYWORD,
                    "Method {}.{} kwargs param is missing '**'".format(
                    device_type, method_name))
