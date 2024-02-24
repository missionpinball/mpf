"""Fast servo implementation."""
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface


class FastServo(ServoPlatformInterface):

    """A servo in the FAST platform connected to a FAST Expansion Board."""

    # __slots__ = ["number", "exp_connection"]

    def __init__(self, breakout_board, port, config):
        """Initialize servo."""
        self.config = config
        self.exp_connection = breakout_board.communicator

        self.base_address = breakout_board.address
        self.servo_index = str(int(port) - 1)  # Servos are 0-indexed
        self.max_runtime = f"{config['max_runtime']:02X}"

        self.write_config_to_servo()

    def write_config_to_servo(self):
        min_us = f"{self.config['min_us']:02X}"
        max_us = f"{self.config['max_us']:02X}"
        home_us = f"{self.config['home_us']:02X}"

        # EM:<INDEX>,1,<MAX_TIME_MS>,<MIN>,<MAX>,<NEUTRAL><CR>
        self.exp_connection.send_with_confirmation(
            f"EM@{self.base_address}:{self.servo_index},1,{self.max_runtime},{min_us},{max_us},{home_us}",
            'EM:P')

    def go_to_position(self, position):
        """Set a servo position."""
        if position < 0 or position > 1:
            raise AssertionError("Position has to be between 0 and 1")

        # MP:<INDEX>,<POSITION>,<TIME_MS><CR>
        self.exp_connection.send_and_forget(f'MP@{self.base_address}:{self.servo_index},{int(position * 255):02X},{self.max_runtime}')

    def set_speed_limit(self, speed_limit):
        """ Called during servo init """
        pass

    def set_acceleration_limit(self, acceleration_limit):
        """ Called during servo init """
        pass

    def stop(self):
        """ Called during shutdown """
        pass
        # TODO: send command to go home and power off servo
