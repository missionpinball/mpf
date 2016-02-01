""" Implements a servo in MPF """

from collections import deque

from mpf.system.device import Device


class Servo(Device):
    """Represents a servo in a pinball machine.

    Args: Same as the Device parent class.
    """

    config_section = 'servos'
    collection = 'servos'
    class_label = 'servo'

    def __init__(self, machine, name, config, collection=None, validate=True):
        super().__init__(machine, name, config, collection,
                         validate=validate)

        self.platform = None

        for position in self.config['positions']:
            self.machine.events.add_handler(self.config['positions'][position],
                                            self._position_event,
                                            position=position)

    def reset(self, **kwargs):
        self.go_to_position(self.config['reset_position'])

    def _position_event(self, position, **kwargs):
        self.go_to_position(position)

    def go_to_position(self, position):
        position = self.config['servo_min'] + position * (
        self.config['servo_max'] - self.config['servo_min'])
        self.config['controller'].go_to_position(self.config['number'],
                                                 position)
