"""Contains code for an FadeCandy hardware for RGB LEDs."""
import asyncio
import logging
import json
import struct

from mpf.core.utility_functions import Util
from mpf.platforms.openpixel import OpenPixelClient
from mpf.platforms.openpixel import OpenpixelHardwarePlatform

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController


class FadecandyHardwarePlatform(OpenpixelHardwarePlatform):

    """Base class for the FadeCandy hardware platform."""

    __slots__ = []

    def __init__(self, machine: "MachineController") -> None:
        """Initialise Fadecandy.

        Args:
            machine: The main ``MachineController`` object.
        """
        super().__init__(machine)

        self.log = logging.getLogger("FadeCandy")
        self.log.debug("Configuring FadeCandy hardware interface.")

    def __repr__(self):
        """Return string representation."""
        return '<Platform.FadeCandy>'

    @asyncio.coroutine
    def _setup_opc_client(self):
        self.opc_client = FadeCandyOPClient(self.machine, self.machine.config['open_pixel_control'])
        yield from self.opc_client.connect()


class FadeCandyOPClient(OpenPixelClient):

    """Base class of an OPC client which connects to a FadeCandy server.

    This class implements some FadeCandy-specific features that are not
    available with generic OPC implementations.

    """

    __slots__ = ["gamma", "whitepoint", "linear_slope", "linear_cutoff", "keyframe_interpolation", "dithering",
                 "config"]

    def __init__(self, machine, config):
        """Initialise Fadecandy client.

        Args:
            machine: The main ``MachineController`` instance.
            config: Dictionary which contains configuration settings for the
                OPC client.
        """
        super().__init__(machine, config)

        self.log = logging.getLogger('FadeCandyClient')

        self.update_every_tick = True

        self.config = self.machine.config_validator.validate_config('fadecandy',
                                                                    self.machine.config['fadecandy'])

        self.gamma = self.config['gamma']
        self.whitepoint = Util.string_to_list(self.config['whitepoint'])

        self.whitepoint[0] = float(self.whitepoint[0])
        self.whitepoint[1] = float(self.whitepoint[1])
        self.whitepoint[2] = float(self.whitepoint[2])

        self.linear_slope = self.config['linear_slope']
        self.linear_cutoff = self.config['linear_cutoff']
        self.keyframe_interpolation = self.config['keyframe_interpolation']
        self.dithering = self.config['dithering']

        if not self.keyframe_interpolation:
            self.update_every_tick = False

    @asyncio.coroutine
    def connect(self):
        """Connect to the hardware."""
        yield from super().connect()
        self.set_global_color_correction()
        self.write_firmware_options()

    def __repr__(self):
        """Return str representation."""
        return '<Platform.FadeCandyOPClient>'

    def set_global_color_correction(self):
        """Write the current global color correction settings to the FadeCandy server.

        This includes gamma, white point, linear slope, and linear cutoff.
        """
        msg = json.dumps({
            'gamma': self.gamma,
            'whitepoint': self.whitepoint,
            'linearSlope': self.linear_slope,
            'linearCutoff': self.linear_cutoff
        })

        self.send(struct.pack(
            "!BBHHH", 0x00, 0xFF, len(msg) + 4, 0x0001, 0x0001) + bytes(msg, 'UTF-8'))

    def write_firmware_options(self):
        """Write the current firmware settings (keyframe interpolation and dithering) to the FadeCandy hardware."""
        config_byte = 0x00

        if not self.dithering:
            config_byte |= 0x01

        if not self.keyframe_interpolation:
            config_byte |= 0x02

        # manual LED control
        # config_byte = config_byte | 0x04

        # turn LED on
        # config_byte = config_byte | 0x08

        self.send(struct.pack(
            "!BBHHHB", 0x00, 0xFF, 0x0005, 0x0001, 0x0002, config_byte))
