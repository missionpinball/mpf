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

        # board_address, breakout_address, device = self.exp_connection.get_address_from_number_string(config['number'])

        self.base_address = breakout_board.address
        self.servo_index = str(int(port) - 1)  # Servos are 0-indexed
        self.max_runtime = f"{config['max_runtime']:02X}"

        self.write_config_to_servo()

    def write_config_to_servo(self):
        min_us = f"{self.config['min_us']:02X}"
        max_us = f"{self.config['max_us']:02X}"
        home_us = f"{self.config['home_us']:02X}"

        self.exp_connection.send_and_confirm(f"EM@{self.base_address}:{self.servo_index},1,{self.max_runtime},{min_us},{max_us},{home_us}", 'EM:P')

    def go_to_position(self, position):
        """Set a servo position."""
        if position < 0 or position > 1:
            raise AssertionError("Position has to be between 0 and 1")

        # convert from [0,1] to [0, 255]
        position_hex = f'{int(position * 255):02X}'

        cmd = f'MP@{self.base_address}:{self.servo_index},{position_hex},{self.max_runtime}'

        self.exp_connection.send_blind(cmd)

    def set_speed_limit(self, speed_limit):
        """Not implemented."""

    def set_acceleration_limit(self, acceleration_limit):
        """Not implemented."""

    def stop(self):
        """Not implemented."""
