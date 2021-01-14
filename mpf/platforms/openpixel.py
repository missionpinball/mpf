"""Contains code for an Open Pixel Controller hardware for RGB LEDs.

The python code to build the OPC message packet came from here:
https://github.com/zestyping/openpixelcontrol/blob/master/python_clients/opc.py
"""
from typing import Optional

import logging

from mpf.core.platform import LightsPlatform
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class OpenpixelHardwarePlatform(LightsPlatform):

    """Base class for the open pixel hardware platform.

    Args:
    ----
        machine: The main ``MachineController`` object.

    """

    __slots__ = ["opc_client"]

    def __init__(self, machine: "MachineController") -> None:
        """Instantiate openpixel hardware platform."""
        super().__init__(machine)

        self.log = logging.getLogger("OpenPixel")
        self.log.debug("Configuring Open Pixel hardware interface.")
        self.opc_client = None      # type: Optional[OpenPixelClient]
        self.features['tickless'] = True

    def __repr__(self):
        """Return str representation."""
        return '<Platform.OpenPixel>'

    async def initialize(self):
        """Initialise openpixel platform."""
        self.machine.config_validator.validate_config("open_pixel_control", self.machine.config['open_pixel_control'])
        if self.machine.config['open_pixel_control']['debug']:
            self.debug = True

        await self._setup_opc_client()

    def stop(self):
        """Stop platform."""
        # disconnect sender
        if self.opc_client:
            self.opc_client.blank_all()
            if self.opc_client.socket_sender:
                self.opc_client.socket_sender.close()
                self.opc_client.socket_sender = None
            self.opc_client = None

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

    def configure_light(self, number, subtype, config, platform_settings) -> LightPlatformInterface:
        """Configure an LED."""
        del config
        return OpenPixelLED(number, self.opc_client, self.debug)

    async def _setup_opc_client(self):
        self.opc_client = OpenPixelClient(self.machine, self.machine.config['open_pixel_control'])
        await self.opc_client.connect()


class OpenPixelLED(LightPlatformInterface):

    """One LED on the openpixel platform."""

    __slots__ = ["log", "opc_client", "debug", "opc_channel", "channel_number"]

    def __init__(self, number, opc_client, debug):
        """Initialise Openpixel LED obeject."""
        super().__init__(number)
        self.log = logging.getLogger('OpenPixelLED')
        channel, channel_number = number.split("-")

        self.opc_client = opc_client
        self.debug = debug
        self.opc_channel = int(channel)
        self.channel_number = int(channel_number)
        self.opc_client.add_pixel(self.opc_channel, self.channel_number)

    def set_fade(self, start_brightness, start_time, target_brightness, target_time):
        """Set brightness using callback."""
        self.opc_client.set_pixel_color(self.opc_channel, self.channel_number, start_brightness, start_time,
                                        target_brightness, target_time)

    def get_board_name(self):
        """Return name for service mode."""
        return "OPC Channel {}".format(self.channel_number)

    def __repr__(self):
        """Return string representation."""
        return "<OpenPixelLED channel={} number={}>".format(self.opc_channel, self.channel_number)

    def is_successor_of(self, other):
        """Return true if the other light has the previous index and is on the same channel."""
        return self.opc_channel == other.opc_channel and self.channel_number == other.channel_number + 1

    def get_successor_number(self):
        """Return next index on node."""
        return "{}-{}".format(self.opc_channel, self.channel_number + 1)

    def __lt__(self, other):
        """Order lights by their order on the hardware."""
        return (self.opc_channel, self.channel_number) < (other.opc_channel, other.channel_number)


class OpenPixelClient:

    """Base class of an OPC client which connects to a FadeCandy server.

    Args:
    ----
        machine: The main ``MachineController`` instance.
        config: Config to use
    """

    __slots__ = ["machine", "log", "update_every_tick", "socket_sender", "max_fade_ms", "channels", "dirty_leds",
                 "msg", "openpixel_config"]

    def __init__(self, machine, config):
        """Initialise openpixel client."""
        self.log = logging.getLogger('OpenPixelClient')

        self.machine = machine
        self.update_every_tick = False
        self.socket_sender = None
        self.max_fade_ms = None
        self.channels = []
        self.dirty_leds = []
        self.msg = []
        self.openpixel_config = config

    async def connect(self):
        """Connect to the hardware."""
        connector = self.machine.clock.open_connection(self.openpixel_config['host'], self.openpixel_config['port'])
        try:
            _, self.socket_sender = await connector
        except OSError:
            raise AssertionError("Cannot connect to {} at {}:{}".format(self.log.name, self.openpixel_config['host'],
                                                                        self.openpixel_config['port']))

        self.max_fade_ms = int(1 / self.machine.config['mpf']['default_light_hw_update_hz'] * 1000)

        self.machine.events.add_handler("init_phase_3", self._start_loop)

    def _start_loop(self, **kwargs):
        del kwargs
        # blank all channels
        self.blank_all()

        # Update at a regular interval
        self.machine.clock.schedule_interval(self.tick, 1 / self.machine.config['mpf']['default_light_hw_update_hz'])

    def add_pixel(self, channel, led):
        """Add a pixel to the list that will be sent to the OPC server.

        Args:
        ----
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
            self.dirty_leds += [dict() for _ in range(channels_to_add)]
            self.msg += [None for _ in range(channels_to_add)]

        new_total = led + 1
        if new_total % 3 != 0:
            new_total += 3 - (new_total % 3)
        leds_to_add = new_total - len(self.channels[channel])
        if leds_to_add > 0:
            self.channels[channel] += [0 for _ in range(leds_to_add)]

    # pylint: disable-msg=too-many-arguments
    def set_pixel_color(self, channel, pixel, start_brightness, start_time, target_brightness, target_time):
        """Set an individual pixel color.

        Args:
        ----
            channel: Int of the OPC channel for this pixel.
            pixel: Int of the number for this pixel on that channel.
            start_brightness: Brightness at start of fade.
            start_time: Timestamp when the fade started.
            target_brightness: Brightness at end of fade.
            target_time: Timestamp when the fade should finish.
        """
        self.dirty_leds[channel][pixel] = (start_brightness, start_time, target_brightness, target_time)

    def tick(self):
        """Update pixels.

        Called periodically.
        """
        for channel_index in range(len(self.channels)):
            if not self.update_every_tick and not self.dirty_leds[channel_index]:
                continue
            self._handle_dirty_leds(channel_index)
            self._update_pixels(channel_index)

    def _handle_dirty_leds(self, channel):
        if not self.dirty_leds[channel]:
            return

        # invalidate cached message
        self.msg[channel] = None

        current_time = self.machine.clock.get_time()
        max_fade_ms = self.max_fade_ms
        for pixel, (start_brightness, start_time, target_brightness, target_time) \
                in dict(self.dirty_leds[channel]).items():
            fade_ms = int((target_time - current_time) * 1000.0)
            if fade_ms > max_fade_ms > 0:
                ratio = ((current_time + (max_fade_ms / 1000.0) - start_time) /
                         (target_time - start_time))
                brightness = start_brightness + (target_brightness - start_brightness) * ratio
            else:
                # fade is done
                brightness = target_brightness
                del self.dirty_leds[channel][pixel]
            value = min(255, max(0, int(brightness * 255)))
            self.channels[channel][pixel] = value

    def _update_pixels(self, channel):
        """Send the list of pixel colors to the OPC server.

        Args:
        ----
            channel: Which OPC channel the pixel data will be written to.

        Returns True on success. False if it was unable to connect to the OPC
        server.

        Note that you must send color data for all the pixels in a channel (or
        all the pixels up until the point you want. e.g. if you have 30 LEDs on
        the channel and you just want to update LED #10, then you need to send
        pixel data for the first 10 pixels.)
        """
        # if we got a cached message just send it
        if not self.msg[channel]:
            self.msg[channel] = bytes(self._build_message(channel))

        self.send(self.msg[channel])

    def _build_message(self, channel):
        """Build the OPC message."""
        msg = bytearray()
        pixels = self.channels[channel]
        len_hi_byte = int(len(pixels) / 256)
        len_lo_byte = (len(pixels)) % 256
        header = bytes([channel, 0, len_hi_byte, len_lo_byte])
        msg.extend(header)
        for i in range(int(len(pixels) / 3)):
            # send GRB because that is the default color order for WS2812

            msg.append(pixels[i * 3 + 1])
            msg.append(pixels[i * 3])
            msg.append(pixels[i * 3 + 2])
        return msg

    def blank_all(self):
        """Blank all channels."""
        for channel_index in range(len(self.channels)):
            self.channels[channel_index] = [0] * len(self.channels[channel_index])
            self.send(bytes(self._build_message(channel_index)))

    def send(self, message):
        """Send a message to the socket.

        Args:
        ----
            message: Message to send
        """
        if not self.socket_sender:
            return
        self.socket_sender.write(message)
