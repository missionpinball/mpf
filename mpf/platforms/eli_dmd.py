"""Contains code for a RGB DMD."""

import logging
import sys
import threading
import traceback
from queue import Queue

import asyncio
import serial
from mpf.core.platform import RgbDmdPlatform


class EliDmd(RgbDmdPlatform):

    """Elis RGB DMD."""

    def __init__(self, machine):
        """Initialise RGB DMD."""
        super().__init__(machine)
        self.features['tickless'] = True

        self.log = logging.getLogger('RgbDmd')
        self.log.debug("Configuring RGB DMD hardware interface.")

        self.reader = None
        self.writer = None

        self.config = self.machine.config_validator.validate_config(
            config_spec='eli_dmd',
            source=self.machine.config['eli_dmd'])

    def initialize(self):
        """Initialise platform."""
        pass

    def stop(self):
        """Stop platform."""
        try:
            self.log.info("Disconnecting from RGB DMD hardware...")
            self.writer.close()
        except AttributeError:
            pass

    def __repr__(self):
        """Return string representation."""
        return '<Platform.EliDmd>'

    def configure_rgb_dmd(self):
        """Configure rgb dmd."""
        self.machine.clock.loop.run_until_complete(self._connect())
        return self

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        future.result()

    @asyncio.coroutine
    def _connect(self):
        self.log.info("Connecting to RGB DMD on %s baud %s", self.config['port'], self.config['baud'])
        connector = self.machine.clock.open_serial_connection(
            url=self.config['port'], baudrate=self.config['baud'], limit=0)
        self.reader, self.writer = yield from connector

    def update(self, data):
        if self.writer:
            self.writer.write(bytearray([0xBA, 0x11, 0x00, 0x03, 0x04, 0x00, 0x00, 0x00]))
            self.writer.write(bytearray(data))
