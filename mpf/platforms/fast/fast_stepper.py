"""Fast servo implementation."""

import asyncio

from mpf.core.utility_functions import Util
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface

POLL_MS = 100

class FastStepper(StepperPlatformInterface):

    """A stepper in the FAST platform connected to a FAST Expansion Board."""

    __slots__ = ["base_address", "config", "exp_connection", "log", "stepper_index",
                 "_is_moving"]

    def __init__(self, breakout_board, port, config):
        """Initialize servo."""
        self.config = config
        self.exp_connection = breakout_board.communicator

        self.stepper_index = Util.int_to_hex_string(int(port) - 1)  # Steppers are 0-indexed
        self.base_address = breakout_board.address
        self.log = breakout_board.log

        self.exp_connection.register_processor('MS:', self.base_address, self.stepper_index, self._process_ms)
        self._is_moving = False


    def home(self, direction):
        if direction != 'counterclockwise':
            raise ConfigFileError("FAST Stepper only supports home in counter-clockwise direction. "
                                  "Please rewire your motor and set homing_direction: counterclockwise "
                                  "in your stepper config.", 1, self.__class__.__name__)
        self._is_moving = True
        self._send_command("MH")

    async def wait_for_move_completed(self):
        # return
        while True:
            if not self._is_moving:
                return
            await asyncio.sleep(1 / POLL_MS)
            self._send_command('MS')

    def move_rel_pos(self, position, speed=None):
        """Move the servo a relative number of steps position."""
        if not position:
            return

        base_command = "MF" if position > 0 else "MR"
        hex_position = Util.int_to_hex_string(position, True)
        cmd_args = [hex_position]
        self.log.debug("Moving stepper index %s: %s steps with speed %s", self.stepper_index, position, speed)

        if speed:
            if speed < 350 or speed > 1650:
                raise ConfigFileError("FAST Stepper only supports speeds between 350-1650, "
                                      f"but received value of {speed}.",
                                      2, self.__class__.__name__)
            speed = Util.int_to_hex_string(speed, True)
            cmd_args.append(speed)

        self._is_moving = True
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
        _index, state = message.split(",")
        state_flags = Util.hex_string_to_int(state)
        self._is_moving = state_flags & 1
