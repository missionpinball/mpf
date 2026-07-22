"""Fast dc motor implementation."""

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.motor_platform_interface import MotorPlatformInterface


class FastMotor(MotorPlatformInterface):

    """A dc motor in the FAST platform connected to a FAST Expansion Board."""

    __slots__ = ["base_address", "config", "exp_connection", "log", "motor_index"]

    def __init__(self, breakout_board, port, config):
        """Initialize dc motor."""
        self.config = config
        self.exp_connection = breakout_board.communicator

        self.motor_index = Util.int_to_hex_string(int(port) - 1)  # Motors are 0-indexed
        self.base_address = breakout_board.address
        self.log = breakout_board.log

    def pulse(self, duration_secs=None, power=None):
        """Pulse the motor at the specified power for the specified duration."""
        if not power or not duration_secs:
            self.log.debug("Motor pulse called with no power or duration, will not move.")
            return

        base_command = "MF"
        hex_power = Util.float_to_hex(power)
        hex_duration = Util.int_to_hex_string(duration_secs * 1000, True)
        self.log.debug("Pulsing motor index %s: for %s seconds with power %s", self.motor_index, duration_secs, power)

        self._send_command(base_command, [hex_duration, hex_power])

    def reverse_pulse(self, duration_secs=None, power=None):
        """Pulse the motor at the specified power for the specified duration in reverse."""
        if not power or not duration_secs:
            self.log.debug("Motor reverse pulse called with no power or duration, will not move.")
            return

        base_command = "MR"
        hex_power = Util.float_to_hex(power)
        hex_duration = Util.int_to_hex_string(duration_secs * 1000, True)
        self.log.debug("Pulsing motor index %s: for %s seconds with power %s in reverse",
                       self.motor_index, duration_secs, power)

        self._send_command(base_command, [hex_duration, hex_power])

    def stop(self):
        """Called during shutdown."""
        self.log.debug("Stopping motor")
        self._send_command("MC")

    def _send_command(self, base_command, payload=None):
        if not payload:
            payload = []
        self.exp_connection.send_and_forget(','.join([
            f'{base_command}@{self.base_address}:{self.motor_index}', *payload]))
