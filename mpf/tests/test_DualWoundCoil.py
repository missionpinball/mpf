"""Test dual wound coil."""
from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestDualWoundCoil(MpfTestCase):

    def getConfigFile(self):
        return 'config_dual_wound_coil.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/device/'

    def testBasicFunctions(self):
        c_power = self.machine.coils.c_power.hw_driver
        c_hold = self.machine.coils.c_hold.hw_driver
        c_power.enable = MagicMock()
        c_power.disable = MagicMock()
        c_power.pulse = MagicMock()
        c_hold.enable = MagicMock()
        c_hold.disable = MagicMock()
        c_hold.pulse = MagicMock()

        # test enable
        self.machine.coils.c_test.enable()
        c_power.pulse.assert_called_with(self.machine.coils.c_power.get_configured_driver(), 20)
        c_power.pulse = MagicMock()
        assert not c_power.enable.called
        c_hold.enable.assert_called_with(self.machine.coils.c_hold.get_configured_driver())
        c_hold.enable = MagicMock()
        assert not c_hold.pulse.called

        # test disable
        self.machine.coils.c_test.disable()
        c_power.disable.assert_called_with(self.machine.coils.c_power.get_configured_driver())
        c_power.disable = MagicMock()
        c_hold.disable.assert_called_with(self.machine.coils.c_hold.get_configured_driver())
        c_hold.disable = MagicMock()

        # test pulse
        self.machine.coils.c_test.pulse(17)
        c_power.pulse.assert_called_with(self.machine.coils.c_power.get_configured_driver(), 17)
        c_hold.pulse.assert_called_with(self.machine.coils.c_hold.get_configured_driver(), 17)

        # test default pulse
        self.machine.coils.c_test.pulse()
        c_power.pulse.assert_called_with(self.machine.coils.c_power.get_configured_driver(), 20)
        c_hold.pulse.assert_called_with(self.machine.coils.c_hold.get_configured_driver(), 10)
