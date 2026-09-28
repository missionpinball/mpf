"""Fast shaker implementation."""

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.shaker_platform_interface import ShakerPlatformInterface


class FastShaker(ShakerPlatformInterface):

    """A shaker in the FAST platform connected to a FAST Expansion Board."""

    __slots__ = ["base_address", "config", "exp_connection", "log", "shaker_index"]

    def __init__(self, breakout_board, port, config):
        """Initialize servo."""
        self.config = config
        self.exp_connection = breakout_board.communicator

        self.shaker_index = Util.int_to_hex_string(int(port) - 1)  # Steppers are 0-indexed
        self.base_address = breakout_board.address
        self.log = breakout_board.log

        #self.exp_connection.register_processor('MS:', self.base_address, self.shaker_index, self._process_ms)

    def pulse(self, duration_secs=None, power=None):
        """Pulse the shaker at the specified power for the specified duration."""
        if not power or not duration_secs:
            self.log.debug("Shaker pulse called with no power or duration, will not shake.")
            return

        base_command = "MF"
        hex_power = Util.float_to_hex(power)
        hex_duration = Util.int_to_hex_string(duration_secs * 1000, True)
        self.log.debug("Pulsing shaker index %s: for %s seconds with power %s", self.shaker_index, duration_secs, power)

        self._send_command(base_command, [hex_duration, hex_power])

    def stop(self):
        """Called during shutdown."""
        self.log.debug("Stopping shaker")
        self._send_command("MC")

    def _send_command(self, base_command, payload=None):
        if not payload:
            payload = []
        self.exp_connection.send_and_forget(','.join([
            f'{base_command}@{self.base_address}:{self.shaker_index}', *payload]))
