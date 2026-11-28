import inspect

from mpf.core.machine import MachineController
from mpf.tests.MpfTestCase import MpfTestCase


class BaseMpfMachineTestCase(MpfTestCase):

    def get_enable_plugins(self):
        return True

    def get_config_file(self):
        return "config.yaml"

    def get_machine_path(self):
        return ""

    def get_absolute_machine_path(self):
        # do not use path relative to MPF folder
        return self.get_machine_path()

    def get_platform(self):
        return 'smart_virtual'


class MpfMachineTestCase(BaseMpfMachineTestCase):

    """MPF only machine test case."""

    def get_use_bcp(self):
        return True

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)

        # remove config patches
        self.machine_config_patches = dict()
        # use bcp mock
        self.machine_config_patches['bcp'] = \
            {"connections": {"local_display": {"type": "mpf.tests.MpfBcpTestCase.MockBcpClient"}}, "servers": []}

        # increase test expected duration
        self.expected_duration = 5.0
