"""MPF plugin which adds events from monitoring a Twitch chatroom."""
import threading
from mpf.core.logging import LogMixin

from .twitch.twitch_client import TwitchClient

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class TwitchBot(LogMixin):

    """Adds Twitch Chat Room events."""

    def __init__(self, machine):
        """Initialise Twitch client."""
        super().__init__()
        self.machine = machine      # type: MachineController
        self.configure_logging("twitch_client")

        if 'twitch_client' not in machine.config:
            self.log.debug('"twitch_client:" section not found in '
                           'machine configuration, so the Twitch Client'
                           'plugin will not be used.')
            return

        self.config = self.machine.config_validator.validate_config(
            "twitch_client", self.machine.config['twitch_client'])

        self.log.info('Attempting to connect to Twitch')
        # THIS SHOULD BE MACHINE VARIABLES
        self.client = TwitchClient(self.machine, self.config['user'], self.config['password'], self.config['channel'],
                                   self.machine.clock.loop)
        thread = threading.Thread(target=self.client.start, args=())
        thread.daemon = True
        thread.start()

        if self.client.is_connected():
            self.info_log('Successful connection to Twitch')
        else:
            self.info_log('Connection error')
