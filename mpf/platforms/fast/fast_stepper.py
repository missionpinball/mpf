"""Fast servo implementation."""

import asyncio

from mpf.core.utility_functions import Util
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface

POLL_MS = 100

class FastStepper(StepperPlatformInterface):

    """A stepper in the FAST platform connected to a FAST Expansion Board."""

    # __slots__ = ["number", "exp_connection"]

    def __init__(self, breakout_board, port, config):
        """Initialize servo."""
        self.config = config
        self.exp_connection = breakout_board.communicator

        self.base_address = breakout_board.address
        # Try this
        self.base_address = '90'
        #
        self.stepper_index = Util.int_to_hex_string(int(port) - 1)  # Steppers are 0-indexed

        self.exp_connection.register_processor('MS:', self.base_address, self.stepper_index, self._process_ms)
        # self.max_runtime = f"{config['max_runtime']:02X}"

    #     self.write_config_to_servo()

    # def write_config_to_servo(self):
    #     """Send the servo configuration to the platform."""
    #     min_us = f"{self.config['min_us']:02X}"
    #     max_us = f"{self.config['max_us']:02X}"
    #     home_us = f"{self.config['home_us']:02X}"

    #     # EM:<INDEX>,1,<MAX_TIME_MS>,<MIN>,<MAX>,<NEUTRAL><CR>
    #     self.exp_connection.send_with_confirmation(
    #         f"EM@{self.base_address}:{self.stepper_index},1,{self.max_runtime},{min_us},{max_us},{home_us}",
    #         'EM:P')

    def home(self, direction):
        if direction != 'counterclockwise':
            raise ConfigFileError("FAST Stepper only supports home in counter-clockwise direction. "
                                  "Please rewire your motor and set homing_direction: counterclockwise "
                                  "in your stepper config.", 1, self.__class__.__name__)
        self._send_command("MH")

    async def wait_for_move_completed(self):
        # return
        polls = 0
        while True:
            await asyncio.sleep(1 / POLL_MS)
            self._send_command('MS')
            polls += 1
            if polls > 500:
                return

    def move_rel_pos(self, position, speed=None):
        """Move the servo a relative number of steps position."""
        if not position:
            return

        base_command = "MF" if position > 0 else "MR"
        hex_position = Util.int_to_hex_string(position, True)
        cmd_args = [hex_position]
        print(f"Moving stepper {self.stepper_index} with speed {speed}")

        if speed:
            if speed < 350 or speed > 1650:
                raise ConfigFileError("FAST Stepper only supports speeds between 350-1650, "
                                      f"but received value of {speed}.",
                                      2, self.__class__.__name__)
            speed = Util.int_to_hex_string(speed, True)
            cmd_args.append(speed)

        self._send_command(base_command, cmd_args)

    def move_vel_mode(self, _velocity):
        pass

    def stop(self):
        """Called during shutdown."""
        self._send_command("MC")

    def set_home_position(self):
        pass

    def _send_command(self, base_command, payload=[]):
        self.exp_connection.send_and_forget(','.join([
            f'{base_command}@{self.base_address}:{self.stepper_index}', *payload]))

    def _process_ms(self, message):
        print(f"FASTStepper {self.stepper_index} has an MS message! '{message}'")
