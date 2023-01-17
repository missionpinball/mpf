import asyncio
from packaging import version
from serial import SerialException, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from typing import Optional
from mpf.platforms.fast import fast_defines

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

class FastNetCommunicator(FastSerialCommunicator):



    MIN_FW = version.parse('2.06')


    ignored_messages = ['RX:P',  # RGB Pass
                        'SN:P',  # Network Switch pass
                        'SL:P',  # Local Switch pass
                        'LX:P',  # Lamp pass
                        'PX:P',  # Segment pass
                        'DN:P',  # Network driver pass
                        'DL:P',  # Local driver pass
                        'XX:F',  # Unrecognized command?
                        'R1:F',
                        'L1:P',
                        'GI:P',
                        'TL:P',
                        'TN:P',
                        'XO:P',  # Servo/Daughterboard Pass
                        'XX:U',
                        'XX:N'
                        ]


    async def init(self):

        await super().init()

        self.is_nano = False  # temp todo
        self.is_retro = False  # temp todo

        await self.query_fast_io_boards()



        return self




    async def reset_net_cpu(self):
        """Reset the NET CPU."""
        self.platform.debug_log('Resetting NET CPU.')
        self.writer.write('BR:\r'.encode())
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
        self.writer.write(f'CH:{hardware_key},FF\r'.encode())

        msg = ''
        while msg != 'CH:P\r':
            msg = (await self.readuntil(b'\r')).decode()
            if msg == '\x00CH:P\r':  # workaround as the -5 Neurons send a null byte after the final boot message
                msg = 'CH:P\r'
            self.platform.debug_log("Got: %s", msg)

    async def query_fast_io_boards(self):
        """Query the NET processor to see if any FAST IO boards are connected.

        If so, queries the IO boards to log them and make sure they're the  proper firmware version.
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

        if not self.is_nano:
            await asyncio.sleep(.2)
            try:
                await asyncio.wait_for(self.configure_hardware(), 15)
            except asyncio.TimeoutError:
                self.platform.warning_log("Configuring FAST hardware timed out.")
            else:
                self.platform.debug_log("FAST hardware configuration accepted.")

        await asyncio.sleep(.5)

        self.platform.debug_log('Reading all switches.')
        self.writer.write('SA:\r'.encode())
        msg = ''
        while not msg.startswith('SA:'):
            msg = (await self.readuntil(b'\r')).decode()
            if not msg.startswith('SA:'):
                self.platform.log.warning("Got unexpected message from FAST while awaiting SA: %s", msg)

        self.platform.process_received_message(msg, "NET")
        self.platform.debug_log('Querying FAST I/O boards (legacy %s, retro %s)...', self.is_nano, self.is_retro)

        firmware_ok = True

        if self.is_retro:
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

            return

        for board_id in range(128):
            self.writer.write('NN:{:02X}\r'.format(board_id).encode())
            msg = ''
            while not msg.startswith('NN:'):
                msg = (await self.readuntil(b'\r')).decode()
                if not msg.startswith('NN:'):
                    self.platform.debug_log("Got unexpected message from FAST while querying IO Boards: %s", msg)

            if msg == 'NN:F\r':
                break

            node_id, model, fw, dr, sw, _, _, _, _, _, _ = msg.split(',')
            node_id = node_id[3:]

            model = model.strip('\x00')

            # Iterate as many boards as possible
            if not model or model == '!Node Not Found!':
                break

            self.platform.register_io_board(FastIoBoard(int(node_id, 16), model, fw, int(sw, 16), int(dr, 16)))

            self.platform.debug_log('Fast IO Board %s: Model: %s, Firmware: %s, Switches: %s, Drivers: %s',
                                    node_id, model, fw, int(sw, 16), int(dr, 16))

            min_fw = IO_LEGACY_MIN_FW if self.is_nano else IO_MIN_FW
            if min_fw > version.parse(fw):
                self.platform.log.critical("Firmware version mismatch. MPF requires the IO boards "
                                           "to be firmware %s, but your Board %s (%s) is firmware %s",
                                           min_fw, node_id, model, fw)
                firmware_ok = False

        if not firmware_ok:
            raise AssertionError("Exiting due to IO board firmware mismatch")
