"""FAST hardware platform.

Contains the hardware interface and drivers for the FAST Pinball platform
hardware, including the FAST Neuron, Nano, and Retro controllers as well
as FAST I/O boards.
"""
import asyncio
from base64 import b16decode
from copy import deepcopy
from typing import Dict, Set, Optional
from serial import SerialException

from mpf.exceptions.runtime_error import MpfRuntimeError
from mpf.platforms.fast.fast_io_board import FastIoBoard
from mpf.platforms.fast.fast_servo import FastServo
from mpf.platforms.fast import fast_defines
from mpf.platforms.fast.fast_audio import FASTAudio
from mpf.platforms.fast.fast_dmd import FASTDMD
from mpf.platforms.fast.fast_driver import FASTDriver
from mpf.platforms.fast.fast_gi import FASTGIString
from mpf.platforms.fast.fast_led import FASTDirectLED, FASTDirectLEDChannel, FASTExpLED
from mpf.platforms.fast.fast_light import FASTMatrixLight
from mpf.platforms.fast.fast_segment_display import FASTSegmentDisplay
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

    """Platform class for the FAST Pinball hardware."""

    # __slots__ = ["dmd_connection", "net_connection", "rgb_connection", "seg_connection", "exp_connection", "aud_connection",
    #              "is_retro", "serial_connections", "fast_leds", "fast_commands", "config", "machine_type", "hw_switch_data",
    #              "io_boards", "flag_led_tick_registered", "_watchdog_task", "_led_task", "_seg_task", "_exp_led_task",
    #              "fast_exp_leds", "flag_exp_led_tick_registered", "fast_segs", "exp_boards", "exp_breakout_boards",
    #              "exp_breakouts_with_leds"]

    port_types = ['net', 'exp', 'aud', 'dmd', 'rgb', 'seg', 'emu']

    def __init__(self, machine):
        """Initialize FAST hardware platform.

        Args:
        ----
            machine: The main ``MachineController`` instance.
        """
        super().__init__(machine)

        self.config = self.machine.config_validator.validate_config("fast", self.machine.config['fast'])
        self._configure_device_logging_and_debug("FAST", self.config)  #todo

        self.ports = list()

        for port_type in self.port_types:
            if self.config[port_type]:
                self.ports.append(port_type)


        if self.config["net"]["controller"]:
            self.machine_type = self.config["net"]["controller"]

        if self.machine_type in ['sys11', 'wpc89', 'wpc95']:
            self.debug_log("Configuring the FAST Controller for Retro driver board")
            # todo make logs respect fast:debug:True or figure out how they work
            self.is_retro = True
        elif self.machine_type in ['neuron', 'nano']:
            self.debug_log("Configuring FAST Controller for FAST I/O boards.")
            self.is_retro = False
        else:
            self.raise_config_error(f'Unknown machine_type "{self.machine_type}" configured fast.', 6)

        # Most FAST platforms don't use ticks, but System11 does
        self.features['tickless'] = self.machine_type != 'sys11'

        self._watchdog_task = None
        self._led_task = None
        self._exp_led_task = None
        self._seg_task = None
        self.serial_connections = dict()
        self.fast_leds = dict()
        self.fast_exp_leds = dict()
        self.fast_segs = list()
        self.flag_led_tick_registered = False
        self.flag_exp_led_tick_registered = False
        self.exp_boards = dict()  # k: EE address, v: FastExpansionBoard instances
        self.exp_breakout_boards = dict()  # k: EEB address, v: FastBreakoutBoard instances
        # self.exp_dirty_led_ports = set() # FastLedPort instances
        self.exp_breakouts_with_leds = set()

        self.hw_switch_data = None
        self.io_boards = dict()     # type: Dict[int, FastIoBoard]

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
                              'AV': lambda x, y: self.receive_audio('AV', x, y), # audio cmd received
                              'AS': lambda x, y: self.receive_audio('AS', x, y),
                              'AH': lambda x, y: self.receive_audio('AH', x, y),
                              'SA': self.receive_sa,  # all switch states
                              '/N': self.receive_nw_open,    # nw switch open
                              '-N': self.receive_nw_closed,  # nw switch closed
                              '/L': self.receive_local_open,    # local sw open
                              '-L': self.receive_local_closed,  # local sw cls
                              '!B': self.receive_bootloader,    # nano bootloader message
                              }

    def get_info_string(self):
        """Dump info strings about boards."""
        info_string = ""

        for port in sorted(self.serial_connections.keys()):
            info_string += f"{port.upper()}: {self.serial_connections[port].remote_model} v{self.serial_connections[port].remote_firmware}\n"

        info_string += "\nI/O Boards:\n"
        for board in self.io_boards.values():
            info_string += board.get_description_string() + "\n"
        return info_string

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
        if self._exp_led_task:
            self._exp_led_task.cancel()
            self._exp_led_task = None

        if self.serial_connections['net']:  # TODO move to communicator via .stop() method
            try:
                self.serial_connections['net'].send_txt('WD:1')  # set watchdog to expire in 1ms
            except Exception:  # port might be closed already
                pass
                # TODO move to communicator via .stop() method, await in comm for ack message


        if self.serial_connections['rgb']:
            self.serial_connections['rgb'].send_txt('BL:AA55')  # reset CPU using bootloader
        if self.serial_connections['dmd']:
            self.serial_connections['dmd'].send_txt('BL:AA55')  # reset CPU using bootloader
        if self.serial_connections['seg']:
            # self.serial_connections['seg'].send_txt('***')  # TODO: reset CPU using
            pass

        try:
            for board_address in self.exp_boards.keys():
                self.serial_connections['exp'].send_txt(f'BR@{board_address}:')
        except KeyError:
            pass

        # wait 100ms for the messages to be sent
        self.machine.clock.loop.run_until_complete(asyncio.sleep(.1))

        for port, connection in self.serial_connections.items():
            if connection:
                connection.stop()
                self.serial_connections[port] = None

        self.serial_connections = dict()

    async def start(self):
        """Start listening for commands and schedule watchdog."""
        self._watchdog_task = self.machine.clock.schedule_interval(self._update_watchdog,
                                                                   self.config['net']['watchdog'] / 2000)
        # todo move watchdog to only be on net cpu

        for connection in self.serial_connections.values():
            await connection.start_read_loop()

    def __repr__(self):
        """Return str representation."""
        return '<Platform.FAST>'

    def register_io_board(self, board):
        """Register a FAST I/O Board.

        Args:
        ----
            board: 'mpf.platform.fast.fast_io_board.FastIoBoard' to register
        """
        if board.node_id in self.io_boards:
            raise AssertionError("Duplicate node_id")
        self.io_boards[board.node_id] = board

    def register_expansion_board(self, board):
        """Register an Expansion board."""
        if board.address in self.exp_boards:
            raise AssertionError("Duplicate expansion board address")
        self.exp_boards[board.address] = board

    def register_breakout_board(self, board):
        """Register a Breakout board."""
        if board.address in self.exp_breakout_boards:
            raise AssertionError("Duplicate breakout board address")
        self.exp_breakout_boards[board.address] = board

    def register_led_board(self, board):
        """Register a Breakout board that has LEDs."""
        self.exp_breakouts_with_leds.add(board.address[:3])

    def _update_watchdog(self):
        """Send Watchdog command."""
        try:
            self.serial_connections['net'].send_txt('WD:' + str(hex(self.config['watchdog']))[2:])  # TODO don't calc each loop
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
        """Connect to each port from the config."""

        for port in self.ports:

            config = self.config[port]

            if port == 'net':
                if config['controller'] == 'neuron':
                    from mpf.platforms.fast.communicators.net_neuron import FastNetNeuronCommunicator
                    communicator = FastNetNeuronCommunicator(platform=self, processor=port, config=config)
                elif config['controller'] == 'nano':
                    from mpf.platforms.fast.communicators.net_nano import FastNetNanoCommunicator
                    communicator = FastNetNanoCommunicator(platform=self, processor=port, config=config)
                elif config['controller'] in ['sys11', 'wpc89', 'wpc95']:
                    from mpf.platforms.fast.communicators.net_retro import FastNetRetroCommunicator
                    communicator = FastNetRetroCommunicator(platform=self, processor=port, config=config)
                else:
                    raise AssertionError("Unknown controller type")  # TODO better error
                self.serial_connections['net'] = communicator

            elif port == 'exp':
                from mpf.platforms.fast.communicators.exp import FastExpCommunicator
                communicator = FastExpCommunicator(platform=self, processor=port,config=config)
                self.serial_connections['exp'] = communicator
            elif port == 'seg':
                from mpf.platforms.fast.communicators.seg import FastSegCommunicator
                communicator = FastSegCommunicator(platform=self, processor=port,config=config)
                self.serial_connections['seg'] = communicator
            elif port == 'aud':
                from mpf.platforms.fast.communicators.aud import FastAudCommunicator
                communicator = FastAudCommunicator(platform=self, processor=port,config=config)
                self.serial_connections['aud'] = communicator
            elif port == 'dmd':
                from mpf.platforms.fast.communicators.dmd import FastDmdCommunicator
                communicator = FastDmdCommunicator(platform=self, processor=port,config=config)
                self.serial_connections['dmd'] = communicator
            elif port == 'emu':
                from mpf.platforms.fast.communicators.emu import FastEmuCommunicator
                communicator = FastEmuCommunicator(platform=self, processor=port,config=config)
                self.serial_connections['emu'] = communicator
            elif port == 'rgb':
                from mpf.platforms.fast.communicators.rgb import FastRgbCommunicator
                communicator = FastRgbCommunicator(platform=self, processor=port,config=config)
                self.serial_connections['rgb'] = communicator
            else:
                raise AssertionError("Unknown processor type")  # TODO better error

            try:
                await communicator.connect()
            except SerialException as e:
                raise MpfRuntimeError("Could not open serial port {}. Is something else connected to the port? "
                                      "Did the port number or your computer change? Do you have permissions to the port? "
                                      "".format(port), 1, self.log.name) from e
            await communicator.init()
            self.serial_connections[port] = communicator

    def _start_seg_updates(self, **kwargs):  #TODO Move to comm, base class even for all the use update tasks
        for s in self.machine.device_manager.collections["segment_displays"]:
            self.fast_segs.append(s.hw_display)

        self.fast_segs.sort(key=lambda x: x.number)

        if self.fast_segs:
            self._seg_task = self.machine.clock.schedule_interval(self._update_segs,
                                                1 / self.config['seg']['fps'])

    def _update_segs(self, **kwargs):
        for s in self.fast_segs:

            if s.next_text:
                self.serial_connections['seg'].send_txt(f'PA:{s.hex_id},{s.next_text.convert_to_str()[0:7]}')
                s.next_text = None

            if s.next_color:
                self.serial_connections['seg'].send_txt(('PC:{},{}').format(s.hex_id, s.next_color))
                s.next_color = None

    def update_leds(self):
        """Update all the LEDs connected to the RGB processor of a FAST Nano controller.

        This is done once per game loop for efficiency (i.e. all LEDs are sent as a single
        update rather than lots of individual ones).

        """
        dirty_leds = [led for led in self.fast_leds.values() if led.dirty]

        if dirty_leds:
            msg = 'RS:' + ','.join(["%s%s" % (led.number, led.current_color) for led in dirty_leds])
            self.serial_connections['rgb'].send_txt(msg)

    def update_exp_leds(self):
        # max 32ms / 31.25fps TODO add enforcement

        for breakout_address in self.exp_breakouts_with_leds:
            dirty_leds = {k:v.current_color for (k, v) in self.fast_exp_leds.items() if (v.dirty and v.address == breakout_address)}
            # {'88000': 'FFFFFF', '88002': '121212'}

            if dirty_leds:
                hex_count = Util.int_to_hex_string(len(dirty_leds))
                msg = f'52443A{hex_count}'  # RD: in hex 52443A

                for led_num, color in dirty_leds.items():
                    msg += f'{led_num[3:]}{color}'

                self.serial_connections['exp'].set_active_board(breakout_address)
                self.serial_connections['exp'].send_bytes(b16decode(msg))

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
        if self.machine_type == 'nano':
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

        if not self.serial_connections['net']:
            raise AssertionError('A request was made to configure a FAST '
                                 'driver, but no connection to a NET processor'
                                 'is available')

        if not number:
            raise AssertionError("Driver needs a number")

        # Figure out the connection type for v1 hardware: local or network (default)
        if self.machine_type == 'nano':
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

        # If we have FAST I/O boards, we need to make sure we have hex strings
        elif self.machine_type in ['nano', 'neuron']:
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

        return FastServo(number_int, self.serial_connections['net'])

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

        if not self.serial_connections['net']:
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

        if self.machine_type == 'nano':
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

        del platform_settings

        if not (self.serial_connections['net'] or self.serial_connections['exp']):
            raise AssertionError('A request was made to configure a FAST Light, '
                                 'but no connection to a NET or EXP processor is '
                                 'available')
        if subtype == "gi":
            return FASTGIString(number, self.serial_connections['net'], self.machine,
                                int(1 / self.config['net']['gi_hz'] * 1000))
        if subtype == "matrix":
            return FASTMatrixLight(number, self.serial_connections['net'], self.machine,
                                   int(1 / self.config['net']['lamp_hz'] * 1000), self)
        if not subtype or subtype == "led":

            try:
                number_str, channel = number.rsplit('-', 1)

            except ValueError as e:
                self.raise_config_error("Light syntax is number-channel (but was \"{}\") for light {}.".format(
                    number, config.name), 9, source_exception=e)
                raise

            if number_str[:3] in ('exp', 'cpu'):

                if not self.serial_connections['exp']:
                    self.raise_config_error("An LED is configured for an expansion board, but no EXP connection exists.", 10)  #todo pick a real number

                if not self.flag_exp_led_tick_registered:

                    if self.config['exp']['led_hz'] > 31.25:
                        self.config['exp']['led_hz'] = 31.25

                    self._exp_led_task = self.machine.clock.schedule_interval(
                        self.update_exp_leds, 1 / self.config['exp']['led_hz'])
                    self.flag_exp_led_tick_registered = True

                this_led_number = FASTExpLED.parse_number_string(number_str, self, return_all=False)

                # this code runs once for each channel, so it will be called 3x per LED which
                # is why we check this here
                if this_led_number not in self.fast_exp_leds:
                    self.fast_exp_leds[this_led_number] = FASTExpLED(number_str, int(self.config['exp']['led_fade_time']), self)

                fast_led_channel = FASTDirectLEDChannel(self.fast_exp_leds[this_led_number], channel)
                self.fast_exp_leds[this_led_number].add_channel(int(channel), fast_led_channel)

                return fast_led_channel

            elif number_str not in self.fast_leds:

                if not self.flag_led_tick_registered:
                    self._led_task = self.machine.clock.schedule_interval(
                        self.update_leds, 1 / self.config['rgb']['led_hz'])
                    self.flag_led_tick_registered = True

                if number_str not in self.fast_leds:
                    self.fast_leds[number_str] = FASTDirectLED(
                        number_str, int(self.config['rgb']['led_fade_time']), self)  # todo is this a real setting?

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

            if str(number).startswith("exp") or str(number).startswith("cpu"):
                # expansion board LED
                index = number

            # if the LED number is in <channel> - <led> format, convert it to a
            # FAST hardware number
            elif '-' in str(number):
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
        if not self.serial_connections['dmd']:
            raise AssertionError("A request was made to configure a FAST DMD, "
                                 "but no connection to a DMD processor is "
                                 "available.")

        return FASTDMD(self.machine, self.serial_connections['dmd'].send_raw)


    def configure_hardware_sound_system(self, platform_settings):
        """Configure a hardware FAST audio controller."""
        if not self.serial_connections['aud']:
            raise AssertionError("A request was made to configure a FAST AUDIO, "
                                 "but no connection to a AUDIO processor is "
                                 "available.")

        return FASTAudio(self.machine, self.serial_connections['aud'].send, platform_settings)


    async def configure_segment_display(self, number: str, display_size: int, platform_settings) -> FASTSegmentDisplay:
        """Configure a segment display."""
        self.debug_log("Configuring FAST segment display.")
        del platform_settings
        if not self.serial_connections['seg']:
            raise AssertionError("A request was made to configure a FAST "
                                 "Segment Display but no connection is "
                                 "available.")

        display = FASTSegmentDisplay(int(number), self.serial_connections['seg'])
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
        if not self.machine_type == 'nano':
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
        """Set pulse on hit and enable and release rule on driver."""
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

    def receive_bootloader(self, msg, remote_processor):  # move? TODO
        """Process bootloader message."""
        self.debug_log("Got Bootloader message: %s from %s", msg, remote_processor)
        ignore_rgb = self.config['rgb']['ignore_reboot'] and \
            remote_processor == self.serial_connections['rgb'].remote_processor
        if msg in ('00', '02'):
            action = "Ignoring RGB crash and continuing play." if ignore_rgb else "MPF will exit now."
            self.error_log("The FAST %s processor rebooted. Unfortunately, that means that it lost all its state "
                           "(such as hardware rules or switch configs). This is likely caused by an unstable "
                           "power supply but it might also be a firmware bug. %s", remote_processor, action)
            if ignore_rgb:
                self.machine.events.post("fast_rgb_rebooted", msg=msg)
                return
            self.machine.stop("FAST {} rebooted during game".format(remote_processor))
