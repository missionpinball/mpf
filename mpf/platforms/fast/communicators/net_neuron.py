import asyncio
from packaging import version
from mpf.platforms.fast import fast_defines

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator
from mpf.platforms.fast.fast_io_board import FastIoBoard

MIN_FW = version.parse('2.06')
IO_MIN_FW = version.parse('1.09')

class FastNetNeuronCommunicator(FastSerialCommunicator):

    ignored_messages = ['WD:P',
                        'TL:P']

    def __init__(self, platform, processor, config):

        super().__init__(platform, processor, config)

        self.watchdog_cmd = f"WD:{config['watchdog']:02X}"
        self._watchdog_task = None

        self.message_processors['SA:'] = self._process_sa
        self.message_processors['!B:'] = self._process_boot_message
        self.message_processors['\x11\x11!'] = self._process_reboot_done
        self.message_processors['NN:'] = self._process_nn
        self.message_processors['/L:'] = self._process_switch_open
        self.message_processors['-L:'] = self._process_switch_closed
        # TODO add 'SL:', 'DL:' etc to look for DL:F, but then what do we do with it?

    async def init(self):
        await self.send_query('ID:', 'ID:')  # Verify we're connected to a Neuron
        await self.send_query('CH:2000,FF', 'CH:P')  # Configure hardware for Neuron with active switch reporting
        self.send_blind('WD:1') # Force expire the watchdog since who knows what state the board is in?
        await self.query_io_boards()
        # await asyncio.sleep(1)  # was experimenting to see if this affects the results of the SA: next
        await self.send_query('SA:', 'SA:')  # Get initial states so switches can be created

    async def soft_reset(self, **kwargs):
        """Reset the NET processor."""
        del kwargs

        # TODO
        # get a list of the current hw driver numbers from machine drivers
        # FAST controllers can hold configs for 104 switches and 48 drivers, so loop through
        # those, comparing their last known states to the current states and only send
        # if they are different

    async def clear_board_serial_buffer(self):
        """Clear out the serial buffer."""
        while True:
            # send enough dummy commands to clear out any buffers on the FAST
            # board that might be waiting for more commands
            self.write_to_port(b' ' * 1024)  # TODO only on Nano, others have timeouts?
            self.write_to_port(b'\r')
            msg = await self._read_with_timeout(.5)

            if msg.startswith('XX:'):
                break

            await asyncio.sleep(.5)

    def _process_boot_message(self, msg):
        """Reset the NET CPU."""

        self.log.info("Resetting NET Processor...")
        # TODO Do something?

    def _process_reboot_done(self, msg):
        self.log.info("Processor reset complete.")
        # TODO Mark all configs as dirty

    async def query_io_boards(self):
        """Query the NET processor to see if any FAST I/O boards are connected.

        If so, queries the I/O boards to log them and make sure they're the  proper firmware version.
        """

        current_node = 0
        while current_node < 10:
            await self.send_query('NN:{:02X}'.format(current_node), 'NN:')

            # Don't move on until we get board 00 in since it can take a sec after a reset
            if not len(self.platform.io_boards):
                if 'switches' not in self.machine.config and 'coils' not in self.machine.config:
                    # No switches or coils, so we don't need I/O boards. This is nice when people are first getting started
                    break
                continue
            else:
                current_node += 1

            # If our count is greater than the number of boards we have, we're done
            if current_node > len(self.platform.io_boards):
                break

    def _process_nn(self, msg):
        firmware_ok = True

        if msg == 'F':  # NN:F
            return

        node_id, model, fw, dr, sw, _, _, _, _, _, _ = msg.split(',')
        # node_id = node_id[3:]

        model = model.strip('\x00')

        if not model or model == '!Node Not Found!':
            return

        if Util.hex_string_to_int(node_id) in self.platform.io_boards:
            return

        self.platform.register_io_board(FastIoBoard(int(node_id, 16), model, fw, int(sw, 16), int(dr, 16)))

        self.log.info('Registered I/O Board %s: Model: %s, Firmware: %s, Switches: %s, Drivers: %s',
                                node_id, model, fw, int(sw, 16), int(dr, 16))

        min_fw = IO_MIN_FW
        if min_fw > version.parse(fw):
            self.platform.log.critical("Firmware version mismatch. MPF requires the I/O boards "
                                        "to be firmware %s, but your Board %s (%s) is firmware %s",
                                        min_fw, node_id, model, fw)
            firmware_ok = False

        if not firmware_ok:
            raise AssertionError("Exiting due to I/O board firmware mismatch")

    def _process_sa(self, msg):
        hw_states = {}
        _, local_states = msg.split(',')

        for offset, byte in enumerate(bytearray.fromhex(local_states)):
            for i in range(8):

                num = Util.int_to_hex_string((offset * 8) + i)

                if byte & (2**i):
                    hw_states[(num, 0)] = 1
                else:
                    hw_states[(num, 0)] = 0

        self.platform.hw_switch_data = hw_states

    def _process_switch_open(self, msg):
        """Process local switch open.

        Args:
        ----
            msg: switch number
            remote_processor: Processor which sent the message.
        """
        self.machine.switch_controller.process_switch_by_num(state=0,
                                                             num=(msg, 0),
                                                             platform=self.platform)

    def _process_switch_closed(self, msg):
        """Process local switch closed.

        Args:
        ----
            msg: switch number
            remote_processor: Processor which sent the message.
        """
        self.machine.switch_controller.process_switch_by_num(state=1,
                                                             num=(msg, 0),
                                                             platform=self.platform)

    def _update_watchdog(self):
        """Send Watchdog command."""

        self.send_blind(self.watchdog_cmd)

    def start(self):
        """Start listening for commands and schedule watchdog."""
        self._update_watchdog()
        self._watchdog_task = self.machine.clock.schedule_interval(self._update_watchdog,
                                                                   self.config['watchdog'] / 2000)

    def stopping(self):
        if self._watchdog_task:
            self._watchdog_task.cancel()
            self._watchdog_task = None
        self.send_blind('WD:1')
