"""MPF plugin allows a machine to be controlled by an OSC client.

This mode requires pyOSC, https://trac.v2.nl/wiki/pyOSC
It was written for pyOSC 0.3.5b build 5394, though later versions should work.
"""

import logging
import socket
import threading
import locale

try:
    # noinspection PyPep8Naming
    from . import OSC as OSCmodule  # noqa
    socket.gethostbyname(socket.gethostname())
    import_success = True
except ImportError:
    import_success = False
    OSCmodule = None


class OSC(object):

    """OSC plugin."""

    def __init__(self, machine):
        """Initialise OSC plugin."""
        if 'osc' not in machine.config:
            machine.log.debug('"OSC:" section not found in the machine '
                              'configuration, so the OSC plugin will not '
                              'be used.')
            return

        if not import_success:
            raise AssertionError('OSC plugin requires PyOSC which does not '
                                 'appear to be installed.')

        self.log = logging.getLogger('osc')
        self.machine = machine
        self.server = None
        self.server_thread = None

        self.config = self.machine.config_validator.validate_config(
            config_spec='osc', source=self.machine.config['osc'])

        if self.config['machine_ip'].lower() == 'auto':
            try:
                self.config['machine_ip'] = (
                    socket.gethostbyname(socket.gethostname()))
            except socket.gaierror:
                self.config['machine_ip'] = '127.0.0.1'

        self.osc_clients = dict()
        self.osc_message = False
        self.client_mode = 'name'
        self.clients_to_delete = list()
        self.clients_to_add = list()

        # If this machine uses WPC driver boards then we can drive devices by #
        self.wpc = (self.machine.config['hardware']['driverboards'][0:3] == 'wpc')

        # register for events
        self.machine.events.add_handler('init_phase_4', self.start)

        self.message_parsers = {
            "SW": self.process_switch,
            "REFRESH": self.process_refresh,
            "LIGHT": self.process_light,
            "COIL": self.process_coil,
            "EV": self.process_event,
            "AUDITS": self._update_audits,
            "CONFIG": self.process_config,
            "SYNC": self.process_sync,
            "WPCSYNC": self.process_wpcsync,
            "FLIPPER": self.process_flipper,
        }

    def start(self):
        """Start the OSC server."""
        receive_address = (self.config['machine_ip'],
                           self.config['machine_port'])
        self.server = OSCmodule.OSCServer(receive_address)
        self.server.addDefaultHandlers()
        self.server.addMsgHandler("default", self.process_message)

        # start the OSC server
        self.log.info("OSC Host listening on %s:%s", self.config['machine_ip'],
                      self.config['machine_port'])
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True  # needed so OSC thread shuts down
        self.server_thread.start()

        if 'switches' in self.config['client_updates']:
            self.register_switches()

        if 'lights' in self.config['client_updates']:
            self.register_lights()

        if 'data' in self.config['client_updates']:
            self._register_data()

    def stop(self):
        """Stop the OSC server."""
        self.server.close()
        self.log.info("Waiting for the OSC host thread to finish")
        self.server_thread.join()
        self.log.debug("OSC host thread is done.")

    def process_message(self, addr, tags, data, client_address):
        """Receive OSC messages and act on them."""
        if self.config['debug_messages']:
            self.log.debug("Incoming OSC message. Client IP: %s, Message: %s, %s"
                           ", %s", client_address, addr, tags, data)

        # Separate the incoming message into category and name parts.
        # For example "/sw/rollover1" is split into "sw" and "rollover1"

        cat = (addr.split("/"))[1]  # [1] since addr begins with a delimiter

        try:
            name = addr.split("/")[2]
        except IndexError:
            name = None  # catches incoming messages that are just one part

        # if this client is not connected, set up a connection
        if client_address not in self.osc_clients:
            self._found_new_osc_client(client_address)

        if cat.upper() in self.message_parsers:
            self.message_parsers[cat.upper()](name, data)
        elif self.config['debug_messages']:
            self.log.warning("Last incoming OSC message was invalid")

    # legacy method which does nothing
    def process_refresh(self, name, data):
        """Process refresh."""
        pass

    def process_sync(self, name, data):
        """Process sync."""
        del name
        if data[0] == 1:
            self.client_mode = 'name'
            self.client_update_all()

    def process_wpcsync(self, name, data):
        """Process wpc sync."""
        del name
        if data[0] == 1:
            self.client_mode = 'wpc'
            self.client_update_all()

    def process_switch(self, switch, data):
        """Process a switch event received from the OSC client."""
        # if the switch name is not valid and we're on WPC hardware, let's try
        # it as a number
        if (switch not in self.machine.switches and self.wpc and
                self.machine.switches.number('S' + str(switch))):
            switch = self.machine.switches.number('S' + str(switch)).name

        if switch in self.machine.switches:
            self.machine.switch_controller.process_switch(name=switch,
                                                          state=int(data[0]),
                                                          logical=True)
        else:
            self.log.debug("Received OSC command for invalid switch '%s'. "
                           "Ignoring...", switch)

    def process_light(self, light, data):
        """Process a light event received from the OSC client."""
        if light not in self.machine.lights and self.wpc:

            if len(light) == 1:
                light = '0' + light

            if self.client_mode == 'wpc':
                light = light.upper()
                if self.machine.lights.number(light):
                    light = self.machine.lights.number(light).name

        if light in self.machine.lights:
            self.machine.lights[light].on(int(255 * data[0]))
        else:
            self.log.debug("Received OSC command for invalid light '%s'. "
                           "Ignorring...", light)

    def process_coil(self, coil, data):
        """Process a coil event received from the OSC client."""
        del data
        if coil in self.machine.coils:
            self.machine.coils[coil].pulse()
            # todo more work to do here, like supporting variable hold times,
            # configurable pulse times, etc. But this is a start.

    def process_event(self, event, data):
        """Post an MPF event based on an event received from the OSC client."""
        del data
        self.machine.events.post(event)

    def process_flipper(self, flipper, data):
        """Call the flipper's sw_flip() or sw_release() event."""
        if data[0] == 1:
            self.machine.flippers[flipper].sw_flip()
        else:
            self.machine.flippers[flipper].sw_release()

    def register_switches(self):
        """Add switch handlers to all switches so the OSC client can receive updates."""
        for switch in self.machine.switches:
            self.machine.switch_controller.add_switch_handler(switch.name, self._client_update_switch,
                                                              1, return_info=True)
            self.machine.switch_controller.add_switch_handler(switch.name, self._client_update_switch,
                                                              0, return_info=True)

    def register_lights(self):
        """Add handlers to all lights so the OSC client can receive updates."""
        try:
            for light in self.machine.lights:
                light.add_handler(self._client_update_light)
        except AttributeError:
            pass

    def _register_data(self):
        self.machine.events.add_handler('player_turn_start', self._update_player)
        self.machine.events.add_handler('ball_started', self._update_ball)
        self.machine.events.add_handler('score_change', self._update_score)

    def _update_player(self, **kwargs):
        del kwargs
        self._update_score()
        self.client_send_osc_message("data", "player",
                                     self.machine.game.player['number'])

    def _update_ball(self, **kwargs):
        del kwargs
        self.client_send_osc_message("data", "ball",
                                     self.machine.game.player['ball'])

    def _update_score(self, **kwargs):
        del kwargs
        self.client_send_osc_message("data", "score", locale.format("%d", self.machine.game.player['score'],
                                                                    grouping=True))

    def _update_audits(self, event, data):
        """Send audit data to the OSC client."""
        # This method just sends all audits to the client whenever any OSC
        # message comes in that starts with /audits
        del event
        del data

        if not hasattr(self.machine, 'auditor'):
            return

        for category in self.machine.auditor.current_audits:
            for entry in self.machine.auditor.current_audits[category]:
                if category != 'Player':
                    self.client_send_osc_message(category="audits",
                                                 name=category + '/' + entry,
                                                 data=self.machine.auditor.current_audits[category][entry])

        if 'player' in self.machine.auditor.current_audits:
            for entry in self.machine.auditor.current_audits['player']:
                self.client_send_osc_message(category="audits",
                                             name='player/' + entry + '/average',
                                             data=self.machine.auditor.current_audits['player'][entry]['average'])
                self.client_send_osc_message(category="audits",
                                             name='player/' + entry + '/total',
                                             data=self.machine.auditor.current_audits['player'][entry]['total'])
                i = 0
                for dummy_iterator in self.machine.auditor.current_audits['player'][entry]['top']:
                    self.client_send_osc_message(category="audits",
                                                 name='player/' + entry + '/top/' + str(i + 1),
                                                 data=self.machine.auditor.current_audits['player'][entry]['top'][i])
                    i += 1

    def process_config(self, event, data):
        """Send config data to the OSC client."""
        # This method just sends all config data to the client whenever any OSC
        # message comes in that starts with /config
        pass

    def client_update_all(self):
        """Update the OSC client.

        Good for when it switches to a new tab or connects a new client.
        """
        self._client_update_all_switches()

    def _client_update_switch(self, switch_name, ms, state):
        del ms
        if self.client_mode == 'wpc':
            switch_name = str(self.machine.switches[switch_name].config['number']).lower()
        self.client_send_osc_message("sw", switch_name, state)

    def _client_update_light(self, light_name, brightness):
        if self.client_mode == 'wpc':
            light_name = str(self.machine.lights[light_name].config['number']).lower()
        self.client_send_osc_message("light", light_name, float(brightness / 255))

    def _client_update_all_switches(self):
        """Update all the switch states on the OSC client."""
        if self.client_mode == 'name':
            for switch in self.machine.switches:
                if self.machine.switch_controller.is_active(switch.name):
                    data = 1
                else:
                    data = 0
                self.client_send_osc_message("sw", switch.name, data)

        elif self.client_mode == 'wpc':
            for switch in self.machine.switches:
                if self.machine.switch_controller.is_active(switch.name):
                    data = 1
                else:
                    data = 0
                self.client_send_osc_message("sw", str(switch.config['number']).lower(), data)

    def client_send_osc_message(self, category, name, data):
        """Send an OSC message to the client to update it.

        Parameters:
        category - type of update, sw, coil, lamp, led, etc.
        name - the name of the object we're updating
        data - the data we're sending
        """
        for client in self.clients_to_add:
            self._setup_osc_client(client)

        if self.osc_clients:
            self.osc_message = OSCmodule.OSCMessage("/" + str(category) + "/" +
                                                    name)
            self.osc_message.append(data)

            for k in list(self.osc_clients.items()):
                try:
                    if self.config['debug_messages']:
                        self.log.debug("Sending OSC Message to client:%s: %s",
                                       k, self.osc_message)
                    k[1].send(self.osc_message)

                except OSCmodule.OSCClientError:
                    self.log.debug("OSC client at address %s disconnected", k[0])
                    # todo mark for deletion
                    self.clients_to_delete.append(k)
                    break

        for client in self.clients_to_delete:
            if client in self.osc_clients:
                del self.osc_clients[client]
        self.clients_to_delete = []

    def _found_new_osc_client(self, address):
        if address not in self.osc_clients:
            self.clients_to_add.append(address)

    def _setup_osc_client(self, address):
        """Setup a new OSC client."""
        self.log.info("OSC client at address %s connected", address[0])
        self.osc_clients[address] = OSCmodule.OSCClient()
        self.osc_clients[address].connect((address[0],
                                           self.config['client_port']))
        if address in self.clients_to_add:
            self.clients_to_add.remove(address)


plugin_class = OSC
