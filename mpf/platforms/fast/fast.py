"""FAST hardware platform.

Contains the hardware interface and drivers for the FAST Pinball platform
hardware, including the FAST Core and WPC controllers as well as FAST I/O
boards.
"""
import asyncio
import os
from copy import deepcopy
from distutils.version import StrictVersion
from typing import Dict, Set, Optional
import serial.tools.list_ports

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

from mpf.core.platform import ServoPlatform, DmdPlatform, SwitchPlatform, DriverPlatform, LightsPlatform, \
    SegmentDisplayPlatform, DriverSettings, SwitchSettings, DriverConfig, SwitchConfig, RepulseSettings
from mpf.core.utility_functions import Util


# pylint: disable-msg=too-many-instance-attributes
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class FastHardwarePlatform(ServoPlatform, LightsPlatform, DmdPlatform,
                           SwitchPlatform, DriverPlatform, SegmentDisplayPlatform):

    """Platform class for the FAST hardware controller."""

    __slots__ = ["dmd_connection", "net_connection", "rgb_connection", "seg_connection",
                 "serial_connections", "fast_leds", "fast_commands", "config", "machine_type", "hw_switch_data",
                 "io_boards", "flag_led_tick_registered", "_watchdog_task", "_led_task"]

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
        else:
            self.machine_type = self.machine.config['hardware']['driverboards'].lower()

        if self.machine_type == 'wpc':
            self.debug_log("Configuring the FAST Controller for WPC driver "
                           "board")
        else:
            self.debug_log("Configuring FAST Controller for FAST IO boards.")

        self.features['tickless'] = True

        self.dmd_connection = None
        self.net_connection = None
        self.rgb_connection = None
        self.seg_connection = None
        self._watchdog_task = None
        self._led_task = None
        self.serial_connections = set()         # type: Set[FastSerialCommunicator]
        self.fast_leds = {}
        self.flag_led_tick_registered = False
        self.hw_switch_data = None
        self.io_boards = {}     # type: Dict[int, FastIoBoard]

        self.fast_commands = {'ID': lambda x, y: None,  # processor ID
                              'WX': lambda x, y: None,  # watchdog
                              'NI': lambda x, y: None,  # node ID
                              'RX': lambda x, y: None,  # RGB cmd received
                              'RA': lambda x, y: None,  # RGB all cmd received
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
            if StrictVersion(update['version']) > StrictVersion(max_firmware) and update['type'] == "net":
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
        if self.net_connection:
            self.net_connection.send('WD:' + str(hex(self.config['watchdog']))[2:])

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

        # Can't use try since it swallows too many errors for now
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
            devices = [port.device for port in serial.tools.list_ports.comports()]
            # Look for four devices with sequential tails of 0-3 or A-D
            seqs = (("0", "1", "2", "3"), ("A", "B", "C", "D"))
            for d in devices:
                for seq in seqs:
                    if d[-1] == seq[0]:
                        root = d[:-1]
                        if "{}{}".format(root, seq[1]) in devices and \
                           "{}{}".format(root, seq[2]) in devices and \
                           "{}{}".format(root, seq[3]) in devices:
                            ports = ("{}{}".format(root, seq[1]), "{}{}".format(root, seq[2]))
                            self.debug_log("Autodetect found ports! {}".format(ports))
                            break
                # If ports were found, skip the rest of the devices
                if ports:
                    break
            if not ports:
                raise RuntimeError("Unable to auto-detect FAST hardware from available devices: {}".format(
                                   ", ".join(devices)))
        else:
            ports = self.config['ports']

        bauds = self.config['baud']
        if len(bauds) == 1:
            bauds = [bauds[0]] * len(ports)
        elif len(bauds) != len(ports):
            raise AssertionError("FAST configuration found {} ports and {} baud rates".format(len(ports), len(bauds)))

        for index, port in enumerate(ports):
            comm = FastSerialCommunicator(platform=self, port=port, baud=bauds[index])
            await comm.connect()
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
        elif name == 'RGB':
            self.rgb_connection = communicator
            self.rgb_connection.send('RF:0')
            self.rgb_connection.send('RA:000000')  # turn off all LEDs
            self.rgb_connection.send('RF:{}'.format(
                Util.int_to_hex_string(self.config['hardware_led_fade_time'])))

    def update_leds(self):
        """Update all the LEDs connected to a FAST controller.

        This is done once per game loop for efficiency (i.e. all LEDs are sent as a single
        update rather than lots of individual ones).

        Also, every LED is updated every loop, even if it doesn't change. This
        is in case some interference causes a LED to change color. Since we
        update every loop, it will only be the wrong color for one tick.
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

        hw_states = dict()

        _, local_states, _, nw_states = msg.split(',')

        for offset, byte in enumerate(bytearray.fromhex(nw_states)):
            for i in range(8):
                num = Util.int_to_hex_string((offset * 8) + i)
                if byte & (2**i):
                    hw_states[(num, 1)] = 1
                else:
                    hw_states[(num, 1)] = 0

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
        except ValueError:
            total_drivers = 0
            for board_obj in self.io_boards.values():
                total_drivers += board_obj.driver_count
            index = self.convert_number_from_config(number)

            if int(index, 16) >= total_drivers:
                raise AssertionError("Driver {} does not exist. Only {} drivers found. Driver number: {}".format(
                    int(index, 16), total_drivers, number))

            return index

        board = int(board_str)
        driver = int(driver_str)

        if board not in self.io_boards:
            raise AssertionError("Board {} does not exist for driver {}".format(board, number))

        if self.io_boards[board].driver_count <= driver:
            raise AssertionError("Board {} only has {} drivers. Driver: {}".format(
                board, self.io_boards[board].driver_count, number))

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

        # If we have WPC driver boards, look up the driver number
        if self.machine_type == 'wpc':
            try:
                number = fast_defines.WPC_DRIVER_MAP[number.upper()]
            except KeyError:
                self.raise_config_error("Could not find WPC driver {}".format(number), 1)

            if ('connection' in platform_settings and
                    platform_settings['connection'].lower() == 'network'):
                platform_settings['connection'] = 1
            else:
                platform_settings['connection'] = 0  # local driver (default for WPC)

        # If we have FAST IO boards, we need to make sure we have hex strings
        elif self.machine_type == 'fast':

            number = self._parse_driver_number(number)

            # Now figure out the connection type
            if ('connection' in platform_settings and
                    platform_settings['connection'].lower() == 'local'):
                platform_settings['connection'] = 0
            else:
                platform_settings['connection'] = 1  # network driver (default for FAST)

        else:
            raise AssertionError("Invalid machine type: {}".format(
                self.machine_type))

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
        except ValueError:
            total_switches = 0
            for board_obj in self.io_boards.values():
                total_switches += board_obj.switch_count
            index = self.convert_number_from_config(number)

            if int(index, 16) >= total_switches:
                raise AssertionError("Switch {} does not exist. Only {} switches found. Switch number: {}".format(
                    int(index, 16), total_switches, number))

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

        FAST Controllers support two types of switches: `local` and `network`.
        Local switches are switches that are connected to the FAST controller
        board itself, and network switches are those connected to a FAST I/O
        board.

        MPF needs to know which type of switch is this is. You can specify the
        switch's connection type in the config file via the ``connection:``
        setting (either ``local`` or ``network``).

        If a connection type is not specified, this method will use some
        intelligence to try to figure out which default should be used.

        If the DriverBoard type is ``fast``, then it assumes the default is
        ``network``. If it's anything else (``wpc``, ``system11``, ``bally``,
        etc.) then it assumes the connection type is ``local``. Connection types
        can be mixed and matched in the same machine.

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

        if self.machine_type == 'wpc':  # translate switch num to FAST switch
            try:
                number = fast_defines.WPC_SWITCH_MAP[str(number).upper()]
            except KeyError:
                self.raise_config_error("Could not find WPC switch {}".format(number), 2)

            if 'connection' not in platform_config:
                platform_config['connection'] = 0  # local switch (default for WPC)
            else:
                platform_config['connection'] = 1  # network switch

        elif self.machine_type == 'fast':
            if 'connection' not in platform_config:
                platform_config['connection'] = 1  # network switch (default for FAST)
            else:
                platform_config['connection'] = 0  # local switch

            try:
                number = self._parse_switch_number(number)
            except ValueError:
                raise AssertionError("Could not parse switch number {}/{}. Seems "
                                     "to be not a valid switch number for the"
                                     "FAST platform.".format(config.name, number))

        # convert the switch number into a tuple which is:
        # (switch number, connection)
        number_tuple = (number, platform_config['connection'])

        self.debug_log("FAST Switch hardware tuple: %s (%s)", number, config.name)

        switch = FASTSwitch(config=config, number_tuple=number_tuple,
                            platform=self, platform_settings=platform_config)

        return switch

    def configure_light(self, number, subtype, config, platform_settings) -> LightPlatformInterface:
        """Configure light in platform."""
        del config
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
            if not self.flag_led_tick_registered:
                # Update leds every frame
                self._led_task = self.machine.clock.schedule_interval(
                    self.update_leds, 1 / self.machine.config['mpf']['default_light_hw_update_hz'])
                self.flag_led_tick_registered = True

            number_str, channel = number.split("-")
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
            if self.machine_type == 'wpc':  # translate number to FAST GI number
                try:
                    number = fast_defines.WPC_GI_MAP[str(number).upper()]
                except KeyError:
                    self.raise_config_error("Could not find WPC GI {}".format(number), 3)
            else:
                number = self.convert_number_from_config(number)

            return [
                {
                    "number": number
                }
            ]
        if subtype == "matrix":
            if self.machine_type == 'wpc':  # translate number to FAST light num
                try:
                    number = fast_defines.WPC_LIGHT_MAP[str(number).upper()]
                except KeyError:
                    self.raise_config_error("Could not find WPC light {}".format(number), 4)
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
                {
                    "number": "{}-0".format(index)
                },
                {
                    "number": "{}-1".format(index)
                },
                {
                    "number": "{}-2".format(index)
                },
            ]

        raise AssertionError("Unknown subtype {}".format(subtype))

    def configure_dmd(self):
        """Configure a hardware DMD connected to a FAST controller."""
        if not self.dmd_connection:
            raise AssertionError("A request was made to configure a FAST DMD, "
                                 "but no connection to a DMD processor is "
                                 "available.")

        return FASTDMD(self.machine, self.dmd_connection.send)

    async def configure_segment_display(self, number: str, platform_settings) -> FASTSegmentDisplay:
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

    def _check_switch_coil_combincation(self, switch, coil):
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

        raise AssertionError("Driver {} and switch {} are on different boards. Cannot apply rule!".format(
            coil.hw_driver.number, switch.hw_switch.number))

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and release rule to driver."""
        self.debug_log("Setting Pulse on hit and release HW Rule. Switch: %s,"
                       "Driver: %s", enable_switch.hw_switch.number,
                       coil.hw_driver.number)

        self._check_switch_coil_combincation(enable_switch, coil)

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

        self._check_switch_coil_combincation(enable_switch, coil)
        self._check_switch_coil_combincation(eos_switch, coil)

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

        self._check_switch_coil_combincation(enable_switch, coil)

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

        self._check_switch_coil_combincation(enable_switch, coil)

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
        self.debug_log("Got Bootloader message: %s from", msg, remote_processor)
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
