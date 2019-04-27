"""A dual wound coil which consists of two coils."""
from mpf.core.events import event_handler
from mpf.core.system_wide_device import SystemWideDevice


class DualWoundCoil(SystemWideDevice):

    """An instance of a dual wound coil which consists of two coils."""

    config_section = "dual_wound_coils"  # String of the config section name
    collection = "dual_wound_coils"  # String name of the collection
    class_label = "dual_wound_coil"  # String of the friendly name of the device class

    def __init__(self, machine, name):
        """Initialise a dual wound coil."""
        super().__init__(machine, name)
        # Add this device to the coil section
        self.machine.coils[name] = self

    @event_handler(2)
    def event_enable(self, **kwargs):
        """Event handler for enable event."""
        del kwargs
        self.enable()

    def enable(self):
        """Enable a dual wound coil.

        Pulse main coil and enable hold coil.
        """
        self.config['main_coil'].pulse()
        self.config['hold_coil'].enable()

    @event_handler(1)
    def event_disable(self, **kwargs):
        """Event handler for disable event."""
        del kwargs
        self.disable()

    def disable(self):
        """Disable a driver."""
        self.config['main_coil'].disable()
        self.config['hold_coil'].disable()

    @event_handler(3)
    def event_pulse(self, milliseconds: int = None, power: float = None, **kwargs):
        """Event handler for pulse event."""
        del kwargs
        self.pulse(milliseconds, power)

    def pulse(self, milliseconds: int = None, power: float = None):
        """Pulse this driver.

        Args:
            milliseconds: The number of milliseconds the driver should be
                enabled for. If no value is provided, the driver will be
                enabled for the value specified in the config dictionary.
            power: A multiplier that will be applied to the default pulse time,
                typically a float between 0.0 and 1.0. (Note this is can only be used
                if milliseconds is also specified.)
        """
        self.config['main_coil'].pulse(milliseconds, power)
        self.config['hold_coil'].pulse(milliseconds, power)
