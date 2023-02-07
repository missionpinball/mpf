import asyncio
from packaging import version
from serial import SerialException, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from typing import Optional
from mpf.platforms.fast import fast_defines

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator
from mpf.platforms.fast.fast_io_board import FastIoBoard

MIN_FW = version.parse('2.06')
IO_MIN_FW = version.parse('0.87')

class FastNetNanoCommunicator(FastSerialCommunicator):

    ignored_messages = []

    async def init(self):
        await super().init()
        await self.query_fast_io_boards()

    async def reset_net_cpu(self):
        """Reset the NET CPU."""
        self.platform.debug_log('Resetting NET CPU.')
        self.send_blind('BR:')
        msg = ''
        while msg != 'BR:P\r' and not msg.endswith('!B:02\r'):
            msg = (await self.readuntil(b'\r')).decode()
            self.platform.debug_log("Got: %s", msg)

    async def query_fast_io_boards(self):
        """Query the NET processor to see if any FAST I/O boards are connected.

        If so, queries the I/O boards to log them and make sure they're the  proper firmware version.
        """
        # reset CPU early
        try:
            # Wait a moment for any previous message cache to clear
            await asyncio.sleep(.2)
            await asyncio.wait_for(self.reset_net_cpu(), 10)
        except asyncio.TimeoutError:
            self.platform.warning_log("Reset of NET CPU failed.")
        else:
            self.platform.debug_log("Reset successful")

        await asyncio.sleep(.5)

        self.platform.debug_log('Reading all switches.')
        self.write_to_port('SA:')
        msg = ''
        while not msg.startswith('SA:'):
            msg = (await self.readuntil(b'\r')).decode()
            if not msg.startswith('SA:'):
                self.platform.log.warning("Got unexpected message from FAST while awaiting SA: %s", msg)

        self.platform.process_received_message(msg, "NET")
        self.platform.debug_log('Querying FAST I/O boards')

        firmware_ok = True

        for board_id in range(128):
            self.write_to_port('NN:{:02X}'.format(board_id))
            msg = ''
            while not msg.startswith('NN:'):
                msg = (await self.readuntil(b'\r')).decode()
                if not msg.startswith('NN:'):
                    self.platform.debug_log("Got unexpected message from FAST while querying I/O Boards: %s", msg)

            if msg == 'NN:F\r':
                break

            node_id, model, fw, dr, sw, _, _, _, _, _, _ = msg.split(',')
            node_id = node_id[3:]

            model = model.strip('\x00')

            # Iterate as many boards as possible
            if not model or model == '!Node Not Found!':
                break

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
