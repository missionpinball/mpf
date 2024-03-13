"""MPF plugin which adds events from monitoring a Twitch chat room."""
import threading
from mpf.core.plugin import MpfPlugin

from .twitch.twitch_client import TwitchClient

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class TwitchBot(MpfPlugin):

    """Adds Twitch chat room events."""

    config_section = 'twitch_client'

    def initialize(self):
        """Initialize Twitch client."""
        self.configure_logging(self.name)
        self.config = self.machine.config_validator.validate_config(
            "twitch_client", self.machine.config['twitch_client'])

        self.log.info('Attempting to connect to Twitch')

        user_var = self.config['user_var']
        password_var = self.config['password_var']
        channel_var = self.config['channel_var']

        user = self.machine.variables.get_machine_var(
            user_var
        ) if user_var is not None else self.config['user']

        password = self.machine.variables.get_machine_var(
            password_var
        ) if password_var is not None else self.config['password']

        channel = self.machine.variables.get_machine_var(
            channel_var
        ) if channel_var is not None else self.config['channel']

        self.client = TwitchClient(self.machine, user, password, channel,
                                   self.machine.clock.loop)
        thread = threading.Thread(target=self.client.start, args=())
        thread.daemon = True
        thread.start()

        if self.client.is_connected():
            self.info_log('Successful connection to Twitch')
        else:
            self.info_log('Connecting...')
