"""FAST hardware platform.

Contains the hardware interface and drivers for the FAST Pinball platform
hardware, including the FAST Neuron, Nano, and Retro controllers as well
as FAST I/O boards.
"""
import asyncio
import os
from copy import deepcopy
from packaging import version
from typing import Dict, Set, Optional
from serial import SerialException

from mpf.exceptions.runtime_error import MpfRuntimeError
from mpf.platforms.fast.fast_io_board import FastIoBoard
from mpf.platforms.fast.fast_servo import FastServo
from mpf.platforms.fast import fast_defines
from mpf.platforms.fast.fast_dmd import FASTDMD
from mpf.platforms.fast.fast_driver import FASTDriver
from mpf.platforms.fast.fast_gi import FASTGIString
from mpf.platforms.fast.fast_led import FASTDirectLED, FASTDirectLEDChannel
from mpf.platforms.fast.fast_light import FASTMatrixLight
from mpf.platforms.fast.fast_segment_display import FASTSegmentDisplay
from mpf.platforms.fast.fast_serial_communicator import FastSerialCommunicator
from mpf.platforms.fast.fast_switch import FASTSwitch
from mpf.platforms.autodetect import autodetect_fast_ports
from mpf.core.platform import ServoPlatform, DmdPlatform, LightsPlatform, SegmentDisplayPlatform, \
    DriverPlatform, DriverSettings, SwitchPlatform, SwitchSettings, DriverConfig, SwitchConfig, \
    RepulseSettings
from mpf.core.utility_functions import Util

from mpf.platforms.system11 import System11OverlayPlatform, System11Driver

# pylint: disable-msg=too-many-instance-attributes
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class FastHardwarePlatform(ServoPlatform, LightsPlatform, DmdPlatform,
                           SegmentDisplayPlatform,
                           System11OverlayPlatform):

    """Platform class for the FAST hardware controller."""

    __slots__ = ["dmd_connection", "net_connection", "rgb_connection", "seg_connection", "is_retro",
                 "serial_connections", "fast_leds", "fast_commands", "config", "machine_type", "hw_switch_data",
                 "io_boards", "flag_led_tick_registered", "_watchdog_task", "_led_task", "_seg_task",
                 "fast_segs"]

    def __init__(self, machine):
        """Initialise fast hardware platform.

        Args:
        ----
            machine: The main ``MachineController`` instance.
        """
        super().__init__(machine)

        self.config = self.machine.config_validator.validate_config("fast", self.machine.config['fast'])
        self._configure_device_logging_and_debug("FAST", self.config)

        if self.config["driverboards"]:
            self.machine_type = self.config["driverboards"]
        elif self.machine.config['hardware']['driverboards']:
            self.machine_type = self.machine.config['hardware']['driverboards'].lower()
        else:
            self.raise_config_error("Please configure driverboards for fast.", 5)

        if self.machine_type in ['sys11', 'wpc89', 'wpc95']:
            self.debug_log("Configuring the FAST Controller for Retro driver board")
            self.is_retro = True
        elif self.machine_type == 'fast':
            self.debug_log("Configuring FAST Controller for FAST IO boards.")
            self.is_retro = False
        else:
            self.raise_config_error(f'Unknown machine_type "{self.machine_type}" configured fast.', 6)

        # Most FAST platforms don't use ticks, but System11 does
        self.features['tickless'] = self.machine_type != 'sys11'

        self.dmd_connection = None
        self.net_connection = None
        self.rgb_connection = None
        self.seg_connection = None
        self._watchdog_task = None
        self._led_task = None
        self.serial_connections = set()         # type: Set[FastSerialCommunicator]
        self.fast_leds = {}
        self.fast_segs = list()
        self.flag_led_tick_registered = False
        self._seg_task = None
        self.hw_switch_data = None
        self.io_boards = {}     # type: Dict[int, FastIoBoard]

        self.fast_commands = {'ID': lambda x, y: None,  # processor ID
                              'WX': lambda x, y: None,  # watchdog
                              'NI': lambda x, y: None,  # node ID
                              'RX': lambda x, y: None,  # RGB cmd received
                              'RA': lambda x, y: None,  # RGB all cmd received
                              'RS': lambda x, y: None,  # RGB single cmd received
                              'RF': lambda x, y: None,  # RGB fade cmd received
                              'DX': lambda x, y: None,  # DMD cmd received
                              'SX': lambda x, y: None,  # sw config received
                              'LX': lambda x, y: None,  # lamp cmd received
                              'PX': lambda x, y: None,  # segment cmd received
                              'WD': lambda x, y: None,  # watchdog
                              'SA': self.receive_sa,  # all switch states
                              '/N': self.receive_nw_open,    # nw switch open
                              '-N': self.receive_nw_closed,  # nw switch closed
                              '/L': self.receive_local_open,    # local sw open
                              '-L': self.receive_local_closed,  # local sw cls
                              '!B': self.receive_bootloader,    # nano bootloader message
                              }

    def get_info_string(self):
        """Dump infos about boards."""
        infos = ""
        if not self.net_connection:
            infos += "No connection to the NET CPU.\n"
        else:
            infos += "NET CPU: {} {} {}\n".format(
                self.net_connection.remote_processor,
                self.net_connection.remote_model,
                self.net_connection.remote_firmware)
        if not self.rgb_connection:
            infos += "No connection to the RGB CPU.\n"
        else:
            infos += "RGB CPU: {} {} {}\n".format(
                self.rgb_connection.remote_processor,
                self.rgb_connection.remote_model,
                self.rgb_connection.remote_firmware)
        if not self.dmd_connection:
            infos += "No connection to the DMD CPU.\n"
        else:
            infos += "DMD CPU: {} {} {}\n".format(
                self.dmd_connection.remote_processor,
                self.dmd_connection.remote_model,
                self.dmd_connection.remote_firmware)
        if not self.seg_connection:
            infos += "No connection to the Segment Controller.\n"
        else:
            infos += "Segment Controller: {} {} {}\n".format(
                self.seg_connection.remote_processor,
                self.seg_connection.remote_model,
                self.seg_connection.remote_firmware)

        infos += "\nBoards:\n"
        for board in self.io_boards.values():
            infos += board.get_description_string() + "\n"
        return infos

    def _update_net(self) -> str:
        """Update NET CPU."""
        infos = ""
        if not self.net_connection:
            infos += "No NET CPU connected. Cannot update.\n"
            return infos
        infos += "NET CPU is version {}\n".format(self.net_connection.remote_firmware)
        max_firmware = self.net_connection.remote_firmware
        update_config = None
        for update in self.config['firmware_updates']:
            if version.parse(update['version']) > version.parse(max_firmware) and update['type'] == "net":
                update_config = update

        if not update_config:
            infos += "Firmware is up to date. Will not update.\n"
            return infos
        infos += "Found an update to version {} for the NET CPU. Will flash file {}\n".format(
            update_config['version'], update_config['file'])
        firmware_file = os.path.join(self.machine.machine_path, update_config['file'])
        try:
            with open(firmware_file) as f:
                update_string = f.read().replace("\n", "\r")
        except FileNotFoundError:
            infos += "Could not find update file.\b"
            return infos
        self.net_connection.writer.write(update_string.encode())
        infos += "Update done.\n"
        return infos

    def update_firmware(self) -> str:
        """Upgrade the firmware of the CPUs."""
        return self._update_net()

    async def initialize(self):
        """Initialise platform."""
        await self._connect_to_hardware()

    def stop(self):
        """Stop platform and close connections."""
        if self._led_task:
            self._led_task.cancel()
            self._led_task = None
        if self._seg_task:
            self._seg_task.cancel()
            self._seg_task = None
        if self._watchdog_task:
            self._watchdog_task.cancel()
            self._watchdog_task = None
        if self.net_connection:
            # set watchdog to expire in 1ms
            self.net_connection.writer.write(b'WD:1\r')
        if self.rgb_connection:
            self.rgb_connection.writer.write(b'BL:AA55\r')  # reset CPU using bootloader
        if self.dmd_connection:
            self.dmd_connection.writer.write(b'BL:AA55\r')  # reset CPU using bootloader

        # wait 100ms for the messages to be send
        self.machine.clock.loop.run_until_complete(asyncio.sleep(.1))

        if self.net_connection:
            self.net_connection.stop()
            self.net_connection = None

        if self.rgb_connection:
            self.rgb_connection.stop()
            self.rgb_connection = None

        if self.dmd_connection:
            self.dmd_connection.stop()
            self.dmd_connection = None

        if self.seg_connection:
            self.seg_connection.stop()
            self.seg_connection = None

        self.serial_connections = set()

    async def start(self):
        """Start listening for commands and schedule watchdog."""
        self._watchdog_task = self.machine.clock.schedule_interval(self._update_watchdog,
                                                                   self.config['watchdog'] / 2000)

        for connection in self.serial_connections:
            await connection.start_read_loop()

    def __repr__(self):
        """Return str representation."""
        return '<Platform.FAST>'

    def register_io_board(self, board):
        """Register an IO board.

        Args:
        ----
            board: 'mpf.platform.fast.fast_io_board.FastIoBoard' to register
        """
        if board.node_id in self.io_boards:
            raise AssertionError("Duplicate node_id")
        self.io_boards[board.node_id] = board

    def _update_watchdog(self):
        """Send Watchdog command."""
        try:
            self.net_connection.send('WD:' + str(hex(self.config['watchdog']))[2:])
        except:
            pass

    def process_received_message(self, msg: str, remote_processor: str):
        """Send an incoming message from the FAST controller to the proper method for servicing.

        Args:
        ----
            msg: messaged which was received
            remote_processor: Processor which sent the message.
        """
        assert self.log is not None
        if msg == "!SRE":
            # ignore system interrupt
            self.log.info("Received system interrupt from %s.", remote_processor)
            return

        if msg[2:3] == ':':
            cmd = msg[0:2]
            payload = msg[3:].replace('\r', '')
        else:   # pragma: no cover
            self.log.warning("Received malformed message: %s from %s", msg, remote_processor)
            return

        # Can't use try since it swallows too many errors for now #TODO
        if cmd in self.fast_commands:
            self.fast_commands[cmd](payload, remote_processor)
        else:   # pragma: no cover
            self.log.warning("Received unknown serial command? %s from %s.", msg, remote_processor)

    async def _connect_to_hardware(self):
        """Connect to each port from the config.

        This process will cause the connection threads to figure out which processor they've connected to
        and to register themselves.
        """
        ports = None
        if self.config['ports'][0] == "autodetect":
            auto_ports = autodetect_fast_ports(self.is_retro)
            if self.is_retro:
                # Retro only returns one port
                ports = auto_ports
            else:
                # Net returns four ports, the second is the CPU
                ports = [auto_ports[1]]
                if 'dmd' in self.config['ports']:
                    ports.insert(0, auto_ports[0])
                if 'rgb' in self.config['ports']:
                    ports.append(auto_ports[2])
                if 'exp' in self.config['ports']:
                    ports.append(auto_ports[3])
        else:
            ports = self.config['ports']

        bauds = self.config['baud']
        if len(bauds) == 1:
            bauds = [bauds[0]] * len(ports)
        elif len(bauds) != len(ports):
            raise AssertionError("FAST configuration found {} ports and {} baud rates".format(len(ports), len(bauds)))

        for index, port in enumerate(ports):
            comm = FastSerialCommunicator(platform=self, port=port, baud=bauds[index])
            try:
                await comm.connect()
            except SerialException as e:
                raise MpfRuntimeError("Could not open serial port {}. Check if you configured the correct port in the "
                                      "fast config section and if you got sufficient permissions to that "
                                      "port".format(port), 1, self.log.name) from e
            self.serial_connections.add(comm)

    def register_processor_connection(self, name: str, communicator):
        """Register processor.

        Once a communication link has been established with one of the
        processors on the FAST board, this method lets the communicator let MPF
        know which processor it's talking to.

        This is a separate method since we don't know which processor is on
        which serial port ahead of time.

        Args:
        ----
            communicator: communicator object
            name: name of processor
        """
        if name == 'DMD':
            self.dmd_connection = communicator
        elif name == 'NET':
            self.net_connection = communicator
        elif name == 'SEG':
            self.seg_connection = communicator

            if not self._seg_task:
                # Need to wait until the segs are all set up
                self.machine.events.add_handler('machine_reset_phase_3', self._start_seg_updates)
                
        elif name == 'RGB':
            self.rgb_connection = communicator
            self.rgb_connection.send('RF:0')
            self.rgb_connection.send('RA:000000')  # turn off all LEDs
            self.rgb_connection.send('RF:{}'.format(
                Util.int_to_hex_string(self.config['hardware_led_fade_time'])))

    def _start_seg_updates(self, **kwargs):        

        for s in self.machine.device_manager.collections["segment_displays"]:
            self.fast_segs.append(s.hw_display)
        
        self.fast_segs.sort(key=lambda x: x.number)

        if self.fast_segs:
            self._seg_task = self.machine.clock.schedule_interval(self._update_segs,
                                                1 / self.machine.config['fast'][
                                                    'segment_display_update_hz'])
    
    def _update_segs(self, **kwargs):
        
        for s in self.fast_segs:

            if s.next_text:
                self.seg_connection.send(f'PA:{s.hex_id},{s.next_text.convert_to_str()[0:7]}')
                s.next_text = None
            
            if s.next_color:
                self.seg_connection.send(('PC:{},{}').format(s.hex_id, s.next_color))
                s.next_color = None

    def update_leds(self):
        """Update all the LEDs connected to a FAST controller.

        This is done once per game loop for efficiency (i.e. all LEDs are sent as a single
        update rather than lots of individual ones).

        """
        dirty_leds = [led for led in self.fast_leds.values() if led.dirty]

        if dirty_leds:
            msg = 'RS:' + ','.join(["%s%s" % (led.number, led.current_color) for led in dirty_leds])
            self.rgb_connection.send(msg)

    async def get_hw_switch_states(self):
        """Return hardware states."""
        return self.hw_switch_data

    def receive_nw_open(self, msg, remote_processor):
        """Process network switch open.

        Args:
        ----
            msg: switch number
            remote_processor: Processor which sent the message.
        """
        assert remote_processor == "NET"
        self.machine.switch_controller.process_switch_by_num(state=0,
                                                             num=(msg, 1),
                                                             platform=self)

    def receive_nw_closed(self, msg, remote_processor):
        """Process network switch closed.

        Args:
        ----
            msg: switch number
            remote_processor: Processor which sent the message.
        """
        assert remote_processor == "NET"
        self.machine.switch_controller.process_switch_by_num(state=1,
                                                             num=(msg, 1),
                                                             platform=self)

    def receive_local_open(self, msg, remote_processor):
        """Process local switch open.

        Args:
        ----
            msg: switch number
            remote_processor: Processor which sent the message.
        """
        assert remote_processor == "NET"
        self.machine.switch_controller.process_switch_by_num(state=0,
                                                             num=(msg, 0),
                                                             platform=self)

    def receive_local_closed(self, msg, remote_processor):
        """Process local switch closed.

        Args:
        ----
            msg: switch number
            remote_processor: Processor which sent the message.
        """
        assert remote_processor == "NET"
        self.machine.switch_controller.process_switch_by_num(state=1,
                                                             num=(msg, 0),
                                                             platform=self)

    def receive_sa(self, msg, remote_processor):
        """Receive all switch states.

        Args:
        ----
            msg: switch states as bytearray
            remote_processor: Processor which sent the message.
        """
        assert remote_processor == "NET"
        self.debug_log("Received SA: %s", msg)
        hw_states = {}

        # Support for v1 firmware which uses network + local switches
        if self.net_connection.is_legacy:
            _, local_states, _, nw_states = msg.split(',')
            for offset, byte in enumerate(bytearray.fromhex(nw_states)):
                for i in range(8):
                    num = Util.int_to_hex_string((offset * 8) + i)
                    if byte & (2**i):
                        hw_states[(num, 1)] = 1
                    else:
                        hw_states[(num, 1)] = 0
        # Support for v2 firmware which uses only local switches
        else:
            _, local_states = msg.split(',')

        for offset, byte in enumerate(bytearray.fromhex(local_states)):
            for i in range(8):

                num = Util.int_to_hex_string((offset * 8) + i)

                if byte & (2**i):
                    hw_states[(num, 0)] = 1
                else:
                    hw_states[(num, 0)] = 0

        self.hw_switch_data = hw_states

    @staticmethod
    def convert_number_from_config(number):
        """Convert a number from config format to hex."""
        return Util.int_to_hex_string(number)

    def _parse_driver_number(self, number):
        try:
            board_str, driver_str = number.split("-")
        except ValueError as e:
            total_drivers = 0
            for board_obj in self.io_boards.values():
                total_drivers += board_obj.driver_count
            try:
                index = self.convert_number_from_config(number)
            except ValueError:
                self.raise_config_error(
                    f"Could not parse driver number {number}. Please verify the number format is either " +
                    "board-driver or driver. Driver should be an integer here.", 7)

            if int(index, 16) >= total_drivers:
                raise AssertionError(f"Driver {int(index, 16)} does not exist. "
                                     f"Only {total_drivers} drivers found. Driver number: {number}") from e

            return index

        board = int(board_str)
        driver = int(driver_str)

        if board not in self.io_boards:
            raise AssertionError(f"Board {board} does not exist for driver {number}")

        if self.io_boards[board].driver_count <= driver:
            raise AssertionError(f"Board {board} only has {self.io_boards[board].driver_count} drivers. "
                                 "Driver: {number}")

        index = 0
        for board_number, board_obj in self.io_boards.items():
            if board_number >= board:
                continue
            index += board_obj.driver_count

        return Util.int_to_hex_string(index + driver)

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> FASTDriver:
        """Configure a driver.

        Args:
        ----
            config: Driver config.
            number: Number of this driver.
            platform_settings: Platform specific settings.

        Returns: Driver object
        """
        # dont modify the config. make a copy
        platform_settings = deepcopy(platform_settings)

        if not self.net_connection:
            raise AssertionError('A request was made to configure a FAST '
                                 'driver, but no connection to a NET processor'
                                 'is available')

        if not number:
            raise AssertionError("Driver needs a number")

        # Figure out the connection type for v1 hardware: local or network (default)
        if self.net_connection.is_legacy:
            if ('connection' in platform_settings and
                    platform_settings['connection'].lower() == 'local'):
                platform_settings['connection'] = 0
            else:
                platform_settings['connection'] = 1
        # V2 hardware uses only local drivers
        else:
            platform_settings['connection'] = 0

        # If we have Retro driver boards, look up the driver number
        if self.is_retro:
            try:
                number = fast_defines.RETRO_DRIVER_MAP[number.upper()]
            except KeyError:
                self.raise_config_error(f"Could not find Retro driver {number}", 1)

        # If we have FAST IO boards, we need to make sure we have hex strings
        elif self.machine_type == 'fast':
            number = self._parse_driver_number(number)

        else:
            raise AssertionError("Invalid machine type: {self.machine_type}")

        return FASTDriver(config, self, number, platform_settings)

    def _parse_servo_number(self, number):
        try:
            board_str, servo_str = number.split("-")
        except ValueError:
            return self.convert_number_from_config(number)

        board = int(board_str)
        servo = int(servo_str)
        if board < 0:
            raise AssertionError("Board needs to be positive.")

        if servo < 0 or servo > 5:
            raise AssertionError("Servo number has to be between 0 and 5.")

        # every servo board supports exactly 6 servos
        return self.convert_number_from_config(board * 6 + servo)

    async def configure_servo(self, number: str) -> FastServo:
        """Configure a servo.

        Args:
        ----
            number: Number of servo

        Returns: Servo object.
        """
        number_int = self._parse_servo_number(str(number))

        return FastServo(number_int, self.net_connection)

    def _parse_switch_number(self, number):
        try:
            board_str, switch_str = number.split("-")
        except ValueError as e:
            total_switches = 0
            for board_obj in self.io_boards.values():
                total_switches += board_obj.switch_count
            index = self.convert_number_from_config(number)

            if int(index, 16) >= total_switches:
                raise AssertionError(f"Switch {int(index, 16)} does not exist. Only "
                                     f"{total_switches} switches found. Switch number: {number}") from e

            return index

        board = int(board_str)
        switch = int(switch_str)

        if board not in self.io_boards:
            raise AssertionError("Board {} does not exist for switch {}".format(board, number))

        if self.io_boards[board].switch_count <= switch:
            raise AssertionError("Board {} only has {} switches. Switch: {}".format(
                board, self.io_boards[board].switch_count, number))

        index = 0
        for board_number, board_obj in self.io_boards.items():
            if board_number >= board:
                continue
            index += board_obj.switch_count

        return Util.int_to_hex_string(index + switch)

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> FASTSwitch:
        """Configure the switch object for a FAST Pinball controller.

        V1 FAST Controllers support two types of switches: `local` and `network`.
        Local switches are switches that are connected to the FAST controller
        board itself, and network switches are those connected to a FAST I/O
        board. V2 FAST Controllers consider all switches to be local, even those
        connected to I/O boards.

        MPF needs to know which type of switch is this is. You can specify the
        switch's connection type in the config file via the ``connection:``
        setting (either ``local`` or ``network``).

        If a connection type is not specified, this method will use some
        intelligence to try to figure out which default should be used.

        If the DriverBoard type is ``fast`` and the firmware is legacy (v1),
        then mpf assumes the default is ``network``. If it's a v2 firmware or
        any other type of board (``sys11``, ``wpc95``, ``wpc89``) then mpf
        assumes the connection type is ``local``. Connection types can be mixed
        and matched in the same machine.

        Args:
        ----
            number: Number of this switch.
            config: Switch config.
            platform_config: Platform specific settings.

        Returns: Switch object.
        """
        if not number:
            raise AssertionError("Switch needs a number")

        if not self.net_connection:
            raise AssertionError("A request was made to configure a FAST "
                                 "switch, but no connection to a NET processor"
                                 "is available")

        if self.is_retro:
            # translate switch num to FAST switch
            try:
                number = fast_defines.RETRO_SWITCH_MAP[str(number).upper()]
            except KeyError:
                self.raise_config_error(f"Could not find switch {number}", 2)
        else:
            try:
                number = self._parse_switch_number(number)
            except ValueError:
                self.raise_config_error(f"Could not parse switch number {config.name}/{number}. Seems "
                                        "to be not a valid switch number for the FAST platform.", 8)

        if self.net_connection.is_legacy:
            # V1 devices can explicitly define switches to be local, or default to network
            if ('connection' in platform_config and
                    platform_config['connection'].lower() == 'local'):
                platform_config['connection'] = 0
            else:
                platform_config['connection'] = 1
        else:
            # V2 devices are only local switches
            platform_config['connection'] = 0

        # convert the switch number into a tuple which is:
        # (switch number, connection)
        number_tuple = (number, platform_config['connection'])

        self.debug_log("FAST Switch hardware tuple: %s (%s)", number, config.name)

        switch = FASTSwitch(config=config, number_tuple=number_tuple,
                            platform=self, platform_settings=platform_config)

        return switch

    def configure_light(self, number, subtype, config, platform_settings) -> LightPlatformInterface:
        """Configure light in platform."""
        if not self.net_connection:
            raise AssertionError('A request was made to configure a FAST Light, '
                                 'but no connection to a NET processor is '
                                 'available')
        if subtype == "gi":
            return FASTGIString(number, self.net_connection.send, self.machine,
                                int(1 / self.machine.config['mpf']['default_light_hw_update_hz'] * 1000))
        if subtype == "matrix":
            return FASTMatrixLight(number, self.net_connection.send, self.machine,
                                   int(1 / self.machine.config['mpf']['default_light_hw_update_hz'] * 1000), self)
        if not subtype or subtype == "led":
            if self.rgb_connection and not self.flag_led_tick_registered:
                # Update leds every frame
                self._led_task = self.machine.clock.schedule_interval(
                    self.update_leds, 1 / self.machine.config['mpf']['default_light_hw_update_hz'])
                self.flag_led_tick_registered = True

            try:
                number_str, channel = number.split("-")
            except ValueError as e:
                self.raise_config_error("Light syntax is number-channel (but was \"{}\") for light {}.".format(
                    number, config.name), 9, source_exception=e)
                raise
            if number_str not in self.fast_leds:
                self.fast_leds[number_str] = FASTDirectLED(
                    number_str, int(self.config['hardware_led_fade_time']), self.machine)
            fast_led_channel = FASTDirectLEDChannel(self.fast_leds[number_str], channel)
            self.fast_leds[number_str].add_channel(int(channel), fast_led_channel)

            return fast_led_channel

        raise AssertionError("Unknown subtype {}".format(subtype))

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse light channels from number string."""
        if subtype == "gi":
            if self.is_retro:  # translate matrix/map number to FAST GI number
                try:
                    number = fast_defines.RETRO_GI_MAP[str(number).upper()]
                except KeyError:
                    self.raise_config_error(f"Could not find GI {number}", 3)
            else:
                number = self.convert_number_from_config(number)

            return [
                {
                    "number": number
                }
            ]
        if subtype == "matrix":
            if self.is_retro:  # translate matrix number to FAST light num
                try:
                    number = fast_defines.RETRO_LIGHT_MAP[str(number).upper()]
                except KeyError:
                    self.raise_config_error(f"Could not find light {number}", 4)
            else:
                number = self.convert_number_from_config(number)

            return [
                {
                    "number": number
                }
            ]
        if not subtype or subtype == "led":
            # if the LED number is in <channel> - <led> format, convert it to a
            # FAST hardware number
            if '-' in str(number):
                num = str(number).split('-')
                index = (int(num[0]) * 64) + int(num[1])
            else:
                index = int(number)
            return [
                {"number": f"{index}-0"},
                {"number": f"{index}-1"},
                {"number": f"{index}-2"},
            ]

        raise AssertionError(f"Unknown subtype {subtype}")

    def configure_dmd(self):
        """Configure a hardware DMD connected to a FAST controller."""
        if not self.dmd_connection:
            raise AssertionError("A request was made to configure a FAST DMD, "
                                 "but no connection to a DMD processor is "
                                 "available.")

        return FASTDMD(self.machine, self.dmd_connection.send)

    async def configure_segment_display(self, number: str, display_size: int, platform_settings) -> FASTSegmentDisplay:
        """Configure a segment display."""
        self.debug_log("Configuring FAST segment display.")
        del platform_settings
        if not self.seg_connection:
            raise AssertionError("A request was made to configure a FAST "
                                 "Segment Display but no connection is "
                                 "available.")

        display = FASTSegmentDisplay(int(number), self.seg_connection)
        return display

    @classmethod
    def get_coil_config_section(cls):
        """Return coil config section."""
        return "fast_coils"

    @classmethod
    def get_switch_config_section(cls):
        """Return switch config section."""
        return "fast_switches"

    def _check_switch_coil_combination(self, switch, coil):
        # V2 hardware can write rules across node boards
        if not self.net_connection.is_legacy:
            return

        switch_number = int(switch.hw_switch.number[0], 16)
        coil_number = int(coil.hw_driver.number, 16)

        # first 8 switches always work
        if 0 <= switch_number <= 7:
            return

        switch_index = 0
        coil_index = 0
        for board_obj in self.io_boards.values():
            # if switch and coil are on the same board we are fine
            if switch_index <= switch_number < switch_index + board_obj.switch_count and \
                    coil_index <= coil_number < coil_index + board_obj.driver_count:
                return
            coil_index += board_obj.driver_count
            switch_index += board_obj.switch_count

        raise AssertionError(f"Driver {coil.hw_driver.number} and switch {switch.hw_switch.number} "
                             "are on different boards. Cannot apply rule!")

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and release rule to driver."""
        self.debug_log("Setting Pulse on hit and release HW Rule. Switch: %s,"
                       "Driver: %s", enable_switch.hw_switch.number,
                       coil.hw_driver.number)

        self._check_switch_coil_combination(enable_switch, coil)

        driver = coil.hw_driver

        cmd = '{}{},{},{},18,{},{},00,{},00'.format(
            driver.get_config_cmd(),
            coil.hw_driver.number,
            driver.get_control_for_cmd(enable_switch),
            enable_switch.hw_switch.number[0],
            Util.int_to_hex_string(coil.pulse_settings.duration),
            driver.get_pwm_for_cmd(coil.pulse_settings.power),
            driver.get_recycle_ms_for_cmd(coil.recycle, coil.pulse_settings.duration))

        enable_switch.hw_switch.configure_debounce(enable_switch.debounce)
        driver.set_autofire(cmd, coil.pulse_settings.duration, coil.pulse_settings.power, 0)

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                      eos_switch: SwitchSettings, coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and release and disable rule on driver."""
        # Potential command from Dave:
        # Command
        # [DL/DN]:<DRIVER_ID>,<CONTROL>,<SWITCH_ID_ON>,<75>,<SWITCH_ID_OFF>,<Driver On Time1>,<Driver On Time2 X 100mS>,
        # <PWM2><Driver Rest Time><CR>#
        # SWITCH_ID_ON would be the flipper switch
        # SWITCH_ID_OFF would be the EOS switch.
        # So for the flipper, Driver On Time1 will = the maximum time the coil can be held on if the EOS fails.
        # Driver On Time2 X 100mS would not be used for a flipper, so set it to 0.
        # And PWM2 should be left on full 0xff unless you need less power for some reason.
        self.debug_log("Setting Pulse on hit and release with HW Rule. Switch:"
                       "%s, Driver: %s", enable_switch.hw_switch.number,
                       coil.hw_driver.number)

        self._check_switch_coil_combination(enable_switch, coil)
        self._check_switch_coil_combination(eos_switch, coil)

        driver = coil.hw_driver

        cmd = '{}{},{},{},75,{},{},00,{},{}'.format(
            driver.get_config_cmd(),
            coil.hw_driver.number,
            driver.get_control_for_cmd(enable_switch, eos_switch),
            enable_switch.hw_switch.number[0],
            eos_switch.hw_switch.number[0],
            Util.int_to_hex_string(coil.pulse_settings.duration),
            driver.get_pwm_for_cmd(coil.pulse_settings.power),
            driver.get_recycle_ms_for_cmd(coil.recycle, coil.pulse_settings.duration))

        enable_switch.hw_switch.configure_debounce(enable_switch.debounce)
        eos_switch.hw_switch.configure_debounce(eos_switch.debounce)
        driver.set_autofire(cmd, coil.pulse_settings.duration, coil.pulse_settings.power, 0)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver."""
        self.warning_log("EOS cut-off rule will not work with FAST on single-wound coils. %s %s %s", enable_switch,
                         eos_switch, coil)
        self.set_pulse_on_hit_and_enable_and_release_rule(enable_switch, coil)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit rule on driver."""
        self.debug_log("Setting Pulse on hit and release HW Rule. Switch: %s,"
                       "Driver: %s", enable_switch.hw_switch.number,
                       coil.hw_driver.number)

        self._check_switch_coil_combination(enable_switch, coil)

        driver = coil.hw_driver

        cmd = '{}{},{},{},10,{},{},00,00,{}'.format(
            driver.get_config_cmd(),
            coil.hw_driver.number,
            driver.get_control_for_cmd(enable_switch),
            enable_switch.hw_switch.number[0],
            Util.int_to_hex_string(coil.pulse_settings.duration),
            driver.get_pwm_for_cmd(coil.pulse_settings.power),
            driver.get_recycle_ms_for_cmd(coil.recycle, coil.pulse_settings.duration))

        enable_switch.hw_switch.configure_debounce(enable_switch.debounce)
        driver.set_autofire(cmd, coil.pulse_settings.duration, coil.pulse_settings.power, 0)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and relase rule on driver."""
        self.debug_log("Setting Pulse on hit and enable and release HW Rule. "
                       "Switch: %s, Driver: %s",
                       enable_switch.hw_switch.number, coil.hw_driver.number)

        self._check_switch_coil_combination(enable_switch, coil)

        driver = coil.hw_driver

        cmd = '{}{},{},{},18,{},{},{},{},00'.format(
            driver.get_config_cmd(),
            driver.number,
            driver.get_control_for_cmd(enable_switch),
            enable_switch.hw_switch.number[0],
            Util.int_to_hex_string(coil.pulse_settings.duration),
            driver.get_pwm_for_cmd(coil.pulse_settings.power),
            driver.get_hold_pwm_for_cmd(coil.hold_settings.power),
            driver.get_recycle_ms_for_cmd(coil.recycle, coil.pulse_settings.duration))

        enable_switch.hw_switch.configure_debounce(enable_switch.debounce)
        driver.set_autofire(cmd, coil.pulse_settings.duration, coil.pulse_settings.power, coil.hold_settings.power)

    def clear_hw_rule(self, switch, coil):
        """Clear a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        Args:
        ----
            switch: The switch whose rule you want to clear.
            coil: The coil whose rule you want to clear.

        """
        self.debug_log("Clearing HW Rule for switch: %s, coils: %s",
                       switch.hw_switch.number, coil.hw_driver.number)

        # TODO: check that the rule is switch + coil and not another switch + this coil

        driver = coil.hw_driver

        driver.clear_autofire(driver.get_config_cmd(), driver.number)

    def receive_bootloader(self, msg, remote_processor):
        """Process bootloader message."""
        self.debug_log("Got Bootloader message: %s from %s", msg, remote_processor)
        ignore_rgb = self.config['ignore_rgb_crash'] and \
            remote_processor == self.rgb_connection.remote_processor
        if msg in ('00', '02'):
            action = "Ignoring RGB crash and continuing play." if ignore_rgb else "MPF will exit now."
            self.error_log("The FAST %s processor rebooted. Unfortunately, that means that it lost all its state "
                           "(such as hardware rules or switch configs). This is likely caused by an unstable "
                           "power supply but it might also be a firmware bug. %s", remote_processor, action)
            if ignore_rgb:
                self.machine.events.post("fast_rgb_rebooted", msg=msg)
                return
            self.machine.stop("FAST {} rebooted during game".format(remote_processor))
