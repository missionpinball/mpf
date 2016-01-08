"""Contains code for an SmartMatrix Shield connected to a Teensy"""

import logging
import serial
import sys
import threading
import traceback
from queue import Queue
from mpf.system.config import Config
from mpf.system.platform import Platform


class HardwarePlatform(Platform):

    def __init__(self, machine):

        super(HardwarePlatform, self).__init__(machine)

        self.log = logging.getLogger('SmartMatrix')
        self.log.info("Configuring SmartMatrix hardware interface.")

        self.dmd_frame = bytearray()
        self.queue = None

        config_spec = '''
                      port: string
                      use_separate_thread: boolean|True
                      '''

        self.config = Config.process_config(config_spec=config_spec,
            source=self.machine.config['smartmatrix'])

    def __repr__(self):
        return '<Platform.SmartMatrix>'

    def configure_dmd(self):
        self.log.debug("Configuring SmartMatrix DMD")
        self.serial_port = serial.Serial(port=self.config['port'],
                                         baudrate=2500000)

        if self.config['use_separate_thread']:
            self.update = self.update_separate_thread

            self.queue = Queue()

            self.dmd_thread = threading.Thread(target=self.dmd_sender_thread)
            self.dmd_thread.daemon = True
            self.dmd_thread.start()
        else:
            self.update = self.update_non_thread
            self.machine.events.add_handler('timer_tick', self.tick,
                                            priority=0)  # p0 so this runs last

        return self

    def update_non_thread(self, data):
        try:
            self.dmd_frame = bytearray(data)
        except TypeError:
            pass

    def update_separate_thread(self, data):
        self.queue.put(bytearray(data))

    def tick(self):
        self.serial_port.write(bytearray([0x01]))
        self.serial_port.write(self.dmd_frame)

    def dmd_sender_thread(self):

        while True:
            data = self.queue.get()  # this will block

            try:
                self.serial_port.write(bytearray([0x01]))
                self.serial_port.write(data)

            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                msg = ''.join(line for line in lines)
                self.machine.crash_queue.put(msg)
