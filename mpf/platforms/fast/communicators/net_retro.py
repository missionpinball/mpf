import asyncio

from packaging import version

from mpf.platforms.fast import fast_defines
from mpf.platforms.fast.communicators.base import FastSerialCommunicator
from mpf.platforms.fast.fast_io_board import FastIoBoard

MIN_FW = version.parse('2.06')

class FastNetRetroCommunicator(FastSerialCommunicator):

    ignored_messages = []

    async def init(self):
        await super().init()
        await self.query_fast_io_boards()

    async def reset_net_cpu(self):
        """Reset the NET CPU."""
        self.platform.debug_log('Resetting NET CPU.')
        self.write_to_port('BR:')
        msg = ''
        while msg != 'BR:P\r' and not msg.endswith('!B:02\r'):
            msg = (await self.readuntil(b'\r')).decode()
            self.platform.debug_log("Got: %s", msg)

    async def configure_hardware(self):
        """Verify Retro board type."""
        # For Retro boards, send the CPU configuration
        hardware_key = fast_defines.HARDWARE_KEY[self.platform.machine_type]
        self.platform.debug_log("Writing FAST hardware key %s from machine type %s",
                                hardware_key, self.platform.machine_type)
        self.write_to_port(f'CH:{hardware_key},FF')

        msg = ''
        while msg != 'CH:P\r':
            msg = (await self.readuntil(b'\r')).decode()
            if msg == '\x00CH:P\r':  # workaround as the -5 Neurons send a null byte after the final boot message
                msg = 'CH:P\r'
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

        # Wait a moment for any previous message cache to clear
        await asyncio.sleep(.2)

        # Configure the hardware for the machine type
        try:
            await asyncio.wait_for(self.configure_hardware(), 15)
        except asyncio.TimeoutError:
            self.platform.warning_log("Configuring FAST hardware timed out.")
        else:
            self.platform.debug_log("FAST hardware configuration accepted.")

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

        # TODO: [Retro] Move the config defines to the Retro's firmware and retrieve via serial query
        # In the meantime, hard-code values large enough to account for the biggest machines
        node_id, drivers, switches = ['00', '40', '80']  # in HEX, aka DEC values 0, 64, 128
        self.platform.register_io_board(FastIoBoard(
            int(node_id, 16),
            self.remote_model,
            self.remote_firmware,
            int(switches, 16),
            int(drivers, 16))
        )

        self.platform.debug_log('Fast Retro Board %s: Model: %s, Firmware: %s, Switches: %s, Drivers: %s',
                                node_id, self.remote_model, self.remote_firmware,
                                int(switches, 16), int(drivers, 16))
