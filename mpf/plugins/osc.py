"""MPF plugin allows a machine to be controlled by an OSC client."""

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
import socket
import threading
import locale

global import_success

try:
    import OSC as OSCmodule
    socket.gethostbyname(socket.gethostname())
    import_success = True
except:
    import_success = False


def preload_check(machine):

    if import_success:
        return True
    else:
        return False


class OSC(object):

    def __init__(self, machine):

        self.log = logging.getLogger('OSC')
        self.machine = machine
        self.config = self.machine.config['OSC']

        if self.config['machine_ip'].upper() == 'AUTO':
            self.config['machine_ip'] = socket.gethostbyname(
                                                        socket.gethostname())

        if 'client_port' not in self.config:
            self.config['client_port'] = 8000

        if 'debug_messages' not in self.config:
                self.config['debug_messages'] = False

        if 'client_updates' in self.config:
            self.config['client_updates'] = self.config['client_updates'].split(
                                                                            ' ')
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

        if 'data' in self.config['client_updates']:
            self.register_data()

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

        try:
            name = addr.split("/")[2]
        except:
            name = None  # catches incoming messages that are just one part

        # if this client is not connected, set up a connection
        if client_address not in self.OSC_clients:
            self.found_new_OSC_client(client_address)

        if cat.upper() == 'SW':
            self.process_switch(name, data)
        elif cat.upper() == 'REFRESH':
            self.client_needs_sync = True  # is this used anymore?
        elif cat.upper() == 'LIGHT':
            self.process_light(name, data)
        elif cat.upper() == 'COIL':
            self.process_coil(name, data)
        elif cat.upper() == 'EV':
            self.process_event(name, data)
        elif cat.upper() == 'AUDITS':
            self.update_audits(name, data)
        elif cat.upper() == 'CONFIG':
            self.process_config(name, data)
        elif cat.upper() == 'SYNC':
            if data[0] == 1:
                self.client_mode = 'name'
                self.client_update_all()
        elif cat.upper() == 'WPCSYNC':
            if data[0] == 1:
                self.client_mode = 'wpc'
                self.client_update_all()
        elif cat.upper() == 'FLIPPER':
            self.process_flipper(name, data)
        elif self.config['debug_messages']:
            self.log.info("Last incoming OSC message was invalid")

    def process_switch(self, switch, data):
        """Processes a switch event received from the OSC client."""

        # if the switch name is not valid and we're on WPC hardware, let's try
        # it as a number
        if (switch not in self.machine.switches and self.wpc and
                self.machine.switches.config['number_str']('S' + str(switch))):
            switch = self.machine.switches.config['number_str']('S' +
                                                            str(switch)).name

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
            # todo more work to do here, like supporting variable hold times,
            # configurable pulse times, etc. But this is a start.

    def process_event(self, event, data):
        """Posts an MPF event based on an event received from the OSC client."""
        self.machine.events.post(event)

    def process_flipper(self, flipper, data):
        """Calls the flipper's sw_flip() or sw_release() event."""

        if data[0] == 1:
            self.machine.flippers[flipper].sw_flip()
        else:
            self.machine.flippers[flipper].sw_release()

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

    def register_data(self):
        self.machine.events.add_handler('player_turn_start', self.update_player)
        self.machine.events.add_handler('ball_started', self.update_ball)
        self.machine.events.add_handler('score_change', self.update_score)

    def update_player(self):
        self.update_score()
        self.client_send_OSC_message("data", "player",
                                     self.machine.game.player.vars['number'])

    def update_ball(self):
        self.client_send_OSC_message("data", "ball",
                                     self.machine.game.player.vars['ball'])

    def update_score(self, **kwargs):
        self.client_send_OSC_message("data", "score",
                                     locale.format("%d",
                                     self.machine.game.player.vars['score'],
                                     grouping=True))

    def update_audits(self, event, data):
        """Sends audit data to the OSC client."""

        # This method just sends all audits to the client whenever any OSC
        # message comes in that starts with /audits

        if not hasattr(self.machine, 'auditor'):
            return

        for category in self.machine.auditor.current_audits:
            for entry in self.machine.auditor.current_audits[category]:
                if category != 'Player':
                    self.client_send_OSC_message(category="audits",
                        name=category + '/' + entry,
                        data=self.machine.auditor.current_audits[category][entry])

        if 'Player' in self.machine.auditor.current_audits:
            for entry in self.machine.auditor.current_audits['Player']:
                self.client_send_OSC_message(category="audits",
                    name='Player/' + entry + '/average',
                    data=self.machine.auditor.current_audits['Player'][entry]
                        ['average'])
                self.client_send_OSC_message(category="audits",
                    name='Player/' + entry + '/total',
                    data=self.machine.auditor.current_audits['Player'][entry]
                        ['total'])
                i = 0
                for top in (self.machine.auditor.current_audits['Player']
                            [entry]['top']):
                    self.client_send_OSC_message(category="audits",
                        name='Player/' + entry + '/top/' + str(i+1),
                        data=self.machine.auditor.current_audits[
                            'Player'][entry]['top'][i])
                    i += 1

    def process_config(self, event, data):
        pass

    def update_config(self, event, data):
        """Sends config data to the OSC client."""

        # This method just sends all config data to the client whenever any OSC
        # message comes in that starts with /config
        pass

    def client_update_all(self):
        """ Update the OSC client.
        Good for when it switches to a new tab or connects a new client
        """
        self.client_update_all_switches()
        self.client_needs_sync = False

    def client_update_switch(self, switch_name, ms, state):
        if self.client_mode == 'wpc':
            switch_name = self.machine.switches[switch_name].config[
                                                        'number_str'].lower()
        self.client_send_OSC_message("sw", switch_name, state)

    def client_update_light(self, light_name, brightness):
        if self.client_mode == 'wpc':
            light_name = self.machine.lights[light_name].config[
                                                        'number_str'].lower()
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
                self.client_send_OSC_message("sw", switch.config[
                                             'number_str'].lower(), data)

    def client_send_OSC_message(self, category, name, data):
        """Sends an OSC message to the client to update it
        Parameters:
        category - type of update, sw, coil, lamp, led, etc.
        name - the name of the object we're updating
        data - the data we're sending
        """
        if self.OSC_clients:
            self.OSC_message = OSCmodule.OSCMessage("/" + str(category) + "/" +
                                                    name)
            self.OSC_message.append(data)

            for k in self.OSC_clients.items():
                try:
                    if self.config['debug_messages']:
                            self.log.info("Sending OSC Message to client:%s: "
                                           "%s", k, self.OSC_message, )
                    k[1].send(self.OSC_message)

                except OSCmodule.OSCClientError:
                    self.log.info("OSC client at address %s disconnected",
                                   k[0])
                    # todo mark for deletion
                    self.clients_to_delete.append(k)

        for client in self.clients_to_delete:
            print "removing OSC client", client
            print "current clients", self.OSC_clients
            if client in self.OSC_clients:
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
        self.OSC_clients[address].connect((address[0],
                                           self.config['client_port']))
        if address in self.clients_to_add:
            self.clients_to_add.remove(address)

# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
