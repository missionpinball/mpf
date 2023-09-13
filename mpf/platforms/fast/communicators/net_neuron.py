# mpf/platforms/fast/communicators/net_neuron.py

import asyncio
from packaging import version

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator
from mpf.platforms.fast.fast_io_board import FastIoBoard
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.platforms.fast.fast_driver import FastDriverConfig
from mpf.platforms.fast.fast_switch import FASTSwitch
from mpf.platforms.fast.fast_driver import FASTDriver


class FastNetNeuronCommunicator(FastSerialCommunicator):

    MIN_FW = version.parse('2.06')
    IO_MIN_FW = version.parse('1.09')
    MAX_IO_BOARDS = 9
    MAX_SWITCHES = 104
    MAX_DRIVERS = 48
    ignored_messages = ['WD:P',
                        'TL:P']

    def __init__(self, platform, processor, config):

        super().__init__(platform, processor, config)

        self.watchdog_cmd = f"WD:{config['watchdog']:02X}"
        self._watchdog_task = None

        self.io_loop = [None] * len(self.config['io_loop'])

        self.switches = list()
        self.drivers = list()

        self.trigger_cmd = 'TL'
        self.driver_cmd = 'DL'
        self.switch_cmd = 'SL'

        self.message_processors['SA:'] = self._process_sa
        self.message_processors['CH:'] = self.process_pass_message
        self.message_processors['!B:'] = self._process_boot_message
        self.message_processors['\x11\x11!'] = self._process_reboot_done
        self.message_processors['NN:'] = self._process_nn
        self.message_processors['DL:'] = self.process_driver_config_msg
        self.message_processors['SL:'] = self.process_switch_config_msg
        self.message_processors['/L:'] = self._process_switch_open
        self.message_processors['-L:'] = self._process_switch_closed
        # TODO add 'SL:', 'DL:' etc to look for DL:F, but then what do we do with it?

        for board, config in self.config['io_loop'].items():
            config['index'] = int(config['order'])-1

            try:
                self.io_loop[config['index']] = board
            except IndexError:
                raise ConfigFileError(f"Invalid order value for I/O board '{board}'. "
                                      "Order values must be sequential starting at 1.", 7, self.log.name)  # TODO

    async def init(self):
        await self.send_and_wait_async('ID:', 'ID:')  # Verify we're connected to a Neuron
        await self.send_and_wait_async('CH:2000,FF', 'CH:')  # Configure hardware for Neuron with active switch reporting
        self.send_and_forget('WD:1') # Force expire the watchdog since who knows what state the board is in?
        await self.query_io_boards()
        # await self.send_and_wait_async('SA:', 'SA:')  # Get initial states so switches can be created

        self.create_switches()
        self.create_drivers()

    def create_switches(self):
        # Neuron tracks all switches regardless of how many are connected
        for i in range(self.MAX_SWITCHES):
            self.switches.append(FASTSwitch(self, i))

    def create_drivers(self):
        # Neuron tracks all drivers regardless of how many are connected
        for i in range(self.MAX_DRIVERS):
            self.drivers.append(FASTDriver(self, i))

    async def soft_reset(self, **kwargs):
        """Reset the NET processor."""
        del kwargs

        await self.reset_switches()
        await self.reset_drivers()
        await self.platform.get_hw_switch_states()

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

        If so, queries the I/O boards to log them and make sure they're the proper firmware version.
        """

        if 'switches' not in self.machine.config and 'coils' not in self.machine.config:
            self.log.debug("No coils or switches configured. Skipping I/O board discovery.")
            return

        current_node = 0
        while current_node < len(self.config['io_loop']):
            await self.send_and_wait_async('NN:{:02X}'.format(current_node), 'NN:')

            # Don't move on until we get board 00 in since it can take a sec after a reset
            if current_node + 1 >= len(self.platform.io_boards):
                current_node += 1

            # If our count is greater than the number of boards we have, we're done
            # if current_node > len(self.platform.io_boards):
            #     break

    async def reset_switches(self):
        """Query the NET processor to get a list of switches and their configurations.
        Compare that to how they should be configured, and send new configuration
        commands for any that are different.
        """

        for switch in self.switches:  # all physical switches, not just ones defined in the config
            await self.send_and_wait_async(f'{self.switch_cmd}:{switch.hw_number}', f'{self.switch_cmd}:{switch.hw_number}')

    async def reset_drivers(self):
        """Query the NET processor to get a list of drivers and their configurations.
        Compare that to how they should be configured, and send new configuration
        commands for any that are different.

        """

        # self.drivers contains a list of all drivers, not just ones defined in the config

        for driver in self.drivers:
            await self.send_and_wait_async(f'DL:{Util.int_to_hex_string(driver.number)}', self.driver_cmd)
            # TODO temp command does not function

    def _process_nn(self, msg):
        firmware_ok = True

        if msg == 'F':  # NN:F
            return

        node_id, model, fw, dr, sw, _, _, _, _, _, _ = msg.split(',')

        node_id = Util.hex_string_to_int(node_id)
        dr = Util.hex_string_to_int(dr)
        sw = Util.hex_string_to_int(sw)
        model = model.strip('\x00')
        model = ('-').join(model.split('-')[:3])  # Remove the revision dash if it's there

        if not model or model == '!Node Not Found!':
            return

        if node_id in self.platform.io_boards:
            return

        name = self.io_loop[node_id]
        model_string_from_config = ('-').join(self.config['io_loop'][name]['model'].split('-')[:3]).upper()  # Fp-I/O-3208-2 -> FP-I/O-3208

        assert model == model_string_from_config, f'I/O board config error. Board {node_id} is reporting as model {model}, but the config file says it\'s model {model_string_from_config}'

        prior_sw = 0
        prior_drv = 0

        for i in range(node_id):
            prior_sw += self.platform.io_boards[i].switch_count
            prior_drv += self.platform.io_boards[i].driver_count

        self.platform.register_io_board(FastIoBoard(self, name, node_id, model, fw, sw, dr, prior_sw, prior_drv))

        self.log.info('Registered I/O Board %s: Model: %s, Firmware: %s, Switches: %s, Drivers: %s',
                                node_id, model, fw, sw, dr)

        min_fw = self.IO_MIN_FW  # TODO move to IO board class
        if min_fw > version.parse(fw):
            self.platform.log.critical("Firmware version mismatch. MPF requires the I/O boards "
                                        "to be firmware %s, but your Board %s (%s) is firmware %s",
                                        min_fw, node_id, model, fw)
            firmware_ok = False

        if not firmware_ok:
            raise AssertionError("Exiting due to I/O board firmware mismatch")

        self.no_response_waiting.set()

    def process_driver_config_msg(self, msg):
        if msg == 'P':
            return

        try:
            int(msg, 16)  # received an DL:L switch count response
            return
        except ValueError:
            pass

        # From here down we're processing driver config data, 9 fields, one byte each
        # <driver_id>,<trigger>,<switch_id>,<mode>,<param_1>,<param_2>,<param_3>,<param_4>,<param_5>
        # https://fastpinball.com/fast-serial-protocol/net/dl/

        current_hw_driver_config = FastDriverConfig(*msg.split(','))

        try:
            driver_obj = self.drivers[int(current_hw_driver_config.number, 16)]
        except IndexError:
            return  # we always get data for 48 drivers, no worries if we don't have that many

        if driver_obj.current_driver_config != current_hw_driver_config:
            driver_obj.send_config_to_driver()

    def process_switch_config_msg(self, msg):
        """Incoming SL:<switch_id>,<mode>,<debounce_close>,<debounce_open> message."""

        if msg == 'P':  # SL:P
            return

        try:
            int(msg, 16)  # received an SL:L switch count response
            return
        except ValueError:
            pass

        # From here down we're processing switch config data
        # '00,02,01,02' = switch number, mode, debounce close, debounce open
        # https://fastpinball.com/fast-serial-protocol/net/sl/

        switch, mode, debounce_close, debounce_open = msg.split(',')

        try:
            switch_obj = self.switches[int(switch, 16)]
        except IndexError:  # Neuron tracks 104 switches regardless of how many are connected
            return

        if (switch_obj.current_hw_config.mode != mode or
            switch_obj.current_hw_config.debounce_close != debounce_close or
            switch_obj.current_hw_config.debounce_open != debounce_open
            ):
            # TODO this seems tedious, should we switch the dataclass to a namedtuple?

            switch_obj.send_config_to_switch()

    def _process_sa(self, msg):
        hw_states = {}
        _, local_states = msg.split(',')

        for offset, byte in enumerate(bytearray.fromhex(local_states)):
            for i in range(8):

                num = (offset * 8) + i

                if byte & (2**i):
                    hw_states[num] = 1
                else:
                    hw_states[num] = 0

        self.platform.hw_switch_data = hw_states

    def _process_switch_open(self, msg):
        """Process local switch open.

        Args:
        ----
            msg: switch number
            remote_processor: Processor which sent the message.
        """
        self.machine.switch_controller.process_switch_by_num(state=0,
                                                             num=int(msg, 16),
                                                             platform=self.platform)

    def _process_switch_closed(self, msg):
        """Process local switch closed.

        Args:
        ----
            msg: switch number
            remote_processor: Processor which sent the message.
        """
        self.machine.switch_controller.process_switch_by_num(state=1,
                                                             num=int(msg, 16),
                                                             platform=self.platform)

    def _update_watchdog(self):
        """Send Watchdog command."""

        self.send_and_forget(self.watchdog_cmd)

    def start_tasks(self):
        """Start listening for commands and schedule watchdog."""
        self._update_watchdog()
        self._watchdog_task = self.machine.clock.schedule_interval(self._update_watchdog,
                                                                   self.config['watchdog'] / 2000)

    def stopping(self):
        if self._watchdog_task:
            self._watchdog_task.cancel()
            self._watchdog_task = None
        self.send_and_forget('WD:1')
