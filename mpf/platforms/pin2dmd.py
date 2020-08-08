"""Contains code for PIN2DMD."""
import logging

import threading
from mpf.core.utility_functions import Util

from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface
from mpf.core.platform import RgbDmdPlatform

# pylint: disable-msg=ungrouped-imports
try:
    import usb.core
except ImportError as e:
    IMPORT_FAILED = e
else:
    IMPORT_FAILED = None    # type: ignore


GAMMA_TABLE = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1,
               1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
               1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
               1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
               2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3,
               3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5,
               5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7,
               7, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 10, 10,
               11, 11, 11, 11, 11, 12, 12, 12, 12, 13, 13, 13, 13, 13, 14, 14,
               14, 14, 15, 15, 15, 16, 16, 16, 16, 17, 17, 17, 18, 18, 18, 18,
               19, 19, 19, 20, 20, 20, 21, 21, 21, 22, 22, 22, 23, 23, 23, 24,
               24, 24, 25, 25, 25, 26, 26, 27, 27, 27, 28, 28, 29, 29, 29, 30,
               30, 31, 31, 31, 32, 32, 33, 33, 34, 34, 35, 35, 35, 36, 36, 37,
               37, 38, 38, 39, 39, 40, 40, 41, 41, 42, 42, 43, 43, 44, 44, 45,
               45, 46, 47, 47, 48, 48, 49, 49, 50, 50, 51, 52, 52, 53, 53, 54,
               55, 55, 56, 56, 57, 58, 58, 59, 60, 60, 61, 62, 62, 63, 63, 63]


class Pin2DmdHardwarePlatform(RgbDmdPlatform):

    """PIN2DMD RGB DMD hardware."""

    __slots__ = ["device", "config"]

    def __init__(self, machine):
        """Initialise PIN2DMD."""
        super().__init__(machine)
        self.features['tickless'] = True
        self.config = self.machine.config_validator.validate_config("pin2dmd", self.machine.config.get('pin2dmd', {}))
        self._configure_device_logging_and_debug('PIN2DMD', self.config)
        self.log.debug("Configuring PIN2DMD hardware interface.")
        self.device = Pin2DmdDevice(machine, self.debug, self.config['resolution'], self.config['panel'])

        if IMPORT_FAILED:
            raise AssertionError('Failed to load pyusb. Did you install pyusb? '
                                 'Try: "pip3 install pyusb".') from IMPORT_FAILED

    async def initialize(self):
        """Initialise platform."""
        await self.device.connect()

    def stop(self):
        """Stop platform."""
        self.device.stop()
        self.device = None

    def __repr__(self):
        """Return string representation."""
        return '<Platform.Pin2Dmd>'

    def configure_rgb_dmd(self, name: str):
        """Configure rgb dmd."""
        if name != "default":
            self.raise_config_error("Use dmd name 'default' for PIN2DMD.", 1)
        return self.device


class Pin2DmdDevice(DmdPlatformInterface):

    """A PIN2DMD device."""

    __slots__ = ["writer", "current_frame", "new_frame_event", "machine", "log", "device", "brightness",
                 "debug", "resolution", "panel"]

    def __init__(self, machine, debug, resolution, panel):
        """Initialise smart matrix device."""
        self.writer = None
        self.current_frame = None
        self.new_frame_event = None
        self.machine = machine
        self.device = None
        self.brightness = 255
        self.log = logging.getLogger('Pin2DmdDevice')
        self.debug = debug
        self.resolution = resolution
        self.panel = panel

    def _send_brightness(self, brightness):
        data = [0x00] * 2052
        data[0] = 0x81
        data[1] = 0xc3
        data[2] = 0xe7
        data[3] = 0xff
        data[4] = 0x08
        data[17] = brightness

        if self.debug:
            self.log.debug("Writing 0x01, %s", "".join(" 0x%02x" % b for b in data))

        self.device.write(0x01, data)

    def _send_frame(self, buffer):
        if self.resolution == "128x32":
            elements = 2048
        else:
            elements = 6144

        output_buffer = [0] * (elements * 6 + 4)

        output_buffer[0] = 0x81
        output_buffer[1] = 0xC3
        output_buffer[2] = 0xE9
        output_buffer[3] = 18

        for i in range(0, elements):
            idx = i * 3

            if self.panel == "rgb":
                # use these mappings for RGB panels
                pixel_r = buffer[idx]
                pixel_g = buffer[idx + 1]
                pixel_b = buffer[idx + 2]
                # lower half of display
                pixel_rl = buffer[elements * 3 + idx]
                pixel_gl = buffer[elements * 3 + idx + 1]
                pixel_bl = buffer[elements * 3 + idx + 2]
            else:
                # use these mappings for RBG panels
                pixel_r = buffer[idx]
                pixel_g = buffer[idx + 2]
                pixel_b = buffer[idx + 1]
                # lower half of display
                pixel_rl = buffer[elements * 3 + idx]
                pixel_gl = buffer[elements * 3 + idx + 2]
                pixel_bl = buffer[elements * 3 + idx + 1]

            # color correction
            pixel_r = GAMMA_TABLE[pixel_r]
            pixel_g = GAMMA_TABLE[pixel_g]
            pixel_b = GAMMA_TABLE[pixel_b]

            pixel_rl = GAMMA_TABLE[pixel_rl]
            pixel_gl = GAMMA_TABLE[pixel_gl]
            pixel_bl = GAMMA_TABLE[pixel_bl]

            target_idx = i + 4

            for _ in range(0, 6):
                output_buffer[target_idx] = ((pixel_gl & 1) << 5) | ((pixel_bl & 1) << 4) | ((pixel_rl & 1) << 3) |\
                                            ((pixel_g & 1) << 2) | ((pixel_b & 1) << 1) | ((pixel_r & 1) << 0)
                pixel_r >>= 1
                pixel_g >>= 1
                pixel_b >>= 1
                pixel_rl >>= 1
                pixel_gl >>= 1
                pixel_bl >>= 1
                target_idx += elements

        if self.debug:
            self.log.debug("Writing 0x01, %s, 1000", "".join(" 0x%02x" % b for b in output_buffer))

        self.device.write(0x01, output_buffer, 1000)

    def _feed_hardware(self):
        """Feed hardware in separate thread.

        Wait for new_frame_event and send the last frame. If no event happened for 1s refresh the last frame.
        """
        current_brightness = None
        while not self.machine.thread_stopper.is_set():
            # wait for new frame or timeout
            self.new_frame_event.wait(1)

            # clear event
            self.new_frame_event.clear()

            # set brightness if it changed
            if self.brightness != current_brightness:
                current_brightness = self.brightness
                self._send_brightness(current_brightness)

            # do not crash on missing frame
            if self.current_frame is None:
                continue

            # send frame
            self._send_frame(self.current_frame)

    async def connect(self):
        """Connect to Pin2Dmd device."""
        self.log.info("Connecting to Pin2DMD RGB DMD")
        self.device = usb.core.find(idVendor=0x0314, idProduct=0xE457)
        if self.device is None:
            raise AssertionError('Pin2Dmd USB device not found')

        self.new_frame_event = threading.Event()
        self.writer = self.machine.clock.loop.run_in_executor(None, self._feed_hardware)
        self.writer.add_done_callback(Util.raise_exceptions)

        self.log.info("Connected to Pin2DMD")

    def set_brightness(self, brightness: float):
        """Set brightness."""
        if brightness < 0.0 or brightness > 1.0:
            raise AssertionError("Brightness has to be between 0 and 1.")
        self.brightness = int(brightness * 255)

    def stop(self):
        """Stop platform."""

    def update(self, data):
        """Update DMD data."""
        self.current_frame = bytearray(data)
        self.new_frame_event.set()
