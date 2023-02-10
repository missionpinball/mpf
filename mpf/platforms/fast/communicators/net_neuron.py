import asyncio
from packaging import version
from mpf.platforms.fast import fast_defines

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator
from mpf.platforms.fast.fast_io_board import FastIoBoard

MIN_FW = version.parse('2.06')
IO_MIN_FW = version.parse('1.09')

class FastNetNeuronCommunicator(FastSerialCommunicator):

    ignored_messages = ['WD:P']

    def __init__(self, platform, processor, config):

        super().__init__(platform, processor, config)

        self.message_processors['SA:'] = self._process_sa
        self.message_processors['!B:'] = self._process_boot_message
        self.message_processors['\x11\x11!'] = self._process_reboot_done
        self.message_processors['NN:'] = self._process_nn

    async def init(self):
        await self.send_query('ID:', 'ID:')  # Verify we're connected to a Neuron
        self.send_blind('WD:1') # Disable watchdog (expire in 1ms)
        await self.send_query('CH:2000,FF:', 'CH:P')  # Configure hardware for Neuron with active switch reporting
        await asyncio.sleep(.5)  # Give the I/O Loop time to start after the reboot
        await self.query_io_boards()
        await self.send_query('SA:', 'SA:')  # Get initial states so switches can be created

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
        self.log.info("Querying I/O Boards...")
        while current_node < 10:
            self.log.info("about to await results of NN:{:02X}".format(current_node))
            await self.send_query('NN:{:02X}'.format(current_node), 'NN:')
            # await asyncio.sleep(.5)
            self.log.info(f"Got NN: Results. current_node: {current_node}, io_boards: {self.platform.io_boards}")

            # Don't move on until we get board 00 in since it can take a sec after a reset
            if not len(self.platform.io_boards):
                continue
            else:
                current_node += 1

            # If our count is greater than the number of boards we have, we're done
            if current_node > len(self.platform.io_boards):
                break

    def _process_nn(self, msg):
        self.log.info("Received NN message: %s", msg)
        self.log.info("Platform IO Boards: %s", self.platform.io_boards)
        firmware_ok = True

        if msg == 'NN:F':
            return msg, False

        node_id, model, fw, dr, sw, _, _, _, _, _, _ = msg.split(',')
        node_id = node_id[3:]

        model = model.strip('\x00')

        # Iterate as many boards as possible
        if not model or model == '!Node Not Found!':
            self.log.info(f"No more I/O boards found. Platform IO Boards: {self.platform.io_boards}")
            return msg, False

        if Util.hex_string_to_int(node_id) in self.platform.io_boards:
            return msg, False

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

        return msg, False

    def _process_sa(self, msg):
        self.platform.process_received_message(msg, "NET")
        return msg, False
