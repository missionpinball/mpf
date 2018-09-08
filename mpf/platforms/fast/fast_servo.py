"""Fast servo implementation."""
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface


class FastServo(ServoPlatformInterface):

    """A servo in the FAST platform."""

    __slots__ = ["number", "net_connection"]

    def __init__(self, number, net_connection):
        """Initialise servo."""
        self.number = number
        self.net_connection = net_connection

    def go_to_position(self, position):
        """Set a servo position."""
        if position < 0 or position > 1:
            raise AssertionError("Position has to be between 0 and 1")

        # convert from [0,1] to [0, 255]
        position_numeric = int(position * 255)

        cmd = 'XO:{},{}'.format(
            self.number,
            Util.int_to_hex_string(position_numeric))

        self.net_connection.send(cmd)

    @classmethod
    def set_speed_limit(cls, speed_limit):
        """Todo emulate speed parameter."""
        pass

    @classmethod
    def set_acceleration_limit(cls, acceleration_limit):
        """Todo emulate acceleration parameter."""
        pass
