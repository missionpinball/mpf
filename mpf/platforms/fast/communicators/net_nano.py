import asyncio
from packaging import version
from serial import SerialException, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from typing import Optional
from mpf.platforms.fast import fast_defines

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.net_neuron import FastNetNeuronCommunicator
from mpf.platforms.fast.fast_io_board import FastIoBoard

class FastNetNanoCommunicator(FastNetNeuronCommunicator):

    MIN_FW = version.parse('1.05')
    IO_MIN_FW = version.parse('0.87')
    ignored_messages = ['WD:P',
                        'TN:P']

    def __init__(self, platform, processor, config):

        super().__init__(platform, processor, config)

        self.watchdog_cmd = f"WD:{config['watchdog']:02X}"
        self._watchdog_task = None

        self.message_processors['SA:'] = self._process_sa
        self.message_processors['!B:'] = self._process_boot_message
        self.message_processors['\x11\x11!'] = self._process_reboot_done
        self.message_processors['NN:'] = self._process_nn
        self.message_processors['/N:'] = self._process_switch_open
        self.message_processors['-N:'] = self._process_switch_closed
        # TODO add 'SN:', 'DN:' etc to look for DN:F, but then what do we do with it?

    async def init(self):
        await self.send_query('ID:', 'ID:')  # Verify we're connected to a Neuron
        self.send_blind('WD:1') # Force expire the watchdog since who knows what state the board is in?
        await self.query_io_boards()
        await self.send_query('SA:', 'SA:')  # Get initial states so switches can be created