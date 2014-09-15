"""Mission Pinball Framework plugin allows a machine to be controlled by an
OSC client."""

# osc.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

# This code requires pyOSC, https://trac.v2.nl/wiki/pyOSC
# It was written for pyOSC 0.3.5b build 5394,
# though I would expect later versions should work

# add support for approved client IPs
# add pincode support

# make it so switch and light handlers only exist if clients are connected

# add support for tags
# add support for x-y coords

import logging
import OSC as OSCmodule
import socket
import threading
import time


class OSC(object):

    def __init__(self, machine):
        self.log = logging.getLogger('OSC')
        self.machine = machine
        self.config = self.machine.config['OSC']

        if self.config['machine_ip'].upper() == 'AUTO':
            self.config['machine_ip'] = socket.gethostbyname(socket.gethostname())

        if 'client_port' not in self.config:
            self.config['client_port'] = 8000

        if 'debug_messages' not in self.config:
                self.config['debug_messages'] = False

        if 'client_updates' in self.config:
            self.config['client_updates'] = self.config['client_updates'].split(' ')
        else:
            self.config['client_updates'] = None

        self.OSC_clients = dict()
        self.client_needs_sync = False
        self.client_last_update_time = None
        self.last_loop_time = 1
        self.client_mode = 'name'
        self.clients_to_delete = list()
        self.clients_to_add = list()

        # If this machine uses WPC driver boards then we can drive devices by #
        if self.machine.config['Hardware']['DriverBoards'][0:3] == 'wpc':
            self.wpc = True
        else:
            self.wpc = False

        # register for events
        self.machine.events.add_handler('machine_init_phase3', self.start)

    def start(self):
        """Starts the OSC server."""
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

    def stop(self):
        """Stops the OSC server."""
        self.server.close()
        self.log.info("Waiting for the OSC host thread to finish")
        self.server_thread.join()
        self.log.info("OSC host thread is done.")

    def process_message(self, addr, tags, data, client_address):
        """Receives OSC messages and acts on them."""

        if self.config['debug_messages']:
            self.log.info("Incoming OSC message. Client IP: %s, Message: %s, %s"
                          ", %s", client_address, addr, tags, data)

        # Separate the incoming message into category and name parts.
        # For example "/sw/rollover1" is split into "sw" and "rollover1"

        cat = (addr.split("/"))[1]  # [1] since addr begins with a delimiter

        if cat == "refresh":  # client switched pages, mark for sync and return
            self.client_needs_sync = True
            return

        if len(addr) > 1:
            name = addr.split("/")[2]
        else:
            return

        # if this client is not connected, set up a connection
        if client_address not in self.OSC_clients:
            self.found_new_OSC_client(client_address)

        if cat.upper() == 'SW':
            self.process_switch(name, data)
        elif cat.upper() == 'LIGHT':
            self.process_light(name, data)
        elif cat.upper() == 'COIL':
            self.process_coil(name, data)
        elif cat.upper() == 'EV':
            self.process_event(name, data)
        elif cat.upper() == 'SYNC':
            if data[0] == 1:
                self.client_mode = 'name'
                self.client_update_all()
        elif cat.upper() == 'WPCSYNC':
            if data[0] == 1:
                self.client_mode = 'wpc'
                self.client_update_all()

    def process_switch(self, switch, data):
        """Processes a switch event received from the OSC client."""

        # if the switch name is not valid and we're on WPC hardware, let's try
        # it as a number
        if (switch not in self.machine.switches and self.wpc and
                self.machine.switches.config['number_str']('S' + str(switch))):
            switch = self.machine.switches.config['number_str']('S' + str(switch)).name

        if switch in self.machine.switches:
            self.machine.switch_controller.process_switch(name=switch,
                                                          state=int(data[0]),
                                                          logical=True)
        else:
            self.log.debug("Received OSC command for invalid switch '%s'. "
                           "Ignoring...", switch)

    def process_light(self, light, data):
        """Processes a light event received from the OSC client."""

        if light not in self.machine.lights and self.wpc:

            if len(light) == 1:
                light = '0' + light

            if self.client_mode == 'wpc':
                # todo change to generator
                light = light.upper()
                for l in self.machine.lights:
                    if l.config['number_str'] == light:
                        light = l.name

        if light in self.machine.lights:
            self.machine.lights[light].on(int(255*data[0]))
        else:
            self.log.debug("Received OSC command for invalid light '%s'. "
                           "Ignorring...", light)

    def process_coil(self, coil, data):
        """Processes a coil event received from the OSC client."""
        if coil in self.machine.coils:
            self.machine.coils[coil].pulse()

    def process_event(self, event, data):
        """Posts an MPF event based on an event received from the OSC client."""
        self.machine.events.post(event)

    def register_switches(self):
        """Adds switch handlers to all switches so the OSC client can receive
        updates."""
        for switch in self.machine.switches:
            self.machine.switch_controller.add_switch_handler(switch.name,
                                                    self.client_update_switch,
                                                    1,
                                                    return_info=True)
            self.machine.switch_controller.add_switch_handler(switch.name,
                                                    self.client_update_switch,
                                                    0,
                                                    return_info=True)

    def register_lights(self):
        """Adds handlers to all lights so the OSC client can receive
        updates."""
        for light in self.machine.lights:
            light.add_handler(self.client_update_light)

    def client_update_all(self):
        """ Update the OSC client.
        Good for when it switches to a new tab or connects a new client
        """
        self.client_update_all_switches()
        self.client_needs_sync = False  # since the sync is done we reset the flag

    def client_update_switch(self, switch_name, ms, state):
        if self.client_mode == 'wpc':
            switch_name = self.machine.switches[switch_name].config['number_str'].lower()
        self.client_send_OSC_message("sw", switch_name, state)

    def client_update_light(self, light_name, brightness):
        if self.client_mode == 'wpc':
            light_name = self.machine.lights[light_name].config['number_str'].lower()
        self.client_send_OSC_message("light", light_name, float(brightness/255))

    def client_update_all_switches(self):
        """ Updates all the switch states on the OSC client."""

        if self.client_mode == 'name':
            for switch in self.machine.switches:
                if self.machine.switch_controller.is_active(switch.name):
                    data = 1
                else:
                    data = 0
                self.client_send_OSC_message("sw", switch.name, data)

        elif self.client_mode == 'wpc':
            for switch in self.machine.switches:
                if self.machine.switch_controller.is_active(switch.name):
                    data = 1
                else:
                    data = 0
                self.client_send_OSC_message("sw", switch.config['number_str'].lower(),
                                             data)

    def client_send_OSC_message(self, category, name, data):
        """Sends an OSC message to the client to update it
        Parameters:
        category - type of update, sw, coil, lamp, led, etc.
        name - the name of the object we're updating
        data - the data we're sending
        """

        if self.OSC_clients:
            self.OSC_message = OSCmodule.OSCMessage("/" + str(category) + "/" + name)
            self.OSC_message.append(data)

            for k, v in self.OSC_clients.iteritems():
                try:
                    if self.config['debug_messages']:
                            self.log.debug("Sending OSC Message to client:%s: %s",
                                           k, self.OSC_message, )
                    v.send(self.OSC_message)

                except OSCmodule.OSCClientError:
                    self.log.debug("OSC client at address %s disconnected", k[0])
                    # todo mark for deletion
                    self.clients_to_delete.append(k)

        for client in self.clients_to_delete:
            del self.OSC_clients[client]
        self.clients_to_delete = []

        for client in self.clients_to_add:
            self.setup_OSC_client(client)

    def found_new_OSC_client(self, address):
        if address not in self.OSC_clients:
            self.clients_to_add.append(address)

    def setup_OSC_client(self, address):
        """Setup a new OSC client"""
        self.log.info("OSC client at address %s connected", address[0])
        self.OSC_clients[address] = OSCmodule.OSCClient()
        self.OSC_clients[address].connect((address[0], self.config['client_port']))
        if address in self.clients_to_add:
            self.clients_to_add.remove(address)
