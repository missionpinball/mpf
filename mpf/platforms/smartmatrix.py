"""Contains code for an SmartMatrix Shield connected to a Teensy"""

import logging
import sys
import threading
import traceback
from queue import Queue
import serial
from mpf.core.platform import RgbDmdPlatform


class HardwarePlatform(RgbDmdPlatform):

    def __init__(self, machine):

        super().__init__(machine)

        self.log = logging.getLogger('SmartMatrix')
        self.log.info("Configuring SmartMatrix hardware interface.")

        self.dmd_frame = bytearray()
        self.queue = None
        self.serial_port = None
        self.dmd_thread = None

        self.config = self.machine.config_validator.validate_config(
            config_spec='smartmatrix',
            source=self.machine.config['smartmatrix'])

    def initialize(self):
        pass

    def stop(self):
        self.serial_port.close()

    def __repr__(self):
        return '<Platform.SmartMatrix>'

    def configure_rgb_dmd(self):
        self.log.debug("Configuring SmartMatrix DMD")
        self.serial_port = serial.Serial(port=self.config['port'],
                                         baudrate=2500000)

        if self.config['use_separate_thread']:
            self.queue = Queue()
            self.dmd_thread = threading.Thread(target=self.dmd_sender_thread)
            self.dmd_thread.daemon = True
            self.dmd_thread.start()
            self.machine.bcp.register_rgb_dmd(self.update_separate_thread)
        else:
            self.machine.bcp.register_rgb_dmd(self.update_non_thread)

    def update_non_thread(self, data):
        try:
            self.serial_port.write(bytearray([0x01]))
            self.serial_port.write(bytearray(data))
        except TypeError:
            pass

    def update_separate_thread(self, data):
        self.queue.put(bytearray(data))

    def dmd_sender_thread(self):
        while True:
            data = self.queue.get()  # this will block

            try:
                self.serial_port.write(bytearray([0x01]))
                self.serial_port.write(bytearray(data))

            except IOError:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                lines = traceback.format_exception(exc_type, exc_value,
                                                   exc_traceback)
                msg = ''.join(line for line in lines)
                self.machine.crash_queue.put(msg)
