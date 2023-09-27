"""FAST Pinball hardware platform."""

import asyncio
from typing import Dict, Optional

from serial import SerialException

from mpf.core.platform import (DmdPlatform, DriverConfig, DriverSettings,
                               LightsPlatform, RepulseSettings,
                               SegmentDisplayPlatform, ServoPlatform,
                               SwitchConfig, SwitchSettings)
from mpf.core.utility_functions import Util
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.exceptions.runtime_error import MpfRuntimeError
from mpf.platforms.fast import fast_defines
from mpf.platforms.fast.fast_audio import FASTAudio
from mpf.platforms.fast.fast_dmd import FASTDMD
from mpf.platforms.fast.fast_driver import FASTDriver
from mpf.platforms.fast.fast_gi import FASTGIString
from mpf.platforms.fast.fast_io_board import FastIoBoard
from mpf.platforms.fast.fast_led import (FASTRGBLED, FASTLEDChannel,
                                         FASTExpLED)
from mpf.platforms.fast.fast_light import FASTMatrixLight
from mpf.platforms.fast.fast_port_detector import FastPortDetector
from mpf.platforms.fast.fast_segment_display import FASTSegmentDisplay
from mpf.platforms.fast.fast_servo import FastServo
from mpf.platforms.fast.fast_switch import FASTSwitch
# pylint: disable-msg=too-many-instance-attributes
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.platforms.system11 import System11Driver, System11OverlayPlatform


class FastHardwarePlatform(ServoPlatform, LightsPlatform, DmdPlatform,
                           SegmentDisplayPlatform,
                           System11OverlayPlatform):

    """Platform class for the FAST Pinball hardware."""

    __slots__ = ["config", "configured_ports", "machine_type", "is_retro",
                "serial_connections", "fast_rgb_leds", "fast_exp_leds", "fast_segs",
                "exp_boards_by_address", "exp_boards_by_name", "exp_breakout_boards",
                "exp_breakouts_with_leds", "hw_switch_data", "new_switch_data",
                "io_boards", "io_boards_by_name", "switches_initialized",
                "drivers_initialized"]

    port_types = ['net', 'exp', 'aud', 'dmd', 'rgb', 'seg', 'emu']

    def __init__(self, machine):
        """Initialize FAST hardware platform.

        Args:
        ----
            machine: The main ``MachineController`` instance.
        """
        super().__init__(machine)

        self.config = self.machine.config_validator.validate_config("fast", self.machine.config['fast'])
        self._configure_device_logging_and_debug("FAST", self.config, url_base='https://fastpinball.com/mpf/error')  # TODO

        self.configured_ports = list()

        for port_type in self.port_types:
            if self.config[port_type]:
                self.configured_ports.append(port_type)

        try:
            self.machine_type = self.config["net"]["controller"]
        except KeyError:
            self.machine_type = 'no_net'

        if self.machine_type in ['sys11', 'wpc89', 'wpc95']:
            self.debug_log("Configuring the FAST Controller for Retro driver board")
            self.is_retro = True
        elif self.machine_type in ['neuron', 'nano']:
            self.debug_log("Configuring FAST Controller for FAST I/O boards.")
            self.is_retro = False
        elif self.machine_type == 'no_net':
            pass
        else:
            self.raise_config_error(f'Unknown machine_type "{self.machine_type}" configured fast.', 6)

        # Most FAST platforms don't use ticks, but System11 does
        self.features['tickless'] = self.machine_type != 'sys11'
        self.features['max_pulse'] = 25500

        self.serial_connections = dict()
        self.fast_rgb_leds = dict()
        self.fast_exp_leds = dict()
        self.fast_segs = list()
        self.exp_boards_by_address = dict()  # k: EE address, v: FastExpansionBoard instances
        self.exp_boards_by_name = dict()  # k: str name, v: FastExpansionBoard instances
        self.exp_breakout_boards = dict()  # k: EEB address, v: FastBreakoutBoard instances
        self.exp_breakouts_with_leds = set()
        self.hw_switch_data = {i: 0 for i in range(112)}
        self.new_switch_data = asyncio.Event()  # Used to signal when we have updated switch data
        self.io_boards = dict()     # type: Dict[int, FastIoBoard]  # TODO move to NET communicator(s) classes?
        self.io_boards_by_name = dict()     # type: Dict[str, FastIoBoard]
        self.switches_initialized = False
        self.drivers_initialized = False

    def get_info_string(self):
        """Dump info strings about attached FAST hardware."""
        info_string = ""

        for port in sorted(self.serial_connections.keys()):
            info_string += f"{port.upper()}: {self.serial_connections[port].remote_model} v{self.serial_connections[port].remote_firmware}\n"

        info_string += "\nI/O Boards:\n"
        for board in self.io_boards.values():
            info_string += board.get_description_string() + "\n"
        return info_string

    async def initialize(self):
        """initialize platform."""
        # self.machine.events.add_async_handler('machine_reset_phase_1', self.soft_reset)
        self.machine.events.add_async_handler('init_phase_1', self.soft_reset)
        self.machine.events.add_handler('init_phase_3', self._start_communicator_tasks)
        self.machine.events.add_handler('machine_reset_phase_2', self._init_complete)
        await self._connect_to_hardware()

    async def soft_reset(self, **kwargs):
        """Soft reset the FAST controller.

        Used to reset / sync / verify all hardware configurations. This command does not perform a
        hard reset of the boards, rather it queries the boards for their current configuration and
        reapplies (with warnings) any configs that are out of sync.

        This command runs during the init_phase_1 phase, and then skips the reset phases, then runs
        again on subsequent resets during the machine_reset_phase_1 phase.
        """
        del kwargs
        self.debug_log("Soft resetting FAST platform.")

        for comm in self.serial_connections.values():
            await comm.soft_reset()

    def _init_complete(self, **kwargs):
        del kwargs
        # Runs on init_phase_2 and moves soft_reset() from init_phase_1 to machine_reset_phase_1
        # We need the soft_reset() to run earlier on boot, but then at reset from there on out
        self.machine.events.remove_handler(self.soft_reset)
        self.machine.events.add_async_handler('machine_reset_phase_1', self.soft_reset)

    def stop(self):
        """Stop platform and close connections."""

        # TODO move all this into the comm classes
        if not self.unit_test:  # Only do this with real hardware TODO better way to check?
            for conn in self.serial_connections.values():
                # clear out whatever's in the send queues

                # TODO register a diverter callback which just swallows all messages
                # Then set the diverter and clear the queue

                for _ in range(conn.send_queue.qsize()):
                    conn.send_queue.get_nowait()
                    conn.send_queue.task_done()
                # conn.msg_diverter.set()

        for conn in self.serial_connections.values():
            conn.stopping()

        # wait 100ms for the messages to be sent
        if not self.unit_test:
            self.machine.clock.loop.run_until_complete(asyncio.sleep(.1))

        for port, connection in self.serial_connections.items():
            if connection:
                connection.stop()
                self.serial_connections[port] = None

        self.serial_connections = dict()

    def _start_communicator_tasks(self, **kwargs):  # init_phase_3
        del kwargs
        for comm in self.serial_connections.values():
            comm.start_tasks()

    def __repr__(self):
        """Return str representation."""
        return '[FAST Platform Interface]'

    def register_io_board(self, board):  # TODO move to NET communicator(s) classes?
        """Register a FAST I/O Board.

        Args:
        ----
            board: 'mpf.platform.fast.fast_io_board.FastIoBoard' to register
        """
        if board.node_id in self.io_boards:
            raise AssertionError("Duplicate node_id")
        self.io_boards[board.node_id] = board
        self.io_boards_by_name[board.name] = board

    def register_expansion_board(self, board):  # TODO move to EXP communicator(s) classes?
        """Register an Expansion board."""
        if board.address in self.exp_boards_by_address:
            raise AssertionError("Duplicate expansion board address")
        self.exp_boards_by_address[board.address] = board
        self.exp_boards_by_name[board.name] = board

    def register_breakout_board(self, board):  # TODO move to EXP communicator(s) classes?
        """Register a Breakout board."""
        if board.address in self.exp_breakout_boards:
            raise AssertionError("Duplicate breakout board address")
        self.exp_breakout_boards[board.address] = board

    def register_led_board(self, board):  # TODO move to EXP communicator(s) classes?
        """Register a Breakout board that has LEDs."""
        self.exp_breakouts_with_leds.add(board.address[:3])

    async def _connect_to_hardware(self):  # TODO move to class methods?
        """Connect to each port from the config."""

        await self._check_for_autodetect()

        for port in self.configured_ports:

            config = self.config[port]

            if port == 'net':
                if config['controller'] == 'neuron':
                    from mpf.platforms.fast.communicators.net_neuron import \
                        FastNetNeuronCommunicator
                    communicator = FastNetNeuronCommunicator(platform=self, processor=port, config=config)
                elif config['controller'] == 'nano':
                    from mpf.platforms.fast.communicators.net_nano import \
                        FastNetNanoCommunicator
                    communicator = FastNetNanoCommunicator(platform=self, processor=port, config=config)
                elif config['controller'] in ['sys11', 'wpc89', 'wpc95']:
                    from mpf.platforms.fast.communicators.net_retro import \
                        FastNetRetroCommunicator
                    communicator = FastNetRetroCommunicator(platform=self, processor=port, config=config)
                else:
                    raise AssertionError("Unknown controller type")  # TODO better error
                self.serial_connections['net'] = communicator

            elif port == 'exp':
                from mpf.platforms.fast.communicators.exp import \
                    FastExpCommunicator
                communicator = FastExpCommunicator(platform=self, processor=port,config=config)
                self.serial_connections['exp'] = communicator
            elif port == 'seg':
                from mpf.platforms.fast.communicators.seg import \
                    FastSegCommunicator
                communicator = FastSegCommunicator(platform=self, processor=port,config=config)
                self.serial_connections['seg'] = communicator
            elif port == 'aud':
                from mpf.platforms.fast.communicators.aud import \
                    FastAudCommunicator
                communicator = FastAudCommunicator(platform=self, processor=port,config=config)
                self.serial_connections['aud'] = communicator
            elif port == 'dmd':
                from mpf.platforms.fast.communicators.dmd import \
                    FastDmdCommunicator
                communicator = FastDmdCommunicator(platform=self, processor=port,config=config)
                self.serial_connections['dmd'] = communicator
            elif port == 'emu':
                from mpf.platforms.fast.communicators.emu import \
                    FastEmuCommunicator
                communicator = FastEmuCommunicator(platform=self, processor=port,config=config)
                self.serial_connections['emu'] = communicator
            elif port == 'rgb':
                from mpf.platforms.fast.communicators.rgb import \
                    FastRgbCommunicator
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

    async def _check_for_autodetect(self):
        # Figures out which processors need to be autodetected and then runs the autodetect process
        autodetect_processors = list()
        hardcoded_ports = list()

        for processor in self.port_types:
            try:
                for port in self.config[processor]['port']:
                    if port == 'auto':
                        autodetect_processors.append(processor)
                    else:
                        hardcoded_ports.append(port)
            except KeyError:
                pass

        if not autodetect_processors:
            return

        detector = FastPortDetector(platform=self, autodetect_processors=autodetect_processors,
                                                  hardcoded_ports=hardcoded_ports)

        await detector.detect_ports()

    async def get_hw_switch_states(self, query_hw=False):
        """Return a dict of hw switch states.

        If query_hw is True, will re-query the hardware for the current switch states. Otherwise it will just return
        the last cached value.
        """

        # If the switches have not been initialized then their states are garbage, so don't bother
        if self.switches_initialized and query_hw:
            self.new_switch_data.clear()
            await self.serial_connections['net'].update_switches_from_hardware()
            await self.new_switch_data.wait()  # Wait here until we have updated switch data

        return self.hw_switch_data

    def _parse_driver_number(self, number):
        # Accepts FAST driver number string (is3208-1) and returns the driver index (0-based int)

        try:
            board_str, driver_str = number.split("-")

        except ValueError as e:  # If there's no dash, assume it's a driver number
            return int(number, 16)

        try:
            board = self.io_boards_by_name[board_str]
        except KeyError:
            raise AssertionError(f"I/O Board {board_str} does not exist for driver {number}")

        driver = int(driver_str)

        if board.driver_count <= driver:
            raise AssertionError(f"I/O Board {board} only has drivers 0-{board.driver_count-1}. Driver value {driver} is not valid.")

        index = board.start_driver + driver

        if index + 1 > self.serial_connections['net'].MAX_DRIVERS:
            raise AssertionError(f"I/O Board {board} driver {driver} is out of range. This would be driver {index + 1} but this platform supports a max of {self.serial_connections['net'].MAX_DRIVERS} drivers.")

        return index

    def configure_driver(self, config: DriverConfig, number: str, platform_config: dict) -> FASTDriver:
        """Configure a driver.

        Args:
        ----
            config: Driver config.
            number: string number entry from config (e.g. 'io3208-0)
            platform_settings: Platform specific settings.

        Returns: Driver object
        """

        if not self.serial_connections['net']:
            raise AssertionError('A request was made to configure a FAST '
                                 'driver, but no connection to a NET processor'
                                 'is available')

        if not number:
            raise AssertionError("Driver needs a number")

        # For a Retro Controller, look up the driver number
        if self.is_retro:
            try:
                index = int(fast_defines.RETRO_DRIVER_MAP[number.upper()], 16)
            except KeyError:
                self.raise_config_error(f"Could not find Retro driver {number}", 1)

        # If we have FAST I/O boards, parse the config into a FAST hex driver number
        elif self.machine_type in ['nano', 'neuron']:
            index = self._parse_driver_number(number)

        else:
            raise AssertionError("Invalid machine type: {self.machine_type}")

        driver = self.serial_connections['net'].drivers[index]  # contains all drivers on the board
        # platform.drivers is empty at this point
        driver.set_initial_config(config, platform_config)

        return driver

    async def configure_servo(self, number: str, config: dict) -> FastServo:
        """Configure a servo.

        Args:
        ----
            number: Number of servo
            config: Dict of config settings.

        Returns: Servo object.
        """
        # TODO consolidate with similar code in configure_light()
        number = number.lower()
        parts = number.split("-")

        exp_board = self.exp_boards_by_name[parts[0]]

        try:
            _, port = parts
            breakout_id = '0'
        except ValueError:
            _, breakout_id, port = parts
            breakout_id = breakout_id.strip('b')

        brk_board = exp_board.breakouts[breakout_id]

        # verify this board support servos
        assert int(port) <= int(brk_board.features['servo_ports'])  # TODO should this be stored as an int?

        config.update(self.machine.config_validator.validate_config('fast_servos', config['platform_settings']))
        del config['platform_settings']

        return FastServo(brk_board, port, config)

    def _parse_switch_number(self, number):
        try:
            board_str, switch_str = number.split("-")
        except ValueError as e:
            total_switches = 0
            for board_obj in self.io_boards.values():
                total_switches += board_obj.switch_count
            index = Util.int_to_hex_string(number)

            if int(index, 16) >= total_switches:
                raise AssertionError(f"Switch {int(index, 16)} does not exist. Only "
                                     f"{total_switches} switches found. Switch number: {number}") from e

            return index

        try:
            board = self.io_boards_by_name[board_str]
        except KeyError:
            raise AssertionError(f"Board {board_str} does not exist for switch {number}")

        switch = int(switch_str)

        if board.switch_count <= switch:
            raise AssertionError(f"Board {board} only has switches 0-{board.switch_count-1}. Switch value {switch} is not valid.")

        return Util.int_to_hex_string(board.start_switch + switch)

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

        switch = self.serial_connections['net'].switches[int(number, 16)]
        switch.set_initial_config(config, platform_config)

        return switch

    def configure_light(self, number, subtype, config, platform_settings) -> LightPlatformInterface:
        """Configure light in platform."""

        # number will have the trailing -X representing the chanel. Typically -0, -1, -2 for RGB LEDs

        del platform_settings

        if subtype == "gi":
            return FASTGIString(number, self.serial_connections['net'], self.machine,
                                int(1 / self.config['net']['gi_hz'] * 1000))
        if subtype == "matrix":
            return FASTMatrixLight(number, self.serial_connections['net'], self.machine,
                                   int(1 / self.config['net']['lamp_hz'] * 1000), self)
        if not subtype or subtype == "led":
            # TODO refactor and split into EXP and RGB communicators
            parts, channel = number.lower().rsplit('-', 1)  # make everything lowercase and strip trailing channel number
            parts = parts.split('-')  # split into board name, (breakout), port, led

            if parts[0] in self.exp_boards_by_name:
                # this is an expansion board LED
                exp_board = self.exp_boards_by_name[parts[0]]

                try:
                    _, port, led = parts
                    breakout = str((int(port) - 1) // 4)  # assume 4 LED ports per breakout, could change to a lookup
                    port = str((int(port) - 1) % 4 + 1)  # ports are always 1-4 so figure out if the printed port on the board is 5-8
                except ValueError:
                    _, breakout, port, led = parts
                    breakout = breakout.strip('b')

                try:
                    brk_board = exp_board.breakouts[breakout]
                except KeyError:
                    raise AssertionError(f'Board {exp_board} does not have a configuration entry for Breakout {breakout}')  # TODO change to mpf config exception

                index = self.port_idx_to_hex(port, led, 32, config.name)
                this_led_number = f'{brk_board.address}{index}'

                # this code runs once for each channel, so it will be called 3x per LED which
                # is why we check this here
                if this_led_number not in self.fast_exp_leds:
                    self.fast_exp_leds[this_led_number] = FASTExpLED(this_led_number, exp_board.config['led_fade_time'], self)

                fast_led_channel = FASTLEDChannel(self.fast_exp_leds[this_led_number], channel)
                self.fast_exp_leds[this_led_number].add_channel(int(channel), fast_led_channel)

                return fast_led_channel

            try:
                number = self.port_idx_to_hex(parts[0], parts[1], 64)
            except IndexError:
                number = f'{int(parts[0]):02X}' # this is a legacy LED number as an int

            if number not in self.fast_rgb_leds:
                try:
                    self.fast_rgb_leds[number] = FASTRGBLED(number, self)
                except KeyError:
                    # This number is not valid
                    raise ConfigFileError(f"Invalid LED number: {'_'.join(parts)}", 3, self.log.name)

            fast_led_channel = FASTLEDChannel(self.fast_rgb_leds[number], channel)
            self.fast_rgb_leds[number].add_channel(int(channel), fast_led_channel)

            return fast_led_channel

        raise AssertionError("Unknown subtype {}".format(subtype))

    def port_idx_to_hex(self, port, device_num, devices_per_port, name=None):
        """Converts port number and LED index into the proper FAST hex number.

        port: the LED port number printed on the board.
        device_num: LED position in the change, First LED is 1. No zeros.
        devices_per_port: number of LEDs per port. Typically 32.
        """
        port = int(port)
        device_num = int(device_num)

        if device_num < 1:
            raise AssertionError(f"Device number {device_num} is not valid for device {name}. The first device in the change should be 1, not 0")

        if port < 1:
            raise AssertionError(f"Port {port} is not valid for device {device_num}")

        if device_num > devices_per_port:
            if name:
                self.raise_config_error(f"Device number {device_num} exceeds the number of devices per port ({devices_per_port}) "
                                        f"for LED {name}", 8)  # TODO get a final error code
            else:
                raise AssertionError(f"Device number {device_num} exceeds the number of devices per port ({devices_per_port})")

        port_offset = ((port - 1) * devices_per_port)
        device_num = device_num - 1
        return f'{(port_offset + device_num):02X}'

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse light channels from number string."""
        if subtype == "gi":
            if self.is_retro:  # translate matrix/map number to FAST GI number
                try:
                    number = fast_defines.RETRO_GI_MAP[str(number).upper()]
                except KeyError:
                    self.raise_config_error(f"Could not find GI {number}", 3)
            else:
                number = Util.int_to_hex_string(number)

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
                number = Util.int_to_hex_string(number)

            return [
                {
                    "number": number
                }
            ]
        if not subtype or subtype == "led":

            return [
                {"number": f"{number}-0"},
                {"number": f"{number}-1"},
                {"number": f"{number}-2"},
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

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit rule on driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse continues. Typically used for
        autofire coils such as pop bumpers.

        FAST Driver Mode 10 or 70, depending on settings
        """

        coil.hw_driver.set_hardware_rule(None, enable_switch, coil)
        # TODO currently this will just use whatever the current mode is. Should we do some math and force a mode?

    def set_delayed_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings, delay_ms: int):
        """Set pulse on hit and release rule to driver.

        When a switch is hit and a certain delay passed it pulses a driver.
        When the switch is released the pulse continues.
        Typically used for kickbacks.

        FAST Driver Mode 30
        """
        coil.hw_driver.set_hardware_rule('30', enable_switch, coil, delay_ms=delay_ms)

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and release rule to driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse is canceled. Typically used on
        the main coil for dual coil flippers without eos switch.

        FAST Driver Mode 18 (with pwm2_power = 00)
        """

        # Force hold to None which is needed with this rule
        coil.hold_settings = None
        coil.hw_driver.set_hardware_rule('18', enable_switch, coil)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and release rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver gets disabled. Typically used for single coil flippers.

        FAST Driver Mode 18 (with pwm2_power != 00)
        """
        # coil.hw_driver.set_pulse_on_hit_and_enable_and_release_rule(enable_switch, coil)
        coil.hw_driver.set_hardware_rule('18', enable_switch, coil)

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                      eos_switch: SwitchSettings, coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver.

        Pulses a driver when a switch is hit. When the switch is released
        the pulse is canceled and the driver gets disabled. When the eos_switch is hit the pulse is canceled
        and the driver becomes disabled. Typically used on the main coil for dual-wound coil flippers with eos switch.

        FAST Driver Mode 75
        """
        del repulse_settings  # TODO do we want to implement software repulse?
        # If enabled, set a switch rule to look for EOS being open and flipper button closed and manually pulse?
        off_switch = eos_switch.hw_switch.hw_number

        coil.hw_driver.set_hardware_rule('75', enable_switch, coil, off_switch=off_switch)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver becomes disabled. When the eos_switch is hit the pulse is canceled
        and the driver becomes enabled (likely with PWM).
        Typically used on the coil for single-wound coil flippers with eos switch.

        FAST Driver Mode 20
        """

        coil.hw_driver.set_hardware_rule('20', enable_switch, coil, eos_switch=eos_switch, repulse_settings=repulse_settings)

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

        driver.clear_autofire()
