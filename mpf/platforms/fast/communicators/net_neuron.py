import asyncio
from packaging import version
from mpf.platforms.fast import fast_defines

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator
from mpf.platforms.fast.fast_io_board import FastIoBoard

MIN_FW = version.parse('2.06')
IO_MIN_FW = version.parse('1.09')

class FastNetNeuronCommunicator(FastSerialCommunicator):

    ignored_messages = ['DL:P',
                        'TL:P',
                        'SL:P']

    def __init__(self, platform, processor, config):

        super().__init__(platform, processor, config)

        self.message_processors['SA'] = self._process_sa
        self.message_processors['!B'] = self._process_boot_message
        self.message_processors['NN'] = self._process_nn

    async def init(self):
        await self.send_query('ID:')  # Verify we're connected to a Neuron
        await self.send_query('BR:', '!B:00')  # Reset the Neuron
        self.send_and_confirm('CH:2000,FF:', 'CH:P')  # Configure hardware for Neuron with active switch reporting
        await self.query_io_boards()
        await self.send_query('SA:')  # Update switch states from hw

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

        self.current_message_processor = self._process_boot_message

        if msg == '!B:00':
            self.log.info("Processor will reboot.")
            return msg, True

        if msg[-5:] == '!B:02':
            self.log.info("Processor boot complete.")
            return msg, False


    async def query_io_boards(self):
        """Query the NET processor to see if any FAST I/O boards are connected.

        If so, queries the I/O boards to log them and make sure they're the  proper firmware version.
        """

        for board_id in range(128):
            found = await self.send_query('NN:{:02X}'.format(board_id))

            if not found:
                break

    def _process_nn(self, msg):

        firmware_ok = True

        if msg == 'NN:F\r':
            return

        node_id, model, fw, dr, sw, _, _, _, _, _, _ = msg.split(',')
        node_id = node_id[3:]

        model = model.strip('\x00')

        # Iterate as many boards as possible
        if not model or model == '!Node Not Found!':
            return False

        self.platform.register_io_board(FastIoBoard(int(node_id, 16), model, fw, int(sw, 16), int(dr, 16)))

        self.platform.debug_log('Fast I/O Board %s: Model: %s, Firmware: %s, Switches: %s, Drivers: %s',
                                node_id, model, fw, int(sw, 16), int(dr, 16))

        min_fw = IO_MIN_FW
        if min_fw > version.parse(fw):
            self.platform.log.critical("Firmware version mismatch. MPF requires the I/O boards "
                                        "to be firmware %s, but your Board %s (%s) is firmware %s",
                                        min_fw, node_id, model, fw)
            firmware_ok = False

        if not firmware_ok:
            raise AssertionError("Exiting due to I/O board firmware mismatch")

        return True

    def _process_sa(self, msg):
        self.platform.process_received_message(msg, "NET")
