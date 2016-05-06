"""Contains the hardware interface and drivers for the FAST Pinball platform
hardware, including the FAST Core and WPC controllers as well as FAST I/O
boards.
"""

import logging
import time
import sys
import threading
import queue
import traceback
import io
from distutils.version import StrictVersion
from copy import deepcopy

from mpf.core.platform import ServoPlatform, MatrixLightsPlatform, GiPlatform, DmdPlatform, LedPlatform, \
    SwitchPlatform, DriverPlatform
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.rgb_led_platform_interface import RGBLEDPlatformInterface
from mpf.platforms.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface
from mpf.platforms.interfaces.gi_platform_interface import GIPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface

try:
    import serial
    serial_imported = True
except ImportError:
    serial_imported = False
    serial = None

# Minimum firmware versions needed for this module
DMD_MIN_FW = '0.88'
NET_MIN_FW = '0.88'
RGB_MIN_FW = '0.87'
IO_MIN_FW = '0.87'

DMD_LATEST_FW = '0.88'
NET_LATEST_FW = '0.90'
RGB_LATEST_FW = '0.88'
IO_LATEST_FW = '0.89'


class HardwarePlatform(ServoPlatform, MatrixLightsPlatform, GiPlatform,
                       DmdPlatform, LedPlatform, SwitchPlatform,
                       DriverPlatform):
    """Platform class for the FAST hardware controller.

    Args:
        machine: The main ``MachineController`` instance.

    """

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger('FAST')
        self.log.info("Configuring FAST hardware.")

        if not serial_imported:
            raise AssertionError('Could not import "pySerial". This is '
                                 'required for the FAST platform interface')

        self.dmd_connection = None
        self.net_connection = None
        self.rgb_connection = None
        self.fast_nodes = list()
        self.connection_threads = set()
        self.receive_queue = queue.Queue()
        self.fast_leds = set()
        self.flag_led_tick_registered = False
        self.fast_io_boards = list()
        self.waiting_for_switch_data = False
        self.config = None
        self.watchdog_command = None
        self.machine_type = None
        self.hw_switch_data = None

        self.wpc_switch_map = {

            # WPC   HEX    DEC
            'S11': '00',  # 00
            'S12': '01',  # 01
            'S13': '02',  # 02
            'S14': '03',  # 03
            'S15': '04',  # 04
            'S16': '05',  # 05
            'S17': '06',  # 06
            'S18': '07',  # 07

            'S21': '08',  # 08
            'S22': '09',  # 09
            'S23': '0A',  # 10
            'S24': '0B',  # 11
            'S25': '0C',  # 12
            'S26': '0D',  # 13
            'S27': '0E',  # 14
            'S28': '0F',  # 15

            'S31': '10',  # 16
            'S32': '11',  # 17
            'S33': '12',  # 18
            'S34': '13',  # 19
            'S35': '14',  # 20
            'S36': '15',  # 21
            'S37': '16',  # 22
            'S38': '17',  # 23

            'S41': '18',  # 24
            'S42': '19',  # 25
            'S43': '1A',  # 26
            'S44': '1B',  # 27
            'S45': '1C',  # 28
            'S46': '1D',  # 29
            'S47': '1E',  # 30
            'S48': '1F',  # 31

            'S51': '20',  # 32
            'S52': '21',  # 33
            'S53': '22',  # 34
            'S54': '23',  # 35
            'S55': '24',  # 36
            'S56': '25',  # 37
            'S57': '26',  # 38
            'S58': '27',  # 39

            'S61': '28',  # 40
            'S62': '29',  # 41
            'S63': '2A',  # 42
            'S64': '2B',  # 43
            'S65': '2C',  # 44
            'S66': '2D',  # 45
            'S67': '2E',  # 46
            'S68': '2F',  # 47

            'S71': '30',  # 48
            'S72': '31',  # 49
            'S73': '32',  # 50
            'S74': '33',  # 51
            'S75': '34',  # 52
            'S76': '35',  # 53
            'S77': '36',  # 54
            'S78': '37',  # 55

            'S81': '38',  # 56
            'S82': '39',  # 57
            'S83': '3A',  # 58
            'S84': '3B',  # 59
            'S85': '3C',  # 60
            'S86': '3D',  # 61
            'S87': '3E',  # 62
            'S88': '3F',  # 63

            'S91': '40',  # 64
            'S92': '41',  # 65
            'S93': '42',  # 66
            'S94': '43',  # 67
            'S95': '44',  # 68
            'S96': '45',  # 69
            'S97': '46',  # 70
            'S98': '47',  # 71

            'S101': '48',  # 72
            'S102': '49',  # 73
            'S103': '4A',  # 74
            'S104': '4B',  # 75
            'S105': '4C',  # 76
            'S106': '4D',  # 77
            'S107': '4E',  # 78
            'S108': '4F',  # 79

            # Directs
            'SD1': '50',  # 80
            'SD2': '51',  # 81
            'SD3': '52',  # 82
            'SD4': '53',  # 83
            'SD5': '54',  # 84
            'SD6': '55',  # 85
            'SD7': '56',  # 86
            'SD8': '57',  # 87

            # DIP switches
            'DIP1': '58',  # 88
            'DIP2': '59',  # 89
            'DIP3': '5A',  # 90
            'DIP4': '5B',  # 91
            'DIP5': '5C',  # 92
            'DIP6': '5D',  # 93
            'DIP7': '5E',  # 94
            'DIP8': '5F',  # 95

            # Fliptronics
            'SF1': '60',  # 96
            'SF2': '61',  # 97
            'SF3': '62',  # 98
            'SF4': '63',  # 99
            'SF5': '64',  # 100
            'SF6': '65',  # 101
            'SF7': '66',  # 102
            'SF8': '67',  # 103
        }

        self.wpc_light_map = {
            'L11': '00', 'L12': '01', 'L13': '02', 'L14': '03',
            'L15': '04', 'L16': '05', 'L17': '06', 'L18': '07',
            'L21': '08', 'L22': '09', 'L23': '0A', 'L24': '0B',
            'L25': '0C', 'L26': '0D', 'L27': '0E', 'L28': '0F',
            'L31': '10', 'L32': '11', 'L33': '12', 'L34': '13',
            'L35': '14', 'L36': '15', 'L37': '16', 'L38': '17',
            'L41': '18', 'L42': '19', 'L43': '1A', 'L44': '1B',
            'L45': '1C', 'L46': '1D', 'L47': '1E', 'L48': '1F',
            'L51': '20', 'L52': '21', 'L53': '22', 'L54': '23',
            'L55': '24', 'L56': '25', 'L57': '26', 'L58': '27',
            'L61': '28', 'L62': '29', 'L63': '2A', 'L64': '2B',
            'L65': '2C', 'L66': '2D', 'L67': '2E', 'L68': '2F',
            'L71': '30', 'L72': '31', 'L73': '32', 'L74': '33',
            'L75': '34', 'L76': '35', 'L77': '36', 'L78': '37',
            'L81': '38', 'L82': '39', 'L83': '3A', 'L84': '3B',
            'L85': '3C', 'L86': '3D', 'L87': '3E', 'L88': '3F',
        }

        self.wpc_driver_map = {
            'C01': '00', 'C02': '01', 'C03': '02', 'C04': '03',
            'C05': '04', 'C06': '05', 'C07': '06', 'C08': '07',
            'C09': '08', 'C10': '09', 'C11': '0A', 'C12': '0B',
            'C13': '0C', 'C14': '0D', 'C15': '0E', 'C16': '0F',
            'C17': '10', 'C18': '11', 'C19': '12', 'C20': '13',
            'C21': '14', 'C22': '15', 'C23': '16', 'C24': '17',
            'C25': '18', 'C26': '19', 'C27': '1A', 'C28': '1B',
            'C29': '1C', 'C30': '1D', 'C31': '1E', 'C32': '1F',
            'C33': '24', 'C34': '25', 'C35': '26', 'C36': '27',
            'FLRM': '20', 'FLRH': '21', 'FLLM': '22', 'FLLH': '23',
            'FURM': '24', 'FURH': '25', 'FULM': '26', 'FULH': '27',
            'C37': '28', 'C38': '29', 'C39': '2A', 'C40': '2B',
            'C41': '2C', 'C42': '2D', 'C43': '2E', 'C44': '2F',
        }

        self.wpc_gi_map = {
            'G01': '00', 'G02': '01', 'G03': '02', 'G04': '03',
            'G05': '04', 'G06': '05', 'G07': '06', 'G08': '07',
        }

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
        self.config = self.machine.config['fast']
        self.machine.config_validator.validate_config("fast", self.config)

        self.watchdog_command = 'WD:' + str(hex(self.config['watchdog']))[2:]

        self.machine_type = (
            self.machine.config['hardware']['driverboards'].lower())

        if self.machine_type == 'wpc':
            self.log.info("Configuring the FAST Controller for WPC driver "
                          "board")
        else:
            self.log.info("Configuring FAST Controller for FAST IO boards.")

        self._connect_to_hardware()

        # todo this is a hack since the above call blocks it screws up the
        # clock. Need to fix this for real

        self.machine.clock.tick()

        if 'config_number_format' not in self.machine.config['fast']:
            self.machine.config['fast']['config_number_format'] = 'int'

    def __repr__(self):
        return '<Platform.FAST>'

    def process_received_message(self, msg):
        """Sends an incoming message from the FAST controller to the proper
        method for servicing.
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
        # Connect to each port from the config. This process will cause the
        # connection threads to figure out which processor they've connected to
        # and to register themselves.
        for port in self.config['ports']:
            self.connection_threads.add(SerialCommunicator(
                machine=self.machine, platform=self, port=port,
                baud=self.config['baud'], send_queue=queue.Queue(),
                receive_queue=self.receive_queue))

    def register_processor_connection(self, name, communicator):
        """Once a communication link has been established with one of the
        processors on the FAST board, this method lets the communicator let MPF
        know which processor it's talking to.

        This is a separate method since we don't know which processor is on
        which serial port ahead of time.
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
        """Updates all the LEDs connected to a FAST controller. This is done
        once per game loop for efficiency (i.e. all LEDs are sent as a single
        update rather than lots of individual ones).

        Also, every LED is updated every loop, even if it doesn't change. This
        is in case some interference causes a LED to change color. Since we
        update every loop, it will only be the wrong color for one tick.
        """
        del dt
        msg = 'RS:' + ','.join(["%s%s" % (led.number, led.current_color)
                                for led in self.fast_leds])
        self.rgb_connection.send(msg)

    def get_hw_switch_states(self):
        self.hw_switch_data = None
        self.net_connection.send('SA:')

        self.tick(0.01)
        while not self.hw_switch_data:
            time.sleep(.01)
            self.tick(0.01)

        return self.hw_switch_data

    def receive_id(self, msg):
        pass

    def receive_wx(self, msg):
        pass

    def receive_ni(self, msg):
        pass

    def receive_rx(self, msg):
        pass

    def receive_dx(self, msg):
        pass

    def receive_sx(self, msg):
        pass

    def receive_lx(self, msg):
        pass

    def receive_px(self, msg):
        pass

    def receive_wd(self, msg):
        pass

    def receive_nw_open(self, msg):
        self.machine.switch_controller.process_switch_by_num(state=0,
                                                             num=(msg, 1))

    def receive_nw_closed(self, msg):
        self.machine.switch_controller.process_switch_by_num(state=1,
                                                             num=(msg, 1))

    def receive_local_open(self, msg):
        self.machine.switch_controller.process_switch_by_num(state=0,
                                                             num=(msg, 0))

    def receive_local_closed(self, msg):
        self.machine.switch_controller.process_switch_by_num(state=1,
                                                             num=(msg, 0))

    def receive_sa(self, msg):

        self.log.debug("Received SA: %s", msg)

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

    def configure_driver(self, config):
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
            config['number'] = self.wpc_driver_map.get(
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

    def configure_switch(self, config):
        """Configures the switch object for a FAST Pinball controller.

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
            config['number'] = self.wpc_switch_map.get(
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

        self.log.debug("FAST Switch hardware tuple: %s", config['number'])

        switch = FASTSwitch(config=config,
                            sender=self.net_connection.send,
                            platform=self)

        return switch

    def configure_led(self, config, channels):
        if channels > 3:
            raise AssertionError("FAST only supports RGB LEDs")
        if not self.rgb_connection:
            raise AssertionError('A request was made to configure a FAST LED, '
                                 'but no connection to an LED processor is '
                                 'available')

        if not self.flag_led_tick_registered:
            # Update leds every frame
            self.machine.clock.schedule_interval(self.update_leds, 0)
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

    def configure_gi(self, config):
        # TODO: Add support for driver-based GI strings

        if not self.net_connection:
            raise AssertionError('A request was made to configure a FAST GI, '
                                 'but no connection to a NET processor is '
                                 'available')

        if self.machine_type == 'wpc':  # translate switch num to FAST switch
            number = self.wpc_gi_map.get(str(config['number']).upper())
        else:
            number = Util.int_to_hex_string(config['number'])

        return FASTGIString(number, self.net_connection.send)

    def configure_matrixlight(self, config):
        if not self.net_connection:
            raise AssertionError('A request was made to configure a FAST '
                                 'matrix light, but no connection to a NET '
                                 'processor is available')

        if self.machine_type == 'wpc':  # translate number to FAST light num
            number = self.wpc_light_map.get(str(config['number']).upper())
        else:
            number = self._convert_number_from_config(config['number'])

        return FASTMatrixLight(number, self.net_connection.send)

    def configure_dmd(self):
        """Configures a hardware DMD connected to a FAST controller."""

        if not self.dmd_connection:
            raise AssertionError("A request was made to configure a FAST DMD, "
                                 "but no connection to a DMD processor is "
                                 "available.")

        self.machine.bcp.register_dmd(
            FASTDMD(self.machine, self.dmd_connection.send).update)

        return

    def tick(self, dt):
        while not self.receive_queue.empty():
            self.process_received_message(self.receive_queue.get(False))

        self.net_connection.send(self.watchdog_command)

    @classmethod
    def get_coil_config_section(cls):
        return "fast_coils"

    @classmethod
    def get_switch_config_section(cls):
        return "fast_switches"

    @classmethod
    def get_coil_overwrite_section(cls):
        return "fast_coil_overwrites"

    def validate_switch_overwrite_section(self, switch, config_overwrite):
        if ("debounce" in config_overwrite and
                switch.config['debounce'] != "auto" and
                switch.config['debounce'] != config_overwrite['debounce']):
            raise AssertionError("Cannot overwrite debounce for switch %s for"
                                 "FAST interface", switch.name)

        config_overwrite = super().validate_switch_overwrite_section(
            switch, config_overwrite)
        return config_overwrite

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        self.log.debug("Setting Pulse on hit and release HW Rule. Switch: %s,"
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
        self.log.debug("Writing hardware rule: %s", cmd)

        self.net_connection.send(cmd)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
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
        self.log.debug("Setting Pulse on hit and release with HW Rule. Switch:"
                       "%s, Driver: %s", enable_switch.hw_switch.number,
                       coil.hw_driver.number)

        # map this to pulse without eos for now
        # TODO: implement correctly
        del disable_switch
        self.set_pulse_on_hit_and_release_rule(enable_switch, coil)

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        self.log.debug("Setting Pulse on hit and release HW Rule. Switch: %s,"
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
        self.log.debug("Writing hardware rule: %s", cmd)

        self.net_connection.send(cmd)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        self.log.debug("Setting Pulse on hit and enable and release HW Rule. "
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
        self.log.debug("Writing hardware rule: %s", cmd)

        self.net_connection.send(cmd)

    def clear_hw_rule(self, switch, coil):
        """Clears a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        Args:
            switch: The switch whose rule you want to clear.
            coil: The coil whose rule you want to clear.

        """
        self.log.debug("Clearing HW Rule for switch: %s, coils: %s",
                       switch.hw_switch.number, coil.hw_driver.number)

        # TODO: check that the rule is switch + coil and not another switch + this coil

        driver = coil.hw_driver

        cmd = '{}{},81'.format(driver.get_config_cmd(), coil.hw_driver.number)

        coil.autofire = None

        self.log.debug("Clearing hardware rule: %s", cmd)

        self.net_connection.send(cmd)

    def servo_go_to_position(self, number, position):
        """Sets a servo position. """

        if number < 0:
            raise AssertionError("invalid number")

        if position < 0 or position > 1:
            raise AssertionError("Position has to be between 0 and 1")

        # convert from [0,1] to [0, 255]
        position_numeric = int(position * 255)

        cmd = 'XO:{},{}'.format(
            Util.int_to_hex_string(number),
            Util.int_to_hex_string(position_numeric))

        self.net_connection.send(cmd)


class FASTSwitch(object):

    def __init__(self, config, sender, platform):
        self.config = config
        self.log = logging.getLogger('FASTSwitch')
        self.number = config['number']
        self.connection = config['number'][1]
        self.send = sender
        self.platform = platform
        self._configured_debounce = False
        self.configure_debounce(config)

    def configure_debounce(self, config):
        if config['debounce'] in ("normal", "auto"):
            debounce_open = self.platform.config['default_normal_debounce_open']
            debounce_close = self.platform.config['default_normal_debounce_close']
        else:
            debounce_open = self.platform.config['default_quick_debounce_open']
            debounce_close = self.platform.config['default_quick_debounce_close']

        if self.connection:
            cmd = 'SN:'
        else:
            cmd = 'SL:'

        new_setting = (debounce_open, debounce_close)
        if new_setting == self._configured_debounce:
            return

        self._configured_debounce = new_setting

        cmd = '{}{},01,{},{}'.format(
            cmd,
            self.number[0],
            Util.int_to_hex_string(debounce_open),
            Util.int_to_hex_string(debounce_close))

        self.send(cmd)


class FASTDriver(DriverPlatformInterface):
    """Base class for drivers connected to a FAST Controller.

    """

    def __init__(self, config, sender, machine):
        """

        """

        self.autofire = None
        self.machine = machine
        self.driver_settings = dict()
        self.config = config

        self.log = logging.getLogger('FASTDriver')

        # Number is already normalized FAST hex string at this point
        self.number = config['number']
        self.send = sender

        if config['connection'] == 1:
            self.driver_settings['config_cmd'] = 'DN:'
            self.driver_settings['trigger_cmd'] = 'TN:'
        else:
            self.driver_settings['config_cmd'] = 'DL:'
            self.driver_settings['trigger_cmd'] = 'TL:'

        self.log.debug("Driver Settings: %s", self.driver_settings)
        self.reset()

    def _get_pulse_ms(self, coil):
        if coil.config['pulse_ms'] is None:
            return self.machine.config['mpf']['default_pulse_ms']
        else:
            return coil.config['pulse_ms']

    def get_pulse_ms_for_cmd(self, coil):
        pulse_ms = self._get_pulse_ms(coil)
        if pulse_ms > 255:
            return "00"
        else:
            return Util.int_to_hex_string(pulse_ms)

    def get_pwm1_for_cmd(self, coil):
        if coil.config['pulse_pwm_mask']:
            pulse_pwm_mask = str(coil.config['pulse_pwm_mask'])
            if len(pulse_pwm_mask) == 32:
                return Util.bin_str_to_hex_str(pulse_pwm_mask, 8)
            elif len(pulse_pwm_mask) == 8:
                return Util.bin_str_to_hex_str(pulse_pwm_mask, 2)
            else:
                raise ValueError("pulse_pwm_mask must either be 8 or 32 bits")
        elif coil.config['pulse_power32'] is not None:
            return "ff"
        elif coil.config['pulse_power'] is not None:
            return Util.pwm8_to_hex_string(coil.config['pulse_power'])
        else:
            return "ff"

    def get_pwm2_for_cmd(self, coil):
        if coil.config['hold_pwm_mask']:
            hold_pwm_mask = str(coil.config['hold_pwm_mask'])
            if len(hold_pwm_mask) == 32:
                return Util.bin_str_to_hex_str(hold_pwm_mask, 8)
            elif len(hold_pwm_mask) == 8:
                return Util.bin_str_to_hex_str(hold_pwm_mask, 2)
            else:
                raise ValueError("hold_pwm_mask must either be 8 or 32 bits")
        elif coil.config['hold_power32'] is not None:
            return "ff"
        elif coil.config['hold_power'] is not None:
            return Util.pwm8_to_hex_string(coil.config['hold_power'])
        else:
            return "ff"

    def get_recycle_ms_for_cmd(self, coil):
        if not coil.config['recycle']:
            return "00"
        elif coil.config['recycle_ms'] is not None:
            return Util.int_to_hex_string(coil.config['recycle_ms'])
        else:
            # default recycle_ms to pulse_ms * 2
            pulse_ms = self._get_pulse_ms(coil)
            if pulse_ms * 2 > 255:
                return "FF"
            else:
                return Util.int_to_hex_string(pulse_ms * 2)

    def get_config_cmd(self):
        return self.driver_settings['config_cmd']

    def get_trigger_cmd(self):
        return self.driver_settings['trigger_cmd']

    def get_control_for_cmd(self, switch):
        control = 0x01  # Driver enabled
        if switch.invert:
            control += 0x10
        return Util.int_to_hex_string(int(control))

    def reset(self):
        """

        Resets a driver

        """
        self.log.debug("Resetting driver %s", self.driver_settings)
        # cmd = (self.get_config_cmd() +
        #        self.number +
        #        ',00,00,00')

        cmd = '{}{},00,00,00'.format(self.get_config_cmd(), self.number)

        self.send(cmd)

    def disable(self, coil):
        """Disables (turns off) this driver. """
        del coil

        # cmd = (self.get_trigger_cmd() +
        #        self.number + ',' + '02')

        cmd = '{}{},02'.format(self.get_trigger_cmd(), self.number)

        self.log.debug("Sending Disable Command: %s", cmd)
        self.send(cmd)
        self.check_auto()

    def enable(self, coil):
        """Enables (turns on) this driver. """

        if self.autofire:
            # If this driver is also configured for an autofire rule, we just
            # manually trigger it with the trigger_cmd and manual on ('03')
            # cmd = (self.get_trigger_cmd() +
            #        self.number + ',' +
            #        '03')

            cmd = '{}{},03'.format(self.get_trigger_cmd(), self.number)

            self.log.warning("Recived a command to enable this driver, but "
                             "this driver is configured with an autofire rule,"
                             " so this enable will reset that rule. We need to"
                             " change this behavior...")

        else:
            # Otherwise we send a full config command, trigger C1 (logic triggered
            # and drive now) switch ID 00, mode 18 (latched)

            if (self.get_pwm1_for_cmd(coil) == 'ff' and
                    self.get_pwm2_for_cmd(coil) == 'ff' and
                    not coil.config['allow_enable']):

                raise AssertionError("Received a command to enable this coil "
                                     "without pwm, but 'allow_enable' has not been"
                                     "set to True in this coil's configuration.")

            else:

                pulse_ms = self.get_pulse_ms_for_cmd(coil)

                cmd = '{}{},C1,00,18,{},{},{},{}'.format(
                    self.get_config_cmd(),
                    self.number,
                    pulse_ms,
                    self.get_pwm1_for_cmd(coil),
                    self.get_pwm2_for_cmd(coil),
                    self.get_recycle_ms_for_cmd(coil))

        # todo pwm32

        self.log.debug("Sending Enable Command: %s", cmd)
        self.send(cmd)
        # todo change hold to pulse with re-ups

    def pulse(self, coil, milliseconds):
        """Pulses this driver. """

        if isinstance(milliseconds, int):
            hex_ms_string = Util.int_to_hex_string(milliseconds)
        else:
            hex_ms_string = milliseconds

        if self.autofire:
            cmd = '{}{},01'.format(self.get_trigger_cmd(), self.number)

            if milliseconds:
                self.log.debug("Received command to pulse driver for %sms, but"
                               "this driver is configured with an autofire rule"
                               ", so that pulse value will be used instead.")
        else:
            cmd = '{}{},89,00,10,{},{},00,00,{}'.format(
                self.get_config_cmd(),
                self.number,
                hex_ms_string,
                self.get_pwm1_for_cmd(coil),
                self.get_recycle_ms_for_cmd(coil))

        self.log.debug("Sending Pulse Command: %s", cmd)
        self.send(cmd)
        self.check_auto()

        return Util.hex_string_to_int(hex_ms_string)

    def check_auto(self):

        if self.autofire:
            cmd = '{}{},00'.format(self.get_trigger_cmd(), self.number)

            self.log.debug("Re-enabling auto fire mode: %s", cmd)
            self.send(cmd)


class FASTGIString(GIPlatformInterface):
    def __init__(self, number, sender):
        """A FAST GI string in a WPC machine.

        TODO: Need to implement the enable_relay and control which strings are
        dimmable.
        """
        self.log = logging.getLogger('FASTGIString.0x' + str(number))
        self.number = number
        self.send = sender

    def off(self):
        self.log.debug("Turning Off GI String")
        self.send('GI:' + self.number + ',00')

    def on(self, brightness=255):
        if brightness >= 255:
            brightness = 255

        self.log.debug("Turning On GI String to brightness %s", brightness)
        # self.send('GI:' + self.number + ',' + Util.int_to_hex_string(brightness))

        self.send('GI:{},{}'.format(self.number,
                                    Util.int_to_hex_string(brightness)))


class FASTMatrixLight(MatrixLightPlatformInterface):

    def __init__(self, number, sender):
        self.log = logging.getLogger('FASTMatrixLight')
        self.number = number
        self.send = sender

    def off(self):
        """Disables (turns off) this matrix light."""
        # self.send('L1:' + self.number + ',00')
        self.send('L1:{},00'.format(self.number))

    def on(self, brightness=255):
        """Enables (turns on) this driver."""
        if brightness >= 255:
            # self.send('L1:' + self.number + ',FF')
            self.send('L1:{},FF'.format(self.number))
        elif brightness == 0:
            self.off()
        else:
            pass
            # patter rates of 10/1 through 2/9


class FASTDirectLED(RGBLEDPlatformInterface):
    """
    Represents a single RGB LED connected to the Fast hardware platform
    """
    def __init__(self, number):
        self.log = logging.getLogger('FASTLED')
        self.number = number
        self._current_color = '000000'

        # All FAST LEDs are 3 element RGB and are set using hex strings

        self.log.debug("Creating FAST RGB LED at hardware address: %s",
                       self.number)

    def color(self, color):
        """Instantly sets this LED to the color passed.

        Args:
            color: an RGBColor object
        """
        self._current_color = "{0}{1}{2}".format(hex(int(color[0]))[2:].zfill(2),
                                                 hex(int(color[1]))[2:].zfill(2),
                                                 hex(int(color[2]))[2:].zfill(2))

    @property
    def current_color(self):
        return self._current_color


class FASTDMD(object):

    def __init__(self, machine, sender):
        self.machine = machine
        self.send = sender

        # Clear the DMD
        # todo

        self.dmd_frame = bytearray()

    def update(self, data):
        self.send(data)


class SerialCommunicator(object):

    # pylint: disable-msg=too-many-arguments
    def __init__(self, machine, platform, port, baud, send_queue,
                 receive_queue):
        self.machine = machine
        self.platform = platform
        self.send_queue = send_queue
        self.receive_queue = receive_queue
        self.debug = False
        self.log = None
        self.dmd = False

        self.remote_processor = None
        self.remote_model = None
        self.remote_firmware = 0.0

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
                                 'TN:P'
                                 'XX:U',
                                 'XX:N',
                                 ]

        self.platform.log.info("Connecting to %s at %sbps", port, baud)
        self.serial_connection = serial.Serial(port=port, baudrate=baud,
                                               timeout=1, writeTimeout=0)

        self.serial_io = io.TextIOWrapper(io.BufferedRWPair(
            self.serial_connection, self.serial_connection, 1), newline='\r',
            line_buffering=True)
        # pylint: disable=W0212
        self.serial_io._CHUNK_SIZE = 1

        self.identify_connection()
        self.platform.register_processor_connection(self.remote_processor, self)
        self._start_threads()

    def identify_connection(self):
        """Identifies which processor this serial connection is talking to."""

        # keep looping and wait for an ID response

        msg = ''

        while True:
            self.platform.log.debug("Sending 'ID:' command to port '%s'",
                                    self.serial_connection.name)
            self.serial_connection.write('ID:\r'.encode())
            msg = self.serial_io.readline()  # todo timeout
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

        self.platform.log.info("Received ID acknowledgement. Processor: %s, "
                               "Board: %s, Firmware: %s", self.remote_processor,
                               self.remote_model, self.remote_firmware)

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
        """Queries the NET processor to see if any FAST IO boards are connected,
        and if so, queries the IO boards to log them and make sure they're the
        proper firmware version.

        """

        self.platform.log.debug('Querying FAST IO boards...')

        firmware_ok = True

        for board_id in range(8):
            self.serial_connection.write('NN:{0}\r'.format(board_id).encode())
            msg = self.serial_io.readline()
            if msg.startswith('NN:'):

                node_id, model, fw, dr, sw, _, _, _, _, _, _ = msg.split(',')
                node_id = node_id[3:]
                model = model.strip()

                # I don't know what character it returns for a non-existent
                # board, I just know they're all the same
                if model == len(model) * model[0]:
                    model = False

                if model:
                    self.platform.log.info('Fast IO Board {0}: Model: {1}, '
                                           'Firmware: {2}, Switches: {3}, '
                                           'Drivers: {4}'.format(node_id, model, fw, int(sw, 16), int(dr, 16)))

                    if StrictVersion(IO_MIN_FW) > str(fw):
                        self.platform.log.critical("Firmware version mismatch. MPF "
                                                   "requires the IO boards to be firmware {0}, but "
                                                   "your Board {1} ({2}) is v{3}".format(IO_MIN_FW, node_id, model, fw))
                        firmware_ok = False

        if not firmware_ok:
            raise AssertionError("Exiting due to IO board firmware mismatch")

    def _start_threads(self):

        self.serial_connection.timeout = None

        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()

        self.sending_thread = threading.Thread(target=self._sending_loop)
        self.sending_thread.daemon = True
        self.sending_thread.start()

    def stop(self):
        """Stops and shuts down this serial connection."""
        self.serial_connection.close()
        self.serial_connection = None  # child threads stop when this is None

        # todo clear the hw?

    def send(self, msg):
        """Sends a message to the remote processor over the serial connection.

        Args:
            msg: String of the message you want to send. THe <CR> character will
                be added automatically.

        """
        if self.dmd:
            self.send_queue.put(msg)
        else:
            self.send_queue.put(msg + '\r')

    def _sending_loop(self):

        debug = self.platform.config['debug']

        try:

            if self.dmd:
                while self.serial_connection:

                    data = self.send_queue.get()
                    msg = b'BM:' + data
                    self.serial_connection.write(msg)

            else:

                while self.serial_connection:
                    msg = self.send_queue.get()
                    self.serial_connection.write(msg.encode())

                    if debug:
                        self.platform.log.info("Sending: %s", msg)

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            msg = ''.join(line for line in lines)
            self.machine.crash_queue.put(msg)

    def _receive_loop(self):

        debug = self.platform.config['debug']

        if not self.dmd:

            try:
                while self.serial_connection:
                    msg = self.serial_io.readline()[:-1]  # strip the \r

                    if debug:
                        self.platform.log.info("Received: %s", msg)

                    if msg not in self.ignored_messages:
                        self.receive_queue.put(msg)

            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                lines = traceback.format_exception(exc_type, exc_value,
                                                   exc_traceback)
                msg = ''.join(line for line in lines)
                self.machine.crash_queue.put(msg)
