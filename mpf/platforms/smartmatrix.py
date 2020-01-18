"""Contains code for SmartMatrix RGB DMD."""

import logging

import threading
from typing import Dict
import serial

from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface

from mpf.exceptions.config_file_error import ConfigFileError

from mpf.core.platform import RgbDmdPlatform
from mpf.core.utility_functions import Util


class SmartMatrixHardwarePlatform(RgbDmdPlatform):

    """SmartMatrix RGB DMD."""

    __slots__ = ["devices"]

    def __init__(self, machine):
        """Initialise RGB DMD."""
        super().__init__(machine)
        self.features['tickless'] = True

        self.configure_logging('SmartMatrix')
        self.log.info("Configuring SmartMatrix RGB DMD hardware interface.")

        self.devices = dict()       # type: Dict[str, SmartMatrixDevice]

        if not isinstance(self.machine.config['smartmatrix'], dict):
            raise ConfigFileError("Smartmatrix config needs to be a dict.", 1, self.log.name)

        for name, config in self.machine.config['smartmatrix'].items():
            config = self.machine.config_validator.validate_config(
                config_spec='smartmatrix',
                source=config)
            self.devices[name] = SmartMatrixDevice(config, machine)

    async def initialize(self):
        """Initialise platform."""
        for device in self.devices.values():
            await device.connect()

    def stop(self):
        """Stop platform."""
        for device in self.devices.values():
            device.stop()

        self.devices = {}

    def __repr__(self):
        """Return string representation."""
        return '<Platform.SmartMatrix>'

    def configure_rgb_dmd(self, name: str):
        """Configure rgb dmd."""
        return self.devices[name]


class SmartMatrixDevice(DmdPlatformInterface):

    """A smartmatrix device."""

    __slots__ = ["config", "writer", "port", "control_data_queue", "current_frame", "new_frame_event", "machine", "log"]

    def __init__(self, config, machine):
        """Initialise smart matrix device."""
        self.config = config
        self.writer = None
        self.port = None
        self.control_data_queue = None
        self.current_frame = None
        self.new_frame_event = None
        self.machine = machine
        self.log = logging.getLogger('SmartMatrixDevice')

    def _feed_hardware(self):
        """Feed hardware in separate thread.

        Wait for new_frame_event and send the last frame. If no event happened for 1s refresh the last frame.
        """
        while not self.machine.thread_stopper.is_set():
            # wait for new frame or timeout
            self.new_frame_event.wait(1)

            # clear event
            self.new_frame_event.clear()

            # check if we need to send any control data
            while self.control_data_queue:
                self.port.write(self.control_data_queue.pop())

            # do not crash on missing frame
            if self.current_frame is None:
                continue

            # send frame
            if self.config['old_cookie']:
                self.port.write(bytearray([0x01]) + self.current_frame)
            else:
                self.port.write(bytearray([0xBA, 0x11, 0x00, 0x03, 0x04, 0x00, 0x00, 0x00]) + self.current_frame)

        # close port before exit
        self.port.close()

    async def connect(self):
        """Connect to SmartMatrix device."""
        self.log.info("Connecting to SmartMatrix RGB DMD on %s baud %s", self.config['port'], self.config['baud'])
        self.port = serial.Serial(self.config['port'], self.config['baud'])
        self.new_frame_event = threading.Event()
        self.control_data_queue = []
        self.writer = self.machine.clock.loop.run_in_executor(None, self._feed_hardware)
        self.writer.add_done_callback(Util.raise_exceptions)

    def set_brightness(self, brightness: float):
        """Set brightness."""
        if brightness < 0.0 or brightness > 1.0:
            raise AssertionError("Brightness has to be between 0 and 1.")
        if not self.config['old_cookie']:
            self.control_data_queue.insert(0, bytearray([0xBA, 0x11, 0x00, 0x03, 20, int(brightness * 255), 00, 00]))

    def stop(self):
        """Stop platform."""

    def update(self, data):
        """Update DMD data."""
        self.current_frame = bytearray(data)
        self.new_frame_event.set()
