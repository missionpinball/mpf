"""Contains code for SmartMatrix RGB DMD."""

import logging

import asyncio
from typing import Dict

from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface

from mpf.exceptions.ConfigFileError import ConfigFileError

from mpf.core.platform import RgbDmdPlatform


class SmartMatrixHardwarePlatform(RgbDmdPlatform):

    """SmartMatrix RGB DMD."""

    def __init__(self, machine):
        """Initialise RGB DMD."""
        super().__init__(machine)
        self.features['tickless'] = True

        self.log = logging.getLogger('SmartMatrix')
        self.log.debug("Configuring SmartMatrix RGB DMD hardware interface.")

        self.devices = dict()       # type: Dict[str, SmartMatrixDevice]

        if not isinstance(self.machine.config['smartmatrix'], dict):
            raise ConfigFileError("Smartmatrix config needs to be a dict.")

        for name, config in self.machine.config['smartmatrix'].items():
            config = self.machine.config_validator.validate_config(
                config_spec='smartmatrix',
                source=config)
            self.devices[name] = SmartMatrixDevice(config, machine)

    @asyncio.coroutine
    def initialize(self):
        """Initialise platform."""
        for device in self.devices.values():
            yield from device.connect()

    def stop(self):
        """Stop platform."""
        for device in self.devices.values():
            device.stop()

    def __repr__(self):
        """Return string representation."""
        return '<Platform.SmartMatrix>'

    def configure_rgb_dmd(self, name: str):
        """Configure rgb dmd."""
        return self.devices[name]

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        future.result()


class SmartMatrixDevice(DmdPlatformInterface):

    """A smartmatrix device."""

    def __init__(self, config, machine):
        """Initialise smart matrix device."""
        self.config = config
        self.reader = None
        self.writer = None
        self.machine = machine
        self.log = logging.getLogger('SmartMatrixDevice')

    @asyncio.coroutine
    def connect(self):
        """Connect to SmartMatrix device."""
        self.log.info("Connecting to SmartMatrix RGB DMD on %s baud %s", self.config['port'], self.config['baud'])
        connector = self.machine.clock.open_serial_connection(
            url=self.config['port'], baudrate=self.config['baud'], limit=0)
        self.reader, self.writer = yield from connector

    def stop(self):
        """Stop device."""
        if self.writer:
            self.log.info("Disconnecting from SmartMatrix RGB DMD hardware.")
            self.writer.close()
            self.writer = None

    def update(self, data):
        """Update DMD data."""
        if self.writer:
            if self.config['old_cookie']:
                self.writer.write(bytearray([0x01]))
            else:
                self.writer.write(bytearray([0xBA, 0x11, 0x00, 0x03, 0x04, 0x00, 0x00, 0x00]))
            self.writer.write(bytearray(data))
