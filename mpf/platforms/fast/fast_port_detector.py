import asyncio

from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE, SerialException
from serial.tools import list_ports

from mpf.platforms.fast.fast_defines import USB_IDS


class FastPortDetector:

    def __init__(self, platform, autodetect_processors, hardcoded_ports):

        self.platform = platform
        self.machine = platform.machine
        self.autodetect_processors = autodetect_processors
        self.hardcoded_ports = hardcoded_ports
        self.detected_fast_ports = list()  # tuples of (port, baud)
        self.tasks = list()
        self.task_writers = dict()
        self.results = dict()  # dict of processor: port

        self.platform.log.info(f"Auto-detecting ports for the following connections: {self.autodetect_processors}")

        self._find_fast_devices()

    def _find_fast_devices(self):
        # Creates a list of all serial ports which have devices attached which match
        # USB VID/PID combinations of FAST devices we're looking for.
        for port in list_ports.comports():
            if (port.vid, port.pid) in USB_IDS:
                proc, desc = USB_IDS[(port.vid, port.pid)]
                if proc in self.autodetect_processors:
                    baud = self.machine.config['fast'][proc]['baud']
                    if port.device not in self.hardcoded_ports:
                        self.detected_fast_ports.append((port.device, baud))
                        self.platform.log.debug(f"Port {port.device} is connected to a {desc}.")
                    else:
                        self.platform.log.debug(f"Skipping auto-detect of {proc} on {port.device} since it's in the config file elsewhere.")

    async def detect_ports(self):
        self.tasks = [asyncio.create_task(self._connect_task(port, baud)) for port, baud in self.detected_fast_ports]
        for task, (_, _) in zip(self.tasks, self.detected_fast_ports):
            task.add_done_callback(self._cleanup_writer)
        # need to catch the task cancellation exception here or else the MPF startup process will think something broke
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await asyncio.sleep(0.1)

    async def _connect_task(self, port, baud):
        """One instance per port is launched to connect and ID whatever's on the other end.

        Sends an ID: command once per second until it gets a response or until other tasks have
        found all the ports and the remaining ones are cancelled.

        If an ID: response comes back that matches a processor we're looking for,
        it reports success and end.

        """
        while True:
            try:
                connector = self.machine.clock.open_serial_connection(
                    url=port, baudrate=baud, limit=0, xonxoff=False,
                    bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE)
                reader, writer = await connector
            except SerialException:
                self.log.error(f"Could not connect to port {port}. Are you connected via CoolTerm? :)")

            self.task_writers[asyncio.current_task()] = writer

            while True:
                writer.write(b'ID:\r')

                # Wait for a response with 1-second timeout
                try:
                    data = await asyncio.wait_for(reader.read(100), timeout=1.0)
                except asyncio.TimeoutError:
                    continue  # retry

                if data:
                    data = data.decode('utf-8', errors='ignore')

                    for processor in self.autodetect_processors:
                        if processor.upper() in data:
                            self._report_success(processor, port)
                            writer.close()
                            return

    def _report_success(self, processor, port):
        self.results[processor] = port
        self.platform.log.info(f'Detected {processor.upper()} on port {port}')
        self.platform.config[processor]['port'] = [port]

        if len(self.results) >= len(self.autodetect_processors):
            self._cancel_remaining_tasks()

    def _cancel_remaining_tasks(self):
        for task in self.tasks:
            if not task.done():
                task.cancel()

    def _cleanup_writer(self, task):
        writer = self.task_writers.pop(task, None)
        if writer:
            writer.close()