"""Contains code for an Open Pixel Controller hardware for RGB LEDs."""
# openpixel.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

# The python code to build the OPC message packet came from here:
# https://github.com/zestyping/openpixelcontrol/blob/master/python_clients/opc.py

import logging
import socket

from mpf.system.platform import Platform



# todo move OPC client to its own thread
# todo change all LED colors to tuples instead of lists


class HardwarePlatform(Platform):
    """Base class for the open pixel hardware platform."""

    def __init__(self, machine):

        super(HardwarePlatform, self).__init__(machine)

        self.log = logging.getLogger("OpenPixel")
        self.log.debug("Configuring Open Pixel hardware interface.")
        self.opc_client = None

    def configure_led(self, config):

        if not self.opc_client:
            self._setup_opc_client()

        if type(config['number']) is str and '-' in config['number']:
            channel, led = config['number'].split('-')
        else:
            led = config['number']
            channel = 0

        return OpenPixelLED(self.opc_client, channel, led)

        self.opc_client.add_pixel(channel, led)

    def _setup_opc_client(self):
        self.opc_client = OpenPixelClient(self.machine,
            server=self.machine.config['openpixelcontrol']['host'],
            port=self.machine.config['openpixelcontrol']['port'])


class OpenPixelLED(object):
    def __init__(self, opc_client, channel, led):
        self.log = logging.getLogger('OpenPixelLED')

        self.opc_client = opc_client
        self.channel = int(channel)
        self.led = int(led)
        self.opc_client.add_pixel(self.channel, self.led)

    def color(self, color):
        self.log.debug("Setting color: %s", color)
        self.opc_client.set_pixel_color(self.channel, self.led, color)

    def enable(self, brightness_compensation=True):
        pass


class OpenPixelClient(object):
    def __init__(self, machine, server, port):

        self.log = logging.getLogger('OpenPixelClient')

        self.machine = machine
        self.server = server
        self.port = int(port)
        self.socket = None
        self.dirty = True
        self.update_every_tick = False

        self.channels = list()

        self.machine.events.add_handler('timer_tick', self.tick, 1000000)

    def add_pixel(self, channel, led):
        """Adds a pixel to the list that will be sent to the OPC server.

        Args:
            channel: Integer of the OPC channel this pixel is on.
            led: Integer of the pixel number (i.e. its position in the list) for
                this pixel.

        This is needed since MPF will process LED device entries in random
        order, so if (for example) we get a call to setup LED #20, then we need
        we make sure we have 19 items on the list before it.

        """
        if len(self.channels) < channel + 1:

            channels_to_add = channel + 1 - len(self.channels)

            self.channels = (
                self.channels + [list() for i in range(channels_to_add)])

        if len(self.channels[channel]) < led + 1:

            leds_to_add = led + 1 - len(self.channels[channel])

            self.channels[channel] = (
                self.channels[channel] + [(0, 0, 0) for i in range(leds_to_add)])

    def set_pixel_color(self, channel, pixel, color):
        self.channels[channel][pixel] = color
        self.dirty = True

    def connect(self):
        """Connect to the OPC server.

        Returns:
            True on success. False if it was unable to connect.

        """
        if self.socket:
            return True

        try:
            self.log.debug('Trying to connect to OPC server: %s:%s',
                           self.server, self.port)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server, self.port))
            self.log.debug('Connected to the OPC server.')
            return True
        except socket.error:
            self.log.debug('Failed to connect to the OPC server.')
            self.socket = None
            return False

    def disconnect(self):
        """Disconnects from the OPC server."""
        if self.socket:
            self.socket.close()
        self.socket = None

    def tick(self):
        """Called once per machine loop to update the pixels."""
        if self.update_every_tick or self.dirty:
            for channel_index, pixel_list in enumerate(self.channels):
                self.put_pixels(pixel_list, channel_index)

            self.dirty = False

    def put_pixels(self, pixels, channel=0):
        """Send the list of pixel colors to the OPC server

        Args:
            pixels: A list of 3-item iterables (tuples or lists). Each item is
                a 0-255 value of the intensity of the red, green, and blue
                values for the pixel. The first item in the list is the first
                pixel on the channel, the second item is the second one, etc.
            channel: Which OPC channel the pixel data will be written to.

        Returns:
            True on success. False if it was unable to connect to the OPC
            server.

        Note that you must send color data for all the pixels in a channel (or
        all the pixels up until the point you want. e.g. if you have 30 LEDs on
        the channel and you just want to update LED #10, then you need to send
        pixel data for the first 10 pixels.)
        """

        is_connected = self.connect()
        if not is_connected:
            self.log.debug('Not connected to OPC server. Ignoring these '
                           'pixels.')
            return False

        # Build the OPC message
        len_hi_byte = int(len(pixels)*3 / 256)
        len_lo_byte = (len(pixels)*3) % 256
        header = chr(channel) + chr(0) + chr(len_hi_byte) + chr(len_lo_byte)
        pieces = [header]
        for r, g, b in pixels:
            r = min(255, max(0, int(r)))
            g = min(255, max(0, int(g)))
            b = min(255, max(0, int(b)))
            pieces.append(chr(r) + chr(g) + chr(b))
        self.send(''.join(pieces))

    def send(self, message):

        is_connected = self.connect()
        if not is_connected:
            self.log.debug('Not connected to OPC server. Ignoring these '
                           'pixels.')
            return False

        try:
            self.socket.send(message)
        except socket.error:
            self.log.debug('Connection lost. Could not send pixels.')
            self.socket = None
            return False

        return True


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

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
