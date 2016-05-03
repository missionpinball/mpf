"""Contains code for an Open Pixel Controller hardware for RGB LEDs.

The python code to build the OPC message packet came from here:
https://github.com/zestyping/openpixelcontrol/blob/master/python_clients/opc.py
"""

import logging
import socket
from queue import Queue
import threading
import sys
import traceback

from mpf.core.platform import LedPlatform
from mpf.platforms.interfaces.rgb_led_platform_interface import RGBLEDPlatformInterface


class HardwarePlatform(LedPlatform):
    """Base class for the open pixel hardware platform.

    Args:
        machine: The main ``MachineController`` object.

    """

    def __init__(self, machine):

        super(HardwarePlatform, self).__init__(machine)

        self.log = logging.getLogger("OpenPixel")
        self.log.debug("Configuring Open Pixel hardware interface.")
        self.opc_client = None

    def __repr__(self):
        return '<Platform.OpenPixel>'

    def configure_led(self, config):

        if not self.opc_client:
            self._setup_opc_client()

        if isinstance(config['number'], str) and '-' in config['number']:
            channel, led = config['number'].split('-')
        else:
            led = config['number']
            channel = 0

        if self.machine.config['open_pixel_control']['number_format'] == 'hex':
            led = int(str(led), 16)

        # self.opc_client.add_pixel(channel, led)

        return OpenPixelLED(self.opc_client, channel, led)

    def _setup_opc_client(self):
        self.opc_client = OpenPixelClient(self.machine, self.machine.config['open_pixel_control'])


class OpenPixelLED(RGBLEDPlatformInterface):

    def __init__(self, opc_client, channel, led):
        self.log = logging.getLogger('OpenPixelLED')

        self.opc_client = opc_client
        self.channel = int(channel)
        self.led = int(led)
        self.opc_client.add_pixel(self.channel, self.led)

    def color(self, color):
        self.log.debug("Setting color: %s", color)
        self.opc_client.set_pixel_color(self.channel, self.led, color.rgb)


class OpenPixelClient(object):
    """Base class of an OPC client which connects to a FadeCandy server.

    Args:
        machine: The main ``MachineController`` instance.
        config: Config to use
    """
    def __init__(self, machine, config):

        self.log = logging.getLogger('OpenPixelClient')

        self.machine = machine
        self.dirty = True
        self.update_every_tick = False
        self.sending_queue = Queue()
        self.sending_thread = None
        self.channels = list()

        # Update the FadeCandy at a regular interval
        # TODO: Add update interval to config
        self.machine.clock.schedule_interval(self.tick, 1/30.0)

        self.sending_thread = OPCThread(self.machine, self.sending_queue,
                                        config)
        self.sending_thread.daemon = True
        self.sending_thread.start()

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

            self.channels += [list() for i in range(channels_to_add)]

        if len(self.channels[channel]) < led + 1:

            leds_to_add = led + 1 - len(self.channels[channel])

            self.channels[channel] += [(0, 0, 0) for i in range(leds_to_add)]

    def set_pixel_color(self, channel, pixel, color):
        """Sets an invidual pixel color.

        Args:
            channel: Int of the OPC channel for this pixel.
            pixel: Int of the number for this pixel on that channel.
            color: 3-item list or tuple of (red, green, blue) color values, each
                an integer between 0-255.
        """
        self.channels[channel][pixel] = color
        self.dirty = True

    def tick(self, dt):
        """Called once per machine loop to update the pixels."""
        del dt
        if self.update_every_tick or self.dirty:
            for channel_index, pixel_list in enumerate(self.channels):
                self.update_pixels(pixel_list, channel_index)

            self.dirty = False

    def update_pixels(self, pixels, channel=0):
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
        self.send(bytes(''.join(pieces), 'UTF-8'))

    def send(self, message):
        """Puts a message on the queue to be sent to the OPC server.

        Args:
            message: The raw message you want to send. No processing is done on
                this. It's sent however it comes in.
        """
        self.sending_queue.put(message)


class OPCThread(threading.Thread):  # pragma: no cover
    """Base class for the thread that connects to the OPC server.

    Args:
        machine: The main ``MachineController`` instance.
        sending_queue: The Queue() object that receives OPC messages for the OPC server.
        config: Dictionary of configuration settings.

    The OPC connection is handled in a separate thread so it doesn't bog down
    the main MPF machine loop if there are connection problems.
    """

    def __init__(self, machine, sending_queue, config):
        threading.Thread.__init__(self)
        self.sending_queue = sending_queue
        self.machine = machine
        self.host = config['host']
        self.port = config['port']
        self.connection_required = config['connection_required']
        self.max_connection_attempts = config['connection_attempts']

        self.log = logging.getLogger("OpenPixelThread")

        self.socket = None
        self.connection_attempts = 0
        self.try_connecting = True

        self.connect()

    def connect(self):
        """Connects to the OPC server.

        Returns:
            True on success. False if it was unable to connect.

        This method also tracks and respects ``connection_attempts`` and
        ``max_connection_attempts``.

        """
        if self.socket:
            return True

        self.connection_attempts += 1

        if 0 < self.max_connection_attempts < self.connection_attempts:

            self.log.debug("Max connection attempts reached")
            self.try_connecting = False

            if self.connection_required:
                self.log.debug("Configuration is set that OPC connection is "
                               "required. MPF exiting.")
                self.done()

        try:
            self.log.debug('Trying to connect to OPC server: %s:%s. Attempt '
                           'number %s', self.host, self.port,
                           self.connection_attempts)
            self.socket = socket.socket()
            self.socket.connect((self.host, self.port))
            self.log.debug('Connected to the OPC server.')
            self.connection_attempts = 0

        except socket.error:
            self.log.warning('Failed to connect to the OPC server: %s:%s',
                             self.host, self.port)
            self.socket = None
            return False

    def disconnect(self):
        """Disconnects from the OPC server."""
        if self.socket:
            self.socket.close()
        self.socket = None

    def run(self):
        """Thread run loop."""
        try:
            while True:
                while self.socket:
                    message = self.sending_queue.get()

                    try:
                        self.socket.send(message)
                    except (IOError, AttributeError):
                        self.log.warning('Connection to OPC server lost.')
                        self.socket = None

                while not self.socket and self.try_connecting:
                    self.connect()
                    # don't want to build up stale pixel data while we're not
                    # connected
                    self.sending_queue.queue.clear()
                    self.log.warning('Discarding stale pixel data from the queue.')

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            msg = ''.join(line for line in lines)
            self.machine.crash_queue.put(msg)

    def done(self):
        """Exits the thread and causes MPF to shut down."""
        self.disconnect()
        self.machine.done = True
