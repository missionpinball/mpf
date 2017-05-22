"""Contains code for SmartMatrix RGB DMD."""

import logging

import asyncio
from mpf.core.platform import RgbDmdPlatform


class SmartMatrix(RgbDmdPlatform):

    """SmartMatrix RGB DMD."""

    def __init__(self, machine):
        """Initialise RGB DMD."""
        super().__init__(machine)
        self.features['tickless'] = True

        self.log = logging.getLogger('SmartMatrix')
        self.log.debug("Configuring SmartMatrix RGB DMD hardware interface.")

        self.reader = None
        self.writer = None

        self.config = self.machine.config_validator.validate_config(
            config_spec='smartmatrix',
            source=self.machine.config['smartmatrix'])

        self.machine.clock.loop.run_until_complete(self._connect())

    def initialize(self):
        """Initialise platform."""
        pass

    def stop(self):
        """Stop platform."""
        try:
            self.log.info("Disconnecting from SmartMatrix RGB DMD hardware...")
            self.writer.close()
        except AttributeError:
            pass

    def __repr__(self):
        """Return string representation."""
        return '<Platform.SmartMatrix>'

    def configure_rgb_dmd(self):
        """Configure rgb dmd."""
        return self

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        future.result()

    @asyncio.coroutine
    def _connect(self):
        self.log.info("Connecting to SmartMatrix RGB DMD on %s baud %s", self.config['port'], self.config['baud'])
        connector = self.machine.clock.open_serial_connection(
            url=self.config['port'], baudrate=self.config['baud'], limit=0)
        self.reader, self.writer = yield from connector

    def update(self, data):
        """Update DMD data."""
        if self.writer:
            if self.config['old_cookie']:
                self.writer.write(bytearray([0x01]))
            else:
                self.writer.write(bytearray([0xBA, 0x11, 0x00, 0x03, 0x04, 0x00, 0x00, 0x00]))
            self.writer.write(bytearray(data))
