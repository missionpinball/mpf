"""FAST hardware platform.

Contains the hardware interface and drivers for the FAST Pinball platform
hardware, including the FAST Core and WPC controllers as well as FAST I/O
boards.
"""

import logging
import time
from distutils.version import StrictVersion
from copy import deepcopy

try:
    import serial
    serial_imported = True
except ImportError:
    serial_imported = False
    serial = None

from mpf.platforms.fast import fast_defines
from mpf.platforms.fast.fast_driver import FASTDriver
from mpf.platforms.fast.fast_gi import FASTGIString
from mpf.platforms.fast.fast_led import FASTDirectLED
from mpf.platforms.fast.fast_light import FASTMatrixLight
from mpf.platforms.fast.fast_switch import FASTSwitch
from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface

from mpf.devices.switch import Switch
from mpf.core.platform import ServoPlatform, MatrixLightsPlatform, GiPlatform, DmdPlatform, LedPlatform, \
    SwitchPlatform, DriverPlatform
from mpf.core.utility_functions import Util

# Minimum firmware versions needed for this module
DMD_MIN_FW = '0.88'
NET_MIN_FW = '0.88'
RGB_MIN_FW = '0.87'
IO_MIN_FW = '0.87'

# DMD_LATEST_FW = '0.88'
# NET_LATEST_FW = '0.90'
# RGB_LATEST_FW = '0.88'
# IO_LATEST_FW = '0.89'


# pylint: disable-msg=too-many-instance-attributes
class HardwarePlatform(ServoPlatform, MatrixLightsPlatform, GiPlatform,
                       DmdPlatform, LedPlatform, SwitchPlatform,
                       DriverPlatform):

    """Platform class for the FAST hardware controller.

    Args:
        machine: The main ``MachineController`` instance.
    """

    def __init__(self, machine):
        """Initialise fast hardware platform."""
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger('FAST')
        self.log.debug("Configuring FAST hardware.")

        if not serial_imported:
            raise AssertionError('Could not import "pySerial". This is '
                                 'required for the FAST platform interface')

        self.features['tickless'] = True

        self.dmd_connection = None
        self.net_connection = None
        self.rgb_connection = None
        self.connection_threads = set()
        self.fast_leds = set()
        self.flag_led_tick_registered = False
        self.config = None
        self.machine_type = None
        self.hw_switch_data = None

        # todo verify this list
        self.fast_commands = {'ID': self.receive_id,  # processor ID
                              'WX': self.receive_wx,  # watchdog
                              'NI': self.receive_ni,  # node ID
                              'RX': self.receive_rx,  # RGB cmd received
                              'DX': self.receive_dx,  # DMD cmd received
                              'SX': self.receive_sx,  # sw config received
                              'LX': self.receive_lx,  # lamp cmd received
                              'PX': self.receive_px,  # segment cmd received
                              'SA': self.receive_sa,  # all switch states
                              '/N': self.receive_nw_open,    # nw switch open
                              '-N': self.receive_nw_closed,  # nw switch closed
                              '/L': self.receive_local_open,    # local sw open
                              '-L': self.receive_local_closed,  # local sw cls
                              'WD': self.receive_wd,  # watchdog
                              }

    def initialize(self):
        """Initialise platform."""
        self.config = self.machine.config['fast']
        self.machine.config_validator.validate_config("fast", self.config)

        if self.config['debug']:
            self.debug = True

        self.machine_type = (
            self.machine.config['hardware']['driverboards'].lower())

        if self.machine_type == 'wpc':
            self.debug_log("Configuring the FAST Controller for WPC driver "
                           "board")
        else:
            self.debug_log("Configuring FAST Controller for FAST IO boards.")

        self._connect_to_hardware()

        if 'config_number_format' not in self.machine.config['fast']:
            self.machine.config['fast']['config_number_format'] = 'int'

        self.machine.clock.schedule_interval(self._update_watchdog, self.config['watchdog'] / 2000)

    def stop(self):
        """Stop platform and close connections."""
        for connection in self.connection_threads:
            connection.stop()

    def __repr__(self):
        return '<Platform.FAST>'

    def _update_watchdog(self, dt):
        del dt
        self.net_connection.send('WD:' + str(hex(self.config['watchdog']))[2:])

    def process_received_message(self, msg: str):
        """Send an incoming message from the FAST controller to the proper method for servicing.

        Args:
            msg: messaged which was received
        """
        if msg[2:3] == ':':
            cmd = msg[0:2]
            payload = msg[3:].replace('\r', '')
        else:
            self.log.warning("Received malformed message: %s", msg)
            return

        # Can't use try since it swallows too many errors for now
        if cmd in self.fast_commands:
            self.fast_commands[cmd](payload)
        else:
            self.log.warning("Received unknown serial command? %s. (This is ok"
                             " to ignore for now while the FAST platform is in "
                             "development)", msg)

    def _connect_to_hardware(self):
        """Connect to each port from the config.

        This process will cause the connection threads to figure out which processor they've connected to
        and to register themselves.
        """
        for port in self.config['ports']:
            self.connection_threads.add(SerialCommunicator(
                machine=self.machine, platform=self, port=port,
                baud=self.config['baud']))

    def register_processor_connection(self, name: str, communicator):
        """Register processor.

        Once a communication link has been established with one of the
        processors on the FAST board, this method lets the communicator let MPF
        know which processor it's talking to.

        This is a separate method since we don't know which processor is on
        which serial port ahead of time.

        Args:
            communicator: communicator object
            name: name of processor
        """
        if name == 'DMD':
            self.dmd_connection = communicator
        elif name == 'NET':
            self.net_connection = communicator
        elif name == 'RGB':
            self.rgb_connection = communicator
            self.rgb_connection.send('RF:0')
            self.rgb_connection.send('RA:000000')  # turn off all LEDs
            self.rgb_connection.send('RF:{}'.format(
                Util.int_to_hex_string(self.config['hardware_led_fade_time'])))

    def update_leds(self, dt):
        """Update all the LEDs connected to a FAST controller.

        This is done once per game loop for efficiency (i.e. all LEDs are sent as a single
        update rather than lots of individual ones).

        Also, every LED is updated every loop, even if it doesn't change. This
        is in case some interference causes a LED to change color. Since we
        update every loop, it will only be the wrong color for one tick.

        Args:
            dt: time since last call
        """
        del dt
        msg = 'RS:' + ','.join(["%s%s" % (led.number, led.current_color)
                                for led in self.fast_leds])
        self.rgb_connection.send(msg)

    def get_hw_switch_states(self):
        """Return initial hardware states."""
        self.hw_switch_data = None
        self.net_connection.send('SA:')

        self.tick(0.01)
        while not self.hw_switch_data:
            time.sleep(.01)
            self.machine.clock.tick()
            self.tick(.01)

        return self.hw_switch_data

    def receive_id(self, msg):
        """Ignore command."""
        pass

    def receive_wx(self, msg):
        """Ignore command."""
        pass

    def receive_ni(self, msg):
        """Ignore command."""
        pass

    def receive_rx(self, msg):
        """Ignore command."""
        pass

    def receive_dx(self, msg):
        """Ignore command."""
        pass

    def receive_sx(self, msg):
        """Ignore command."""
        pass

    def receive_lx(self, msg):
        """Ignore command."""
        pass

    def receive_px(self, msg):
        """Ignore command."""
        pass

    def receive_wd(self, msg):
        """Ignore command."""
        pass

    def receive_nw_open(self, msg):
        """Process network switch open.

        Args:
            msg: switch number
        """
        self.machine.switch_controller.process_switch_by_num(state=0,
                                                             num=(msg, 1),
                                                             platform=self)

    def receive_nw_closed(self, msg):
        """Process network switch closed.

        Args:
            msg: switch number
        """
        self.machine.switch_controller.process_switch_by_num(state=1,
                                                             num=(msg, 1),
                                                             platform=self)

    def receive_local_open(self, msg):
        """Process local switch open.

        Args:
            msg: switch number
        """
        self.machine.switch_controller.process_switch_by_num(state=0,
                                                             num=(msg, 0),
                                                             platform=self)

    def receive_local_closed(self, msg):
        """Process local switch closed.

        Args:
            msg: switch number
        """
        self.machine.switch_controller.process_switch_by_num(state=1,
                                                             num=(msg, 0),
                                                             platform=self)

    def receive_sa(self, msg):
        """Receive all switch states.

        Args:
            msg: switch states as bytearray
        """
        self.debug_log("Received SA: %s", msg)

        hw_states = dict()

        num_local, local_states, num_nw, nw_states = msg.split(',')
        del num_local
        del num_nw

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

    def _convert_number_from_config(self, number):
        if self.config['config_number_format'] == 'int':
            return Util.int_to_hex_string(number)
        else:
            return Util.normalize_hex_string(number)

    def configure_driver(self, config: dict) -> FASTDriver:
        """Configure a driver.

        Args:
            config: Driver config.

        Returns: Driver object
        """
        # dont modify the config. make a copy
        config = deepcopy(config)

        if not self.net_connection:
            raise AssertionError('A request was made to configure a FAST '
                                 'driver, but no connection to a NET processor'
                                 'is available')

        if not config['number']:
            raise AssertionError("Driver needs a number")

        # If we have WPC driver boards, look up the driver number
        if self.machine_type == 'wpc':
            config['number'] = fast_defines.wpc_driver_map.get(
                config['number'].upper())

            if ('connection' in config and
                    config['connection'].lower() == 'network'):
                config['connection'] = 1
            else:
                config['connection'] = 0  # local driver (default for WPC)

        # If we have FAST IO boards, we need to make sure we have hex strings
        elif self.machine_type == 'fast':

            config['number'] = self._convert_number_from_config(config['number'])

            # Now figure out the connection type
            if ('connection' in config and
                    config['connection'].lower() == 'local'):
                config['connection'] = 0
            else:
                config['connection'] = 1  # network driver (default for FAST)

        else:
            raise AssertionError("Invalid machine type: {}".format(
                self.machine_type))

        return FASTDriver(config, self.net_connection.send, self.machine)

    def configure_servo(self, config: dict):
        """Configure a servo.

        Args:
            config: Servo config.

        Returns: Servo object.
        """
        number = self._convert_number_from_config(config['number'])

        return FastServo(number, self.net_connection)

    def configure_switch(self, config: dict) -> FASTSwitch:
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
            config: Switch config.

        Returns: Switch object.
        """
        # dont modify the config. make a copy
        config = deepcopy(config)

        if not config['number']:
            raise AssertionError("Switch needs a number")

        if not self.net_connection:
            raise AssertionError("A request was made to configure a FAST "
                                 "switch, but no connection to a NET processor"
                                 "is available")

        if self.machine_type == 'wpc':  # translate switch num to FAST switch
            config['number'] = fast_defines.wpc_switch_map.get(
                str(config['number']).upper())
            if 'connection' not in config:
                config['connection'] = 0  # local switch (default for WPC)
            else:
                config['connection'] = 1  # network switch

        elif self.machine_type == 'fast':
            if 'connection' not in config:
                config['connection'] = 1  # network switch (default for FAST)
            else:
                config['connection'] = 0  # local switch

            try:
                config['number'] = self._convert_number_from_config(config['number'])
            except ValueError:
                raise AssertionError("Could not parse switch number %s. Seems "
                                     "to be not a valid switch number for the"
                                     "FAST platform.", config['number'])

        # convert the switch number into a tuple which is:
        # (switch number, connection)
        config['number'] = (config['number'], config['connection'])

        self.debug_log("FAST Switch hardware tuple: %s", config['number'])

        switch = FASTSwitch(config=config,
                            sender=self.net_connection.send,
                            platform=self)

        return switch

    def configure_led(self, config: dict, channels: int):
        """Configure a WS2812 LED.

        Args:
            config: LED config.
            channels: Number of channels (3 for RGB)

        Returns: LED object.

        """
        if channels > 3:
            raise AssertionError("FAST only supports RGB LEDs")
        if not self.rgb_connection:
            raise AssertionError('A request was made to configure a FAST LED, '
                                 'but no connection to an LED processor is '
                                 'available')

        if not self.flag_led_tick_registered:
            # Update leds every frame
            self.machine.clock.schedule_interval(self.update_leds,
                                                 1 / self.machine.config['mpf']['default_led_hw_update_hz'])
            self.flag_led_tick_registered = True

        # if the LED number is in <channel> - <led> format, convert it to a
        # FAST hardware number
        if '-' in str(config['number']):
            num = str(config['number']).split('-')
            number = Util.int_to_hex_string((int(num[0]) * 64) + int(num[1]))
        else:
            number = self._convert_number_from_config(config['number'])

        this_fast_led = FASTDirectLED(number)
        self.fast_leds.add(this_fast_led)

        return this_fast_led

    def configure_gi(self, config: dict) -> FASTGIString:
        """Configure a GI.

        Args:
            config: GI config.

        Returns: GI object.
        """
        # TODO: Add support for driver-based GI strings

        if not self.net_connection:
            raise AssertionError('A request was made to configure a FAST GI, '
                                 'but no connection to a NET processor is '
                                 'available')

        if self.machine_type == 'wpc':  # translate switch num to FAST switch
            number = fast_defines.wpc_gi_map.get(str(config['number']).upper())
        else:
            number = self._convert_number_from_config(config['number'])

        return FASTGIString(number, self.net_connection.send)

    def configure_matrixlight(self, config: dict) -> FASTMatrixLight:
        """Configure a matrix light.

        Args:
            config: Matrix light config.

        Returns: Matrix light object.
        """
        if not self.net_connection:
            raise AssertionError('A request was made to configure a FAST '
                                 'matrix light, but no connection to a NET '
                                 'processor is available')

        if self.machine_type == 'wpc':  # translate number to FAST light num
            number = fast_defines.wpc_light_map.get(str(config['number']).upper())
        else:
            number = self._convert_number_from_config(config['number'])

        return FASTMatrixLight(number, self.net_connection.send)

    def configure_dmd(self):
        """Configure a hardware DMD connected to a FAST controller."""
        if not self.dmd_connection:
            raise AssertionError("A request was made to configure a FAST DMD, "
                                 "but no connection to a DMD processor is "
                                 "available.")

        self.machine.bcp.register_dmd(
            FASTDMD(self.machine, self.dmd_connection.send).update)

        return

    @classmethod
    def get_coil_config_section(cls):
        """Return coil config section."""
        return "fast_coils"

    @classmethod
    def get_switch_config_section(cls):
        """Return switch config section."""
        return "fast_switches"

    @classmethod
    def get_coil_overwrite_section(cls):
        """Return coil overwrite section."""
        return "fast_coil_overwrites"

    def validate_switch_overwrite_section(self, switch: Switch, config_overwrite: dict) -> dict:
        """Validate switch overwrite section for platform.

        Args:
            switch: switch to validate
            config_overwrite: overwrite config to validate

        Returns: Validated config.
        """
        if ("debounce" in config_overwrite and
                switch.config['debounce'] != "auto" and
                switch.config['debounce'] != config_overwrite['debounce']):
            raise AssertionError("Cannot overwrite debounce for switch %s for"
                                 "FAST interface", switch.name)

        config_overwrite = super().validate_switch_overwrite_section(
            switch, config_overwrite)
        return config_overwrite

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and release rule to driver."""
        self.debug_log("Setting Pulse on hit and release HW Rule. Switch: %s,"
                       "Driver: %s", enable_switch.hw_switch.number,
                       coil.hw_driver.number)

        driver = coil.hw_driver

        cmd = '{}{},{},{},18,{},{},00,{},00'.format(
            driver.get_config_cmd(),
            coil.hw_driver.number,
            driver.get_control_for_cmd(enable_switch),
            enable_switch.hw_switch.number[0],
            driver.get_pulse_ms_for_cmd(coil),
            driver.get_pwm1_for_cmd(coil),
            driver.get_recycle_ms_for_cmd(coil))

        driver.autofire = True
        enable_switch.hw_switch.configure_debounce(enable_switch.config)
        self.debug_log("Writing hardware rule: %s", cmd)

        self.net_connection.send(cmd)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        """Set pulse on hit and enable and release and disable rule on driver."""
        # Potential command from Dave:
        # Command
        # [DL/DN]:<DRIVER_ID>,<CONTROL>,<SWITCH_ID_ON>,<75>,<SWITCH_ID_OFF>,<Driver On Time1>,<Driver On Time2 X 100mS>,
        # <PWM2><Driver Rest Time><CR>#
        # SWITCH_ID_ON would be the flipper switch
        # SWITCH_ID_OFF would be the EOS switch.
        # So for the flipper, Driver On Time1 will = the maximum time the coil can be held on if the EOS fails.
        # Driver On Time2 X 100mS would not be used for a flipper, so set it to 0.
        # And PWM2 should be left on full 0xff unless you need less power for some reason.
        # No release so far :-(
        self.debug_log("Setting Pulse on hit and release with HW Rule. Switch:"
                       "%s, Driver: %s", enable_switch.hw_switch.number,
                       coil.hw_driver.number)

        # map this to pulse without eos for now
        # TODO: implement correctly
        del disable_switch
        self.set_pulse_on_hit_and_release_rule(enable_switch, coil)

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        """Set pulse on hit rule on driver."""
        self.debug_log("Setting Pulse on hit and release HW Rule. Switch: %s,"
                       "Driver: %s", enable_switch.hw_switch.number,
                       coil.hw_driver.number)

        driver = coil.hw_driver

        cmd = '{}{},{},{},10,{},{},00,00,{}'.format(
            driver.get_config_cmd(),
            coil.hw_driver.number,
            driver.get_control_for_cmd(enable_switch),
            enable_switch.hw_switch.number[0],
            driver.get_pulse_ms_for_cmd(coil),
            driver.get_pwm1_for_cmd(coil),
            driver.get_recycle_ms_for_cmd(coil))

        driver.autofire = True
        enable_switch.hw_switch.configure_debounce(enable_switch.config)
        self.debug_log("Writing hardware rule: %s", cmd)

        self.net_connection.send(cmd)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and enable and relase rule on driver."""
        self.debug_log("Setting Pulse on hit and enable and release HW Rule. "
                       "Switch: %s, Driver: %s",
                       enable_switch.hw_switch.number, coil.hw_driver.number)

        driver = coil.hw_driver
        if (driver.get_pwm1_for_cmd(coil) == "ff" and
                driver.get_pwm2_for_cmd(coil) == "ff" and
                not coil.config['allow_enable']):

            # todo figure how to show the friendly name of this driver
            raise AssertionError("Coil {} may not be enabled at 100% without "
                                 "allow_enabled or pwm settings".format(coil.hw_driver.number))

        cmd = '{}{},{},{},18,{},{},{},{},00'.format(
            driver.get_config_cmd(),
            coil.hw_driver.number,
            driver.get_control_for_cmd(enable_switch),
            enable_switch.hw_switch.number[0],
            driver.get_pulse_ms_for_cmd(coil),
            driver.get_pwm1_for_cmd(coil),
            driver.get_pwm2_for_cmd(coil),
            driver.get_recycle_ms_for_cmd(coil))

        driver.autofire = True
        enable_switch.hw_switch.configure_debounce(enable_switch.config)
        self.debug_log("Writing hardware rule: %s", cmd)

        self.net_connection.send(cmd)

    def clear_hw_rule(self, switch, coil):
        """Clear a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        Args:
            switch: The switch whose rule you want to clear.
            coil: The coil whose rule you want to clear.

        """
        self.debug_log("Clearing HW Rule for switch: %s, coils: %s",
                       switch.hw_switch.number, coil.hw_driver.number)

        # TODO: check that the rule is switch + coil and not another switch + this coil

        driver = coil.hw_driver

        cmd = '{}{},81'.format(driver.get_config_cmd(), coil.hw_driver.number)

        coil.autofire = None

        self.debug_log("Clearing hardware rule: %s", cmd)

        self.net_connection.send(cmd)


class FastServo(ServoPlatformInterface):

    """A servo in the FAST platform."""

    def __init__(self, number, net_connection):
        """Initialise servo."""
        self.number = number
        self.net_connection = net_connection

    def go_to_position(self, position):
        """Set a servo position."""
        if position < 0 or position > 1:
            raise AssertionError("Position has to be between 0 and 1")

        # convert from [0,1] to [0, 255]
        position_numeric = int(position * 255)

        cmd = 'XO:{},{}'.format(
            self.number,
            Util.int_to_hex_string(position_numeric))

        self.net_connection.send(cmd)


class FASTDMD(object):

    """Object for a FAST DMD."""

    def __init__(self, machine, sender):
        """Initialise DMD."""
        self.machine = machine
        self.send = sender

        # Clear the DMD
        # todo

    def update(self, data: bytes):
        """Update data on the DMD.

        Args:
            data: bytes to send to DMD
        """
        self.send(data)


# pylint: disable-msg=too-many-instance-attributes
class SerialCommunicator(object):

    """Handles the serial communication to the FAST platform."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, machine, platform, port, baud):
        """Initialise communicator."""
        self.machine = machine
        self.platform = platform
        self.dmd = False

        self.remote_processor = None
        self.remote_model = None
        self.remote_firmware = 0.0

        self.received_msg = b''

        self.ignored_messages = ['RX:P',  # RGB Pass
                                 'SN:P',  # Network Switch pass
                                 'SN:F',  #
                                 'SL:P',  # Local Switch pass
                                 'SL:F',
                                 'LX:P',  # Lamp pass
                                 'PX:P',  # Segment pass
                                 'DN:P',  # Network driver pass
                                 'DN:F',
                                 'DL:P',  # Local driver pass
                                 'DL:F',  # Local driver fail
                                 'XX:F',  # Unrecognized command?
                                 'R1:F',
                                 'L1:P',
                                 'GI:P',
                                 'TL:P',
                                 'TN:P',
                                 'XO:P',  # Servo/Daughterboard Pass
                                 'XX:U',
                                 'XX:N',
                                 ]

        self.platform.log.info("Connecting to %s at %sbps", port, baud)
        self.serial_connection = serial.Serial(port=port, baudrate=baud,
                                               timeout=1, writeTimeout=0)

        self.identify_connection()
        self.platform.register_processor_connection(self.remote_processor, self)
        self._start_threads()

    def identify_connection(self):
        """Identifie which processor this serial connection is talking to."""
        # keep looping and wait for an ID response

        msg = ''

        # send enough dummy commands to clear out any buffers on the FAST
        # board that might be waiting for more commands
        self.serial_connection.write(((' ' * 256) + '\r').encode())

        while True:
            self.platform.debug_log("Sending 'ID:' command to port '%s'",
                                    self.serial_connection.name)
            self.serial_connection.write('ID:\r'.encode())
            msg = self.serial_connection.read_until(b'\r').decode()
            if msg.startswith('ID:'):
                break

        # examples of ID responses
        # ID:DMD FP-CPU-002-1 00.87
        # ID:NET FP-CPU-002-2 00.85
        # ID:RGB FP-CPU-002-2 00.85

        try:
            self.remote_processor, self.remote_model, self.remote_firmware = (
                msg[3:].split())
        except ValueError:
            self.remote_processor, self.remote_model, = msg[3:].split()

        self.platform.debug_log("Received ID acknowledgement. Processor: %s, "
                                "Board: %s, Firmware: %s",
                                self.remote_processor, self.remote_model,
                                self.remote_firmware)

        if self.remote_processor == 'DMD':
            min_version = DMD_MIN_FW
            # latest_version = DMD_LATEST_FW
            self.dmd = True
        elif self.remote_processor == 'NET':
            min_version = NET_MIN_FW
            # latest_version = NET_LATEST_FW
        else:
            min_version = RGB_MIN_FW
            # latest_version = RGB_LATEST_FW

        if StrictVersion(min_version) > StrictVersion(self.remote_firmware):
            raise AssertionError('Firmware version mismatch. MPF requires'
                                 ' the {} processor to be firmware {}, but yours is {}'.
                                 format(self.remote_processor, min_version, self.remote_firmware))

        if self.remote_processor == 'NET' and self.platform.machine_type == 'fast':
            self.query_fast_io_boards()

    def query_fast_io_boards(self):
        """Querie the NET processor to see if any FAST IO boards are connected.

        If so, queries the IO boards to log them and make sure they're the  proper firmware version.
        """
        self.platform.debug_log('Querying FAST IO boards...')

        firmware_ok = True

        for board_id in range(8):
            self.serial_connection.write('NN:{0}\r'.format(board_id).encode())
            msg = self.serial_connection.read_until(b'\r').decode()
            if msg.startswith('NN:'):

                node_id, model, fw, dr, sw, _, _, _, _, _, _ = msg.split(',')
                node_id = node_id[3:]
                model = model.strip()

                # I don't know what character it returns for a non-existent
                # board, I just know they're all the same
                if model == len(model) * model[0]:
                    model = False

                if model:
                    self.platform.debug_log('Fast IO Board {0}: Model: {1}, '
                                            'Firmware: {2}, Switches: {3}, '
                                            'Drivers: {4}'.format(node_id,
                                                                  model, fw,
                                                                  int(sw, 16),
                                                                  int(dr, 16)))

                    if StrictVersion(IO_MIN_FW) > str(fw):
                        self.platform.log.critical("Firmware version mismatch. MPF "
                                                   "requires the IO boards to be firmware {0}, but "
                                                   "your Board {1} ({2}) is v{3}".format(IO_MIN_FW, node_id, model, fw))
                        firmware_ok = False

        if not firmware_ok:
            raise AssertionError("Exiting due to IO board firmware mismatch")

    def _start_threads(self):
        self.serial_connection.timeout = None
        self.machine.clock.schedule_socket_read_callback(self.serial_connection, self._receiver)

    def stop(self):
        """Stop and shut down this serial connection."""
        self.serial_connection.close()
        self.serial_connection = None  # child threads stop when this is None

        # todo clear the hw?

    def send(self, msg):
        """Send a message to the remote processor over the serial connection.

        Args:
            msg: String of the message you want to send. THe <CR> character will
                be added automatically.

        """
        debug = self.platform.config['debug']
        if self.dmd:
            self.serial_connection.write(b'BM:' + msg)
            if debug:
                self.platform.log.debug("Send: %s", msg.decode())

        else:
            self.serial_connection.write(msg.encode() + b'\r')
            if debug:
                self.platform.log.debug("Send: %s", msg)

    def _receiver(self):
        debug = self.platform.config['debug']
        self.received_msg += self.serial_connection.read_all()

        while True:
            pos = self.received_msg.find(b'\r')

            # no more complete messages
            if pos == -1:
                break

            msg = self.received_msg[:pos]
            self.received_msg = self.received_msg[pos + 1:]

            if not msg:
                continue

            if debug:
                self.platform.log.debug("Received: %s", msg.decode())

            if msg.decode() not in self.ignored_messages:
                self.platform.process_received_message(msg.decode())

