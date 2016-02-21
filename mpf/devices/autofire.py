""" Contains the base class for autofire coil devices."""

from mpf.core.device import Device


class AutofireCoil(Device):
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

    def __init__(self, machine, name, config=None, validate=True):
        super().__init__(machine, name, config, validate=validate)

        self.coil = self.config['coil']
        self.switch = self.config['switch']

        self.validate()

        self.switch_activity = 1

        if self.switch.invert:
            self.switch_activity = 0

        if self.config['reverse_switch']:
            self.switch_activity ^= 1

        if self.debug:
            self.log.debug('Platform Driver: %s', self.platform)

    def validate(self):
        """Autofire rules only work if the switch is on the same platform as the
        coil.

        In the future we may expand this to support other rules various platform
        vendors might have.

        """

        if self.switch.platform == self.coil.platform:
            self.platform = self.coil.platform
            return True
        else:
            return False

    def enable(self, **kwargs):
        """Enables the autofire coil rule."""

        # todo disable first to clear any old rules?

        self.log.debug("Enabling")

        # todo make this work for holds too?

        self.platform.set_hw_rule(sw_name=self.switch.name,
                                  sw_activity=self.switch_activity,
                                  driver_name=self.coil.name,
                                  driver_action='pulse',
                                  disable_on_release=False,
                                  **self.config)

    def disable(self, **kwargs):
        """Disables the autofire coil rule."""
        self.log.debug("Disabling")
        self.platform.clear_hw_rule(self.switch.name)
