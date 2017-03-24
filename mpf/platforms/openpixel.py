"""Contains code for an Open Pixel Controller hardware for RGB LEDs.

The python code to build the OPC message packet came from here:
https://github.com/zestyping/openpixelcontrol/blob/master/python_clients/opc.py
"""

import logging

from typing import Callable
from typing import Tuple

from mpf.core.platform import LightsPlatform
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class HardwarePlatform(LightsPlatform):

    """Base class for the open pixel hardware platform.

    Args:
        machine: The main ``MachineController`` object.

    """

    def __init__(self, machine):
        """Instantiate openpixel hardware platform."""
        super(HardwarePlatform, self).__init__(machine)

        self.log = logging.getLogger("OpenPixel")
        self.debug_log("Configuring Open Pixel hardware interface.")
        self.opc_client = None
        self.features['tickless'] = True

    def __repr__(self):
        """Return str representation."""
        return '<Platform.OpenPixel>'

    def initialize(self):
        """Initialise openpixel platform."""
        self.machine.config_validator.validate_config("open_pixel_control", self.machine.config['open_pixel_control'])
        if self.machine.config['open_pixel_control']['debug']:
            self.debug = True

    def stop(self):
        """Stop platform."""
        # disconnect sender
        self.opc_client.socket_sender.close()

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse number to three channels."""
        del subtype
        if isinstance(number, str) and '-' in number:
            opc_channel, led_number = number.split('-')
        else:
            led_number = number
            opc_channel = "0"

        channel_number = int(led_number) * 3

        return [
            {
                "number": opc_channel + "-" + str(channel_number)
            },
            {
                "number": opc_channel + "-" + str(channel_number + 1)
            },
            {
                "number": opc_channel + "-" + str(channel_number + 2)
            }
        ]

    def configure_light(self, number, subtype, platform_settings) -> LightPlatformInterface:
        """Configure an LED."""
        if not self.opc_client:
            self._setup_opc_client()

        opc_channel, channel_number = number.split("-")

        return OpenPixelLED(self.opc_client, opc_channel, channel_number, self.debug)

    def _setup_opc_client(self):
        self.opc_client = OpenPixelClient(self.machine, self.machine.config['open_pixel_control'])


class OpenPixelLED(LightPlatformInterface):

    """One LED on the openpixel platform."""

    def __init__(self, opc_client, channel, channel_number, debug):
        """Initialise Openpixel LED obeject."""
        self.log = logging.getLogger('OpenPixelLED')

        self.opc_client = opc_client
        self.debug = debug
        self.opc_channel = int(channel)
        self.channel_number = int(channel_number)
        self.opc_client.add_pixel(self.opc_channel, self.channel_number)

    def set_fade(self, color_and_fade_callback: Callable[[int], Tuple[float, int]]):
        """Set brightness using callback."""
        self.opc_client.set_pixel_color(self.opc_channel, self.channel_number, color_and_fade_callback)


class OpenPixelClient(object):

    """Base class of an OPC client which connects to a FadeCandy server.

    Args:
        machine: The main ``MachineController`` instance.
        config: Config to use
    """

    def __init__(self, machine, config):
        """Initialise openpixel client."""
        self.log = logging.getLogger('OpenPixelClient')

        self.machine = machine
        self.dirty = True
        self.update_every_tick = False
        self.socket_sender = None
        self.channels = list()

        connector = self.machine.clock.open_connection(config['host'], config['port'])
        _, self.socket_sender = self.machine.clock.loop.run_until_complete(connector)

        # Update the FadeCandy at a regular interval
        self.machine.clock.schedule_interval(self.tick, 1 / self.machine.config['mpf']['default_light_hw_update_hz'])

    def add_pixel(self, channel, led):
        """Add a pixel to the list that will be sent to the OPC server.

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

            self.channels += [list() for _ in range(channels_to_add)]

        if len(self.channels[channel]) < led + 1:

            leds_to_add = led + 1 - len(self.channels[channel])

            self.channels[channel] += [0 for _ in range(leds_to_add)]

    def set_pixel_color(self, channel, pixel, callback: Callable[[int], Tuple[float, int]]):
        """Set an invidual pixel color.

        Args:
            channel: Int of the OPC channel for this pixel.
            pixel: Int of the number for this pixel on that channel.
            callback: callback to get brightness
        """
        self.channels[channel][pixel] = callback
        self.dirty = True

    def tick(self):
        """Called once per machine loop to update the pixels."""
        if self.update_every_tick or self.dirty:
            for channel_index, pixel_list in enumerate(self.channels):
                self.update_pixels(pixel_list, channel_index)

            self.dirty = False

    @staticmethod
    def _add_pixel(msg, max_fade_ms, brightness):
        if callable(brightness):
            brightness = brightness(max_fade_ms)[0] * 255
        brightness = min(255, max(0, int(brightness)))
        msg.append(brightness)

    def update_pixels(self, pixels, channel=0):
        """Send the list of pixel colors to the OPC server.

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
        msg = bytearray()
        max_fade_ms = int(1 / self.machine.config['mpf']['default_light_hw_update_hz'])
        len_hi_byte = int(len(pixels) / 256)
        len_lo_byte = (len(pixels)) % 256
        header = bytes([channel, 0, len_hi_byte, len_lo_byte])
        msg.extend(header)
        for i in range(int(len(pixels) / 3)):
            # send GRB because that is the default color order for WS2812

            self._add_pixel(msg, max_fade_ms, pixels[i * 3 + 1])
            self._add_pixel(msg, max_fade_ms, pixels[i * 3])
            self._add_pixel(msg, max_fade_ms, pixels[i * 3 + 2])

        self.send(bytes(msg))

    def send(self, message):
        """Send a message to the socket.

        Args:
            message: Message to send
        """
        self.socket_sender.write(message)
