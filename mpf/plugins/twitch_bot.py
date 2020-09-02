"""MPF plugin which automatically plays back switch events from the config file."""

import logging
import os
import threading
from mpf.core.scriptlet import Scriptlet
from .twitch.twitch_client import TwitchClient

class TwitchBot:
    def __init__(self, machine):
        """Initialise Twitch client."""
        self.log = logging.getLogger('twitch_client')

        if 'twitch_client' not in machine.config:
            machine.log.debug('"twitch_client:" section not found in '
                              'machine configuration, so the Twitch Client'
                              'plugin will not be used.')
            return

        self.config = self.machine.config['twitch_client']

        self.log.info('Attempting to connect to Twitch')
        self.client = TwitchClient(self.machine, self.config['user'], self.config['password'], self.config['channel'])
        thread = threading.Thread(target=self.client.start, args=())
        thread.daemon = True
        thread.start()

        if self.client.is_connected():
            self.info_log('Successful connection to Twitch')
        else:
            self.info_log('Connection error')

