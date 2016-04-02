""" Contains the base class for autofire coil devices."""
from mpf.devices.driver import ReconfiguredDriver
from mpf.devices.switch import ReconfiguredSwitch
from mpf.core.system_wide_device import SystemWideDevice


class AutofireCoil(SystemWideDevice):
    """Base class for coils in the pinball machine which should fire
    automatically based on switch activity using hardware switch rules.

    autofire_coils are used when you want the coils to respond "instantly"
    without waiting for the lag of the python game code running on the host
    computer.

    Examples of autofire_coils are pop bumpers, slingshots, and flippers.

    Args: Same as Device.
    """

    config_section = 'autofire_coils'
    collection = 'autofires'
    class_label = 'autofire'

    def _initialize(self):
        self.coil = ReconfiguredDriver(self.config['coil'], self.config['coil_overwrite'])
        self.switch = ReconfiguredSwitch(self.config['switch'], self.config['switch_overwrite'],
                                         self.config['reverse_switch'])

        self.debug_log('Platform Driver: %s', self.platform)

    def prepare_config(self, config, is_mode_config):
        config = super().prepare_config(config, is_mode_config)
        if "coil_overwrite" not in config:
            config['coil_overwrite'] = ReconfiguredDriver.filter_from_config(config)
        if "switch_overwrite" not in config:
            config['switch_overwrite'] = ReconfiguredSwitch.filter_from_config(config)

        # TODO: find a better solution for this overwrite defaults
        if "debounce" not in config['switch_overwrite']:
            config['switch_overwrite']['debounce'] = False
        if "recycle" not in config['coil_overwrite']:
            config['coil_overwrite']['recycle'] = True

        return config

    def enable(self, **kwargs):
        """Enables the autofire coil rule."""
        del kwargs

        self.log.debug("Enabling")

        self.coil.set_pulse_on_hit_rule(self.switch)

    def disable(self, **kwargs):
        """Disables the autofire coil rule."""
        del kwargs
        self.log.debug("Disabling")
        self.coil.clear_hw_rule(self.switch)
