"""MPF plugin to control the machine via OSC."""
import asyncio
import logging

from mpf.core.switch_controller import MonitoredSwitchChange

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController

# pythonosc is not a requirement for MPF so we fail with a nice error when loading
try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import AsyncIOOSCUDPServer
    from pythonosc.udp_client import SimpleUDPClient

except ImportError:
    Dispatcher = None
    AsyncIOOSCUDPServer = None
    SimpleUDPClient = None


class Osc:

    """Control switches via OSC."""

    def __init__(self, machine):
        """Initialise switch player."""
        self.log = logging.getLogger('OSC Plugin')
        self.machine = machine  # type: MachineController

        if 'osc_plugin' not in machine.config:
            machine.log.debug('"osc_plugin:" section not found in '
                              'machine configuration, so the OSC'
                              'plugin will not be used.')
            return

        if not Dispatcher:
            raise AssertionError("To use the OSC plugin you need to install the pythonosc extension.")

        self.config = self.machine.config['osc_plugin']
        self.machine.config_validator.validate_config("osc_plugin", self.config)
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
        yield from self.server.create_serve_endpoint()
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
