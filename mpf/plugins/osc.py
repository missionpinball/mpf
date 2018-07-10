"""MPF plugin to control the machine via OSC."""
import asyncio
import logging

from mpf.core.switch_controller import MonitoredSwitchChange
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

PYPY = False
if PYPY:
    from mpf.core.machine import MachineController


class Osc(object):

    """Plays back switch sequences from a config file, used for testing."""

    def __init__(self, machine):
        """Initialise switch player."""
        self.log = logging.getLogger('osc')
        self.machine = machine  # type: MachineController

        if 'osc' not in machine.config:
            machine.log.debug('"osc:" section not found in '
                              'machine configuration, so the OSC'
                              'plugin will not be used.')
            return

        self.config = self.machine.config['osc']
        self.machine.config_validator.validate_config("osc", self.config)
        if not self.config['enabled']:
            return

        self.dispatcher = Dispatcher()
        self.dispatcher.map("/sw/*", self.handle_switch)
        self.server = AsyncIOOSCUDPServer((self.config['server_ip'], self.config['server_port']), self.dispatcher,
                                          self.machine.clock.loop)

        self.machine.events.add_async_handler("init_phase_5", self._start)

        self.client = SimpleUDPClient(self.config['client_ip'], self.config['client_port'])

    @asyncio.coroutine
    def _start(self):
        yield from self.server.serve_async()
        self.machine.switch_controller.add_monitor(self._notify_switch_changes)


    def __repr__(self):
        """Return string representation."""
        return '<Osc>'

    def handle_switch(self, switch_name, state):
        """Handle Switch change from OSC."""
        self.machine.switch_controller.process_switch(switch_name, bool(state), logical=True)

    def _notify_switch_changes(self, change: MonitoredSwitchChange):
        """Send switch change to OSC client."""
        self.client.send_message("/sw/{}".format(change.name), change.state)


plugin_class = Osc
