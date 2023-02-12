"""Fast servo implementation."""
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface


class FastServo(ServoPlatformInterface):

    """A servo in the FAST platform connected to a FAST Expansion Board."""

    # __slots__ = ["number", "exp_connection"]

    def __init__(self, config, exp_connection):
        """Initialise servo."""
        self.config = config
        self.exp_connection = exp_connection

        board_address, breakout_address, device = self.exp_connection.get_address_from_number_string(config['number'])

        self.base_address = f'{board_address}{breakout_address}'
        self.servo_index = str(int(device[-1]) - 1)  # Servos are 0-indexed

        assert(board_address in exp_connection.exp_boards, f"Board address {board_address} not found")
        assert(self.base_address in ['B40', 'B50', 'B60', 'B70'], f"Board address not valid")  # Servos only on EXP-0071 boards for now

        self.write_config_to_servo()

    def write_config_to_servo(self):

        # TODO need proper config validation for platform_settings

        min_us = f"{self.config['platform_settings']['min_us']:02X}"
        max_us = f"{self.config['platform_settings']['max_us']:02X}"
        home_us = f"{self.config['platform_settings']['home_us']:02X}"
        max_runtime = f"{self.config['platform_settings']['max_runtime']:02X}"

        self.exp_connection.send_blind(f"EM@{self.base_address}:{self.servo_index},1,{max_runtime},{min_us},{max_us},{home_us}")

    def go_to_position(self, position):
        """Set a servo position."""
        if position < 0 or position > 1:
            raise AssertionError("Position has to be between 0 and 1")

        # convert from [0,1] to [0, 255]
        position_hex = f'{int(position * 255):02X}'

        cmd = f'MP@{self.base_address}:{self.servo_index},{position_hex},FFFF'

        self.exp_connection.send_blind(cmd)

    def set_speed_limit(self, speed_limit):
        """Not implemented."""

    def set_acceleration_limit(self, acceleration_limit):
        """Not implemented."""

    def stop(self):
        """Not implemented."""
