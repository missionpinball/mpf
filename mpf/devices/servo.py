"""Implements a servo in MPF."""
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("_position")
class Servo(SystemWideDevice):

    """Represents a servo in a pinball machine.

    Args: Same as the Device parent class.
    """

    config_section = 'servos'
    collection = 'servos'
    class_label = 'servo'

    def __init__(self, machine, name):
        """Initialise servo."""
        self.hw_servo = None
        self._position = None
        super().__init__(machine, name)

    def _initialize(self):
        self.load_platform_section('servo_controllers')

        for position in self.config['positions']:
            self.machine.events.add_handler(self.config['positions'][position],
                                            self._position_event,
                                            position=position)

        self.hw_servo = self.platform.configure_servo(self.config)

    def reset(self, **kwargs):
        """Go to reset position."""
        del kwargs
        self.go_to_position(self.config['reset_position'])

    def _position_event(self, position, **kwargs):
        del kwargs
        self.go_to_position(position)

    def go_to_position(self, position):
        """Move servo to position."""
        # linearly interpolate between servo limits
        position = self.config['servo_min'] + position * (
            self.config['servo_max'] - self.config['servo_min'])

        self._position = position

        # call platform with calculated position
        self.hw_servo.go_to_position(position)
