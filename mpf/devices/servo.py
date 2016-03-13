""" Implements a servo in MPF """

from mpf.core.system_wide_device import SystemWideDevice


class Servo(SystemWideDevice):
    """Represents a servo in a pinball machine.

    Args: Same as the Device parent class.
    """

    config_section = 'servos'
    collection = 'servos'
    class_label = 'servo'

    def _initialize(self):
        self.load_platform_section('servo_controllers')

        for position in self.config['positions']:
            self.machine.events.add_handler(self.config['positions'][position],
                                            self._position_event,
                                            position=position)

    def reset(self, **kwargs):
        del kwargs
        self.go_to_position(self.config['reset_position'])

    def _position_event(self, position, **kwargs):
        del kwargs
        self.go_to_position(position)

    def go_to_position(self, position):
        # linearly interpolate between servo limits
        position = self.config['servo_min'] + position * (
            self.config['servo_max'] - self.config['servo_min'])

        # call platform with calculated position
        self.platform.servo_go_to_position(self.config['number'], position)
