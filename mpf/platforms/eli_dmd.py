"""Contains code for a RGB DMD."""

import logging
import sys
import threading
import traceback
from queue import Queue
import serial
from mpf.core.platform import RgbDmdPlatform


class EliDmd(RgbDmdPlatform):

    """Elis RGB DMD."""

    def __init__(self, machine):
        """Initialise RGB DMD."""
        super().__init__(machine)

        self.log = logging.getLogger('RgbDmd')
        self.log.debug("Configuring RGB DMD hardware interface.")

        self.queue = None
        self.serial_port = None
        self.dmd_thread = None
        self.update = None

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
            self.serial_port.close()
        except AttributeError:
            pass

    def __repr__(self):
        """Return string representation."""
        return '<Platform.EliDmd>'

    def configure_rgb_dmd(self):
        """Configure rgb dmd."""
        self.log.info("Connecting to RGB DMD on %s baud %s", self.config['port'], self.config['baud'])
        self.serial_port = serial.Serial(port=self.config['port'], baudrate=self.config['baud'])

        self.queue = Queue()
        self.dmd_thread = threading.Thread(target=self._dmd_sender_thread)
        self.dmd_thread.daemon = True
        self.dmd_thread.start()
        self.update = self._update_separate_thread

        return self

    def _update_separate_thread(self, data):
        self.queue.put(bytearray(data))

    def _dmd_sender_thread(self):
        while True:
            print(".")
            data = self.queue.get()  # this will block

            try:
                self.serial_port.write(bytearray([0xBA, 0x11, 0x00, 0x03, 0x04, 0x00, 0x00, 0x00]))
                self.serial_port.write(bytearray(data))

            except IOError:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                lines = traceback.format_exception(exc_type, exc_value,
                                                   exc_traceback)
                msg = ''.join(line for line in lines)
                self.machine.crash_queue.put(msg)
