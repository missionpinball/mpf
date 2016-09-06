"""Contains the base class for autofire coil devices."""
from mpf.core.device_monitor import DeviceMonitor

from mpf.devices.driver import ReconfiguredDriver
from mpf.devices.switch import ReconfiguredSwitch
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("_enabled")
class AutofireCoil(SystemWideDevice):

    """Coils in the pinball machine which should fire automatically based on switch hits using hardware switch rules.

    autofire_coils are used when you want the coils to respond "instantly"
    without waiting for the lag of the python game code running on the host
    computer.

    Examples of autofire_coils are pop bumpers, slingshots, and flippers.

    Args: Same as Device.
    """

    config_section = 'autofire_coils'
    collection = 'autofires'
    class_label = 'autofire'

    def __init__(self, machine, name):
        """Initialise autofire."""
        self.coil = None
        self.switch = None
        self._enabled = False
        super().__init__(machine, name)

    def _initialize(self):
        if "debounce" not in self.config['switch_overwrite']:
            self.config['switch_overwrite']['debounce'] = "quick"
        if "recycle" not in self.config['coil_overwrite']:
            self.config['coil_overwrite']['recycle'] = True

        self.coil = ReconfiguredDriver(self.config['coil'], self.config['coil_overwrite'])
        self.switch = ReconfiguredSwitch(self.config['switch'], self.config['switch_overwrite'],
                                         self.config['reverse_switch'])

        self.debug_log('Platform Driver: %s', self.platform)

    def enable(self, **kwargs):
        """Enable the autofire coil rule."""
        del kwargs

        if self._enabled:
            return
        self._enabled = True

        self.log.debug("Enabling")

        self.coil.set_pulse_on_hit_rule(self.switch)

    def disable(self, **kwargs):
        """Disable the autofire coil rule."""
        del kwargs

        if not self._enabled:
            return
        self._enabled = False

        self.log.debug("Disabling")
        self.coil.clear_hw_rule(self.switch)
