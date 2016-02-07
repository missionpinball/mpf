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

from mpf.core.platform import Platform
from mpf.core.config import Config
from mpf.core.utility_functions import Util
from mpf.platform.interfaces.rgb_led_platform_interface import RGBLEDPlatformInterface
from mpf.platform.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface
from mpf.platform.interfaces.gi_platform_interface import GIPlatformInterface
from mpf.platform.interfaces.driver_platform_interface import DriverPlatformInterface
from mpf.core.rgb_color import RGBColor

try:
    import serial
    serial_imported = True
except:
    serial_imported = False

# Minimum firmware versions needed for this module
DMD_MIN_FW = '0.88'
NET_MIN_FW = '0.88'
RGB_MIN_FW = '0.87'
IO_MIN_FW = '0.87'

DMD_LATEST_FW = '0.88'
NET_LATEST_FW = '0.90'
RGB_LATEST_FW = '0.88'
IO_LATEST_FW = '0.89'


class HardwarePlatform(Platform):
    """Platform class for the FAST hardware controller.

    Args:
        machine: The main ``MachineController`` instance.

    """

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger('FAST')
        self.log.info("Configuring FAST hardware.")

        if not serial_imported:
            raise AssertionError('Could not import "pySerial". This is required for '
                           'the FAST platform interface')

        # ----------------------------------------------------------------------
        # Platform-specific hardware features. WARNING: Do not edit these. They
        # are based on what the FAST hardware can and cannot do.
        self.features['max_pulse'] = 255  # todo
        self.features['hw_rule_coil_delay'] = True  # todo
        self.features['variable_recycle_time'] = True  # todo
        self.features['variable_debounce_time'] = True  # todo
        # Make the platform features available to everyone
        self.machine.config['platform'] = self.features
        # ----------------------------------------------------------------------

        self.hw_rules = dict()
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

        self.wpc_switch_map = {

        #    WPC   HEX    DEC
            'S11': '00',  #00
            'S12': '01',  #01
            'S13': '02',  #02
            'S14': '03',  #03
            'S15': '04',  #04
            'S16': '05',  #05
            'S17': '06',  #06
            'S18': '07',  #07

            'S21': '08',  #08
            'S22': '09',  #09
            'S23': '0A',  #10
            'S24': '0B',  #11
            'S25': '0C',  #12
            'S26': '0D',  #13
            'S27': '0E',  #14
            'S28': '0F',  #15

            'S31': '10',  #16
            'S32': '11',  #17
            'S33': '12',  #18
            'S34': '13',  #19
            'S35': '14',  #20
            'S36': '15',  #21
            'S37': '16',  #22
            'S38': '17',  #23

            'S41': '18',  #24
            'S42': '19',  #25
            'S43': '1A',  #26
            'S44': '1B',  #27
            'S45': '1C',  #28
            'S46': '1D',  #29
            'S47': '1E',  #30
            'S48': '1F',  #31

            'S51': '20',  #32
            'S52': '21',  #33
            'S53': '22',  #34
            'S54': '23',  #35
            'S55': '24',  #36
            'S56': '25',  #37
            'S57': '26',  #38
            'S58': '27',  #39

            'S61': '28',  #40
            'S62': '29',  #41
            'S63': '2A',  #42
            'S64': '2B',  #43
            'S65': '2C',  #44
            'S66': '2D',  #45
            'S67': '2E',  #46
            'S68': '2F',  #47

            'S71': '30',  #48
            'S72': '31',  #49
            'S73': '32',  #50
            'S74': '33',  #51
            'S75': '34',  #52
            'S76': '35',  #53
            'S77': '36',  #54
            'S78': '37',  #55

            'S81': '38',  #56
            'S82': '39',  #57
            'S83': '3A',  #58
            'S84': '3B',  #59
            'S85': '3C',  #60
            'S86': '3D',  #61
            'S87': '3E',  #62
            'S88': '3F',  #63

            'S91': '40',  #64
            'S92': '41',  #65
            'S93': '42',  #66
            'S94': '43',  #67
            'S95': '44',  #68
            'S96': '45',  #69
            'S97': '46',  #70
            'S98': '47',  #71

            'S101': '48',  #72
            'S102': '49',  #73
            'S103': '4A',  #74
            'S104': '4B',  #75
            'S105': '4C',  #76
            'S106': '4D',  #77
            'S107': '4E',  #78
            'S108': '4F',  #79

            # Directs
            'SD1': '50',  #80
            'SD2': '51',  #81
            'SD3': '52',  #82
            'SD4': '53',  #83
            'SD5': '54',  #84
            'SD6': '55',  #85
            'SD7': '56',  #86
            'SD8': '57',  #87

            # DIP switches
            'DIP1': '58',  #88
            'DIP2': '59',  #89
            'DIP3': '5A',  #90
            'DIP4': '5B',  #91
            'DIP5': '5C',  #92
            'DIP6': '5D',  #93
            'DIP7': '5E',  #94
            'DIP8': '5F',  #95

            # Fliptronics
            'SF1': '60',  #96
            'SF2': '61',  #97
            'SF3': '62',  #98
            'SF4': '63',  #99
            'SF5': '64',  #100
            'SF6': '65',  #101
            'SF7': '66',  #102
            'SF8': '67',  #103

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
                              '-L': self.receive_local_closed,  # local sw close
                              'WD': self.receive_wd,  # watchdog
                              }

    def initialize(self):
        self.config = self.machine.config['fast']
        self.machine.config_processor.process_config2("fast", self.config)

        self.watchdog_command = 'WD:' + str(hex(self.config['watchdog']))[2:]

        self.machine_type = (
            self.machine.config['hardware']['driverboards'].lower())

        if self.machine_type == 'wpc':
            self.log.info("Configuring the FAST Controller for WPC driver "
                           "board")
        else:
            self.log.info("Configuring FAST Controller for FAST IO boards.")

        self._connect_to_hardware()

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
            self.log.warning("Received unknown serial command? %s. (This is ok "
                             "to ignore for now while the FAST platform is in "
                             "development)", msg)

    def _connect_to_hardware(self):
        # Connect to each port from the config. This process will cause the
        # connection threads to figure out which processor they've connected to
        # and to register themselves.
        for port in self.config['ports']:
            self.connection_threads.add(SerialCommunicator(machine=self.machine,
                                                           platform=self, port=port, baud=self.config['baud'],
                                                           send_queue=queue.Queue(), receive_queue=self.receive_queue))

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
            self.rgb_connection.send('RF:' + Util.int_to_hex_string(self.config['hardware_led_fade_time']))

    def update_leds(self, dt):
        """Updates all the LEDs connected to a FAST controller. This is done
        once per game loop for efficiency (i.e. all LEDs are sent as a single
        update rather than lots of individual ones).

        Also, every LED is updated every loop, even if it doesn't change. This
        is in case some interference causes a LED to change color. Since we
        update every loop, it will only be the wrong color for one tick.
        """
        msg = 'RS:' + ','.join(["%s%s" % (led.number, led.current_color) for led in self.fast_leds])
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
        self.machine.switch_controller.process_switch(state=0,
                                                      num=(msg, 1))

    def receive_nw_closed(self, msg):
        self.machine.switch_controller.process_switch(state=1,
                                                      num=(msg, 1))

    def receive_local_open(self, msg):
        self.machine.switch_controller.process_switch(state=0,
                                                      num=(msg, 0))

    def receive_local_closed(self, msg):
        self.machine.switch_controller.process_switch(state=1,
                                                      num=(msg, 0))

    def receive_sa(self, msg):

        self.log.info("Received SA: %s", msg)

        hw_states = dict()

        num_local, local_states, num_nw, nw_states = msg.split(',')

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

    def configure_driver(self, config, device_type='coil'):

        if not self.net_connection:
            self.log.critical("A request was made to configure a FAST driver, "
                              "but no connection to a NET processor is "
                              "available")
            sys.exit()

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

            if self.config['config_number_format'] == 'int':
                config['number'] = Util.int_to_hex_string(config['number'])
            else:
                config['number'] = Util.normalize_hex_string(config['number'])

            # Now figure out the connection type
            if ('connection' in config and
                    config['connection'].lower() == 'local'):
                config['connection'] = 0
            else:
                config['connection'] = 1  # network driver (default for FAST)

        else:
            self.log.critical("Invalid machine type: {0{}}".format(
                self.machine_type))
            sys.exit()

        return (FASTDriver(config, self.net_connection.send, self.machine),
                (config['number'], config['connection']))

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

        if not self.net_connection:
            raise AssertionError("A request was made to configure a FAST switch, "
                              "but no connection to a NET processor is "
                              "available")

        if self.machine_type == 'wpc':  # translate switch number to FAST switch
            config['number'] = self.wpc_switch_map.get(
                                                config['number_str'].upper())
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
                if self.config['config_number_format'] == 'int':
                    config['number'] = Util.int_to_hex_string(config['number'])
                else:
                    config['number'] = Util.normalize_hex_string(config['number'])
            except ValueError:
                raise AssertionError("Could not parse switch number " + config['number'] + ". Seems to be not a "
                                     " a valid switch number for the FAST platform.")

        # convert the switch number into a tuple which is:
        # (switch number, connection)
        config['number'] = (config['number'], config['connection'])

        if not config['debounce_open']:
            config['debounce_open'] = self.config['default_debounce_open']

        if not config['debounce_close']:
            config['debounce_close'] = self.config['default_debounce_close']

        self.log.debug("FAST Switch hardware tuple: %s", config['number'])

        switch = FASTSwitch(number=config['number'],
                            debounce_open=config['debounce_open'],
                            debounce_close=config['debounce_close'],
                            sender=self.net_connection.send)

        return switch, config['number']

    def configure_led(self, config):

        if not self.rgb_connection:
            self.log.critical("A request was made to configure a FAST LED, "
                              "but no connection to an LED processor is "
                              "available")
            sys.exit()

        if not self.flag_led_tick_registered:
            # Update leds every frame
            self.machine.clock.schedule_interval(self.update_leds, 0)
            self.flag_led_tick_registered = True

        # if the LED number is in <channel> - <led> format, convert it to a
        # FAST hardware number
        if '-' in config['number_str']:
            num = config['number_str'].split('-')
            config['number'] = (int(num[0]) * 64) + int(num[1])
            self.config['config_number_format'] = 'int'
        else:
            config['number'] = str(config['number'])

        if self.config['config_number_format'] == 'int':
            config['number'] = Util.int_to_hex_string(config['number'])
        else:
            config['number'] = Util.normalize_hex_string(config['number'])

        this_fast_led = FASTDirectLED(config['number'])
        self.fast_leds.add(this_fast_led)

        return this_fast_led

    def configure_gi(self, config):
        # TODO: Add support for driver-based GI strings

        if not self.net_connection:
            self.log.critical("A request was made to configure a FAST GI, "
                              "but no connection to a NET processor is "
                              "available")
            sys.exit()

        if self.machine_type == 'wpc':  # translate switch number to FAST switch
            config['number'] = self.wpc_gi_map.get(config['number_str'].upper())

        return (FASTGIString(config['number'], self.net_connection.send),
                config['number'])

    def configure_matrixlight(self, config):

        if not self.net_connection:
            self.log.critical("A request was made to configure a FAST matrix "
                              "light, but no connection to a NET processor is "
                              "available")
            sys.exit()

        if self.machine_type == 'wpc':  # translate number to FAST light num
            config['number'] = self.wpc_light_map.get(
                                                config['number_str'].upper())
        elif self.config['config_number_format'] == 'int':
            config['number'] = Util.int_to_hex_string(config['number'])
        else:
            config['number'] = Util.normalize_hex_string(config['number'])

        return (FASTMatrixLight(config['number'], self.net_connection.send),
                config['number'])

    def configure_dmd(self):
        """Configures a hardware DMD connected to a FAST controller."""

        if not self.dmd_connection:
            self.log.warning("A request was made to configure a FAST DMD, "
                              "but no connection to a DMD processor is "
                              "available. No hardware DMD will be used.")

            return FASTDMD(self.machine, self.null_dmd_sender)

        return FASTDMD(self.machine, self.dmd_connection.send)

    def null_dmd_sender(self, *args, **kwargs):
        pass

    def tick(self, dt):
        while not self.receive_queue.empty():
            self.process_received_message(self.receive_queue.get(False))

        self.net_connection.send(self.watchdog_command)

    def write_hw_rule(self, switch_obj, sw_activity, driver_obj, driver_action,
                      disable_on_release=True, drive_now=False,
                      **driver_settings_overrides):
        """Used to write (or update) a hardware rule to the FAST controller.

        *Hardware Rules* are used to configure the hardware controller to
        automatically change driver states based on switch changes. These rules
        are completely handled by the hardware (i.e. with no interaction from
        the Python game code). They're used for things that you want to happen
        fast, like firing coils when flipper buttons are pushed, slingshots, pop
        bumpers, etc.

        You can overwrite existing hardware rules at any time to change or
        remove them.

        Args:
            switch_obj: Which switch you're creating this rule for. The
                parameter is a reference to the switch object itself.
            sw_activity: Int which specifies whether this coil should fire when
                the switch becomes active (1) or inactive (0)
            driver_obj: Driver object this rule is being set for.
            driver_action: String 'pulse' or 'hold' which describe what action
                will be applied to this driver
            drive_now: Should the hardware check the state of the switches when
                this rule is first applied, and fire the coils if they should
                be? Typically this is True, especially with flippers because you
                want them to fire if the player is holding in the buttons when
                the machine enables the flippers (which is done via several
                calls to this method.)

        """

        driver_settings = deepcopy(driver_obj.hw_driver.driver_settings)

        driver_settings.update(driver_obj.hw_driver.merge_driver_settings(
            **driver_settings_overrides))

        self.log.debug("Setting HW Rule. Switch: %s, Switch_action: %s, Driver:"
                      " %s, Driver settings: %s", switch_obj.name, sw_activity,
                      driver_obj.name, driver_settings)

        control = 0x01  # Driver enabled
        if drive_now:
            control += 0x08

        if sw_activity == 0:
            control += 0x10

        control = Util.int_to_hex_string(int(control))

        # todo need to implement disable_on_release

        if driver_action == 'pulse':
            mode = '10'                               # Mode 10 settings
            param1 = driver_settings['pulse_ms']      # initial pulse ms
            param2 = driver_settings['pwm1']          # intial pwm
            param3 = '00'                             # pulse 2 time
            param4 = '00'                             # pulse 2 pwm
            param5 = driver_settings['recycle_ms']    # recycle ms

        elif driver_action == 'hold':
            mode = '18'                               # Mode 18 settings
            param1 = driver_settings['pulse_ms']      # intiial pulse ms
            param2 = driver_settings['pwm1']          # intial pwm
            param3 = driver_settings['pwm2']          # hold pwm
            param4 = driver_settings['recycle_ms']    # recycle ms
            param5 = '00'                             # not used with Mode 18

        elif driver_action == 'timed_hold':

            # fast hold time is ms*100
            hold_value = driver_settings['activation_time']

            mode = '70'                               # Mode 70 settings
            param1 = driver_settings['pulse_ms']      # intiial pulse ms
            param2 = driver_settings['pwm1']          # intial pwm
            param3 = hold_value                       # hold time
            param4 = driver_settings['pwm2']          # hold pwm
            param5 = driver_settings['recycle_ms']    # recycle ms

        else:
            raise ValueError("Invalid driver action: '%s'. Expected 'hold', "
                             "'timed_hold', or 'pulse'" % (driver_action))

        self.hw_rules[driver_obj] = {'mode': mode,
                               'param1': param1,
                               'param2': param2,
                               'param3': param3,
                               'param4': param4,
                               'param5': param5,
                               'switch': switch_obj.number}

        cmd = (driver_settings['config_cmd'] +
               driver_obj.number[0] + ',' +
               control  + ',' +
               switch_obj.number[0] + ',' +
               mode + ',' +
               param1 + ',' +
               param2 + ',' +
               param3 + ',' +
               param4 + ',' +
               param5)

        driver_obj.autofire = cmd
        self.log.debug("Writing hardware rule: %s", cmd)

        self.net_connection.send(cmd)

    def clear_hw_rule(self, sw_name):
        """Clears a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        Args:
            sw_name: The string name of the switch whose rule you want to clear.

        """
        sw_num = self.machine.switches[sw_name].number

        # find the rule(s) based on this switch
        coils = [k for k, v in self.hw_rules.items() if v['switch'] == sw_num]

        self.log.debug("Clearing HW Rule for switch: %s %s, coils: %s", sw_name,
                       sw_num, coils)

        for coil in coils:

            del self.hw_rules[coil]

            driver_settings = coil.hw_driver.driver_settings

            cmd = (driver_settings['config_cmd'] +
                   driver_settings['number'] + ',' +
                   '81')

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

        # build command and send it
        cmd = 'XO:' + Util.int_to_hex_string(number) + ',' + Util.int_to_hex_string(position_numeric)
        self.net_connection.send(cmd)


class FASTSwitch(object):

    def __init__(self, number, debounce_open, debounce_close, sender):
        self.log = logging.getLogger('FASTSwitch')
        self.number = number[0]
        self.connection = number[1]
        self.send = sender

        if self.connection:
            cmd = 'SN:'
        else:
            cmd = 'SL:'

        debounce_open = str(hex(debounce_open))[2:]
        debounce_close = str(hex(debounce_close))[2:]

        cmd += str(self.number) + ',01,' + debounce_open + ',' + debounce_close

        self.send(cmd)


class FASTDriver(DriverPlatformInterface):
    """Base class for drivers connected to a FAST Controller.

    """

    def __init__(self, config, sender, machine):
        """

        """

        self.autofire = None
        self.config = dict()
        self.driver_settings = self.create_driver_settings(machine, **config)

        self.driver_settings['mode'] = '10'     # pulsed

        self.log = logging.getLogger('FASTDriver')

        # Number is already normalized FAST hex string at this point
        self.driver_settings['number'] = config['number']
        self.send = sender

        if config['connection'] == 1:
            self.driver_settings['config_cmd'] = 'DN:'
            self.driver_settings['trigger_cmd'] = 'TN:'
        else:
            self.driver_settings['config_cmd'] = 'DL:'
            self.driver_settings['trigger_cmd'] = 'TL:'

        self.driver_settings.update(self.merge_driver_settings(**config))

        self.log.debug("Driver Settings: %s", self.driver_settings)
        self.reset()

    def reset(self):
        """

        Resets a driver

        """
        self.log.debug("Reseting driver %s", self.driver_settings)
        cmd = (self.driver_settings['config_cmd'] +
               self.driver_settings['number'] +
               ',00,00,00')
        self.send(cmd)

    def create_driver_settings(self, machine, pulse_ms=None, **kwargs):
        return_dict = dict()
        if pulse_ms is None:
            pulse_ms = machine.config['mpf']['default_pulse_ms']

        try:
            return_dict['allow_enable'] = kwargs['allow_enable']
        except KeyError:
            return_dict['allow_enable'] = False

        return_dict['pulse_ms'] = Util.int_to_hex_string(pulse_ms)
        return_dict['pwm1'] = 'ff'
        return_dict['pwm2'] = 'ff'
        return_dict['recycle_ms'] = '00'

        return return_dict

    def merge_driver_settings(self,
                            pulse_ms=None,
                            pwm_on_ms=None,
                            pwm_off_ms=None,
                            pulse_power=None,
                            hold_power=None,
                            pulse_power32=None,
                            hold_power32=None,
                            pulse_pwm_mask=None,
                            hold_pwm_mask=None,
                            recycle_ms=None,
                            activation_time=None,
                            **kwargs
                            ):

        if pwm_on_ms:
            raise ValueError("The setting 'pwm_on_ms' is not valid with the "
                             "FAST platform. Use a hold_power or hold_pwm_mask"
                             " instead.")
        if pwm_off_ms:
            raise ValueError("The setting 'pwm_off_ms' is not valid with the "
                             "FAST platform. Use a hold_power or hold_pwm_mask"
                             " instead.")

        if pulse_power32:
            raise NotImplementedError('"pulse_power32" has not been '
                                      'implemented yet')

        if hold_power32:
            raise NotImplementedError('"hold_power32" has not been '
                                      'implemented yet')

        return_dict = dict()
        return_dict['pwm32'] = None

        if activation_time is not None:
            if activation_time > 25500:
                raise ValueError('Max FAST timed_hold time is 25.5s')

            # FAST activation times are ms * 100
            return_dict['activation_time'] = str(activation_time / 100)

        if recycle_ms is not None:
            return_dict['recycle_ms'] = (Util.int_to_hex_string(recycle_ms))

        if pulse_ms is not None:
            return_dict['pulse_ms'] = Util.int_to_hex_string(pulse_ms)

        if pulse_pwm_mask:
            pulse_pwm_mask = str(pulse_pwm_mask)
            if len(pulse_pwm_mask) == 32:
                return_dict['pwm1'] = Util.bin_str_to_hex_str(pulse_pwm_mask, 8)
            elif len(pulse_pwm_mask) == 8:
                return_dict['pwm1'] = Util.bin_str_to_hex_str(pulse_pwm_mask, 2)
            else:
                raise ValueError("pulse_pwm_mask must either be 8 or 32 bits")
        elif pulse_power32 is not None:
            return_dict['pwm32']  = Util.pwm32_to_hex_string(pulse_power32)
        elif pulse_power is not None:
            return_dict['pwm1']  = Util.pwm8_to_hex_string(pulse_power)

        if hold_pwm_mask:
            hold_pwm_mask = str(hold_pwm_mask)
            if len(hold_pwm_mask) == 32:
                return_dict['pwm2'] = Util.bin_str_to_hex_str(hold_pwm_mask, 8)
            elif len(hold_pwm_mask) == 8:
                return_dict['pwm2'] = Util.bin_str_to_hex_str(hold_pwm_mask, 2)
            else:
                raise ValueError("hold_pwm_mask must either be 8 or 32 bits")
        elif hold_power32 is not None:
            return_dict['pwm32'] = Util.pwm32_to_hex_string(hold_power32)
        elif hold_power is not None:
            return_dict['pwm2'] = Util.pwm8_to_hex_string(hold_power)

        return return_dict

    def disable(self):
        """Disables (turns off) this driver. """
        cmd = (self.driver_settings['trigger_cmd'] +
               self.driver_settings['number'] + ',' + '02')

        self.log.debug("Sending Disable Command: %s", cmd)
        self.send(cmd)
        self.check_auto()

    def enable(self):
        """Enables (turns on) this driver. """
        if self.autofire:
            # If this driver is also configured for an autofire rule, we just
            # manually trigger it with the trigger_cmd and manual on ('03')
            cmd = (self.driver_settings['trigger_cmd'] +
                   self.driver_settings['number'] + ',' +
                   '03')
            self.log.warning("Recived a command to enable this driver, but "
                             "this driver is configured with an autofire rule,"
                             " so this enable will reset that rule. We need to"
                             " change this behavior...")

        else:
            # Otherwise we send a full config command, trigger C1 (logic triggered
            # and drive now) switch ID 00, mode 18 (latched)

            if (self.driver_settings['pwm1'] == 'ff' and
                    self.driver_settings['pwm2'] == 'ff' and
                    not ('allow_enable' in self.driver_settings and
                    self.driver_settings['allow_enable'])):

                raise AssertionError("Received a command to enable this coil "
                                 "without pwm, but 'allow_enable' has not been"
                                 "set to True in this coil's configuration.")

            else:

                cmd = (self.driver_settings['config_cmd'] +
                       self.driver_settings['number'] +
                       ',C1,00,18,' +
                       self.driver_settings['pulse_ms'] + ',' +
                       self.driver_settings['pwm1'] + ',' +
                       self.driver_settings['pwm2'] + ',' +
                       self.driver_settings['recycle_ms'])

        # todo pwm32

        self.log.debug("Sending Enable Command: %s", cmd)
        self.send(cmd)
        # todo change hold to pulse with re-ups

        #self.check_auto()

    def pulse(self, milliseconds=None):
        """Pulses this driver. """

        if not milliseconds:
            hex_ms_string = self.driver_settings['pulse_ms']
        else:
            hex_ms_string = Util.int_to_hex_string(milliseconds)
        if self.autofire:
            cmd = (self.driver_settings['trigger_cmd'] +
                   self.driver_settings['number'] + ',' +
                   '01')
            if milliseconds:
                self.log.debug("Received command to pulse driver for %sms, but"
                               "this driver is configured with an autofire rule"
                               ", so that pulse value will be used instead.")
        else:
            cmd = (self.driver_settings['config_cmd'] +
                   self.driver_settings['number'] +
                   ',89,00,10,' +
                   hex_ms_string + ',' +
                   self.driver_settings['pwm1'] + ',00,00,' +
                   self.driver_settings['recycle_ms'])

        self.log.debug("Sending Pulse Command: %s", cmd)
        self.send(cmd)
        self.check_auto()

        return Util.hex_string_to_int(hex_ms_string)

    def get_pulse_ms(self):
        return Util.hex_string_to_int(self.driver_settings['pulse_ms'])

    def check_auto(self):

        if self.autofire:
            cmd = (self.driver_settings['trigger_cmd'] +
                   self.driver_settings['number'] +
                   ',00')

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
        self.last_time_changed = self.machine.clock.get_time()

    def on(self, brightness=255):
        if brightness >= 255:
            self.log.debug("Turning On GI String")
            self.send('GI:' + self.number + ',FF')
        elif brightness == 0:
            self.off()
        else:
            brightness = str(hex(brightness))[2:]
            self.send('GI:' + self.number + ',' + brightness)

        self.last_time_changed = self.machine.clock.get_time()


class FASTMatrixLight(MatrixLightPlatformInterface):

    def __init__(self, number, sender):
        self.log = logging.getLogger('FASTMatrixLight')
        self.number = number
        self.send = sender

    def off(self):
        """Disables (turns off) this matrix light."""
        self.send('L1:' + self.number + ',00')
        self.last_time_changed = self.machine.clock.get_time()

    def on(self, brightness=255):
        """Enables (turns on) this driver."""
        if brightness >= 255:
            self.send('L1:' + self.number + ',FF')
        elif brightness == 0:
            self.off()
        else:
            pass
            # patter rates of 10/1 through 2/9

        self.last_time_changed = self.machine.clock.get_time()


class FASTDirectLED(RGBLEDPlatformInterface):
    """
    Represents a single RGB LED connected to the Fast hardware platform
    """
    def __init__(self, number):
        self.log = logging.getLogger('FASTLED')
        self.number = number
        self._color_order_function = FASTDirectLED._color_rgb
        self._current_color = '000000'

        # All FAST LEDs are 3 element RGB and are set using hex strings

        self.log.debug("Creating FAST RGB LED at hardware address: %s",
                       self.number)

    @property
    def color_order(self):
        return {
            FASTDirectLED._color_rgb: 'rgb',
            FASTDirectLED._color_rbg: 'rbg',
            FASTDirectLED._color_grb: 'grb',
            FASTDirectLED._color_gbr: 'gbr',
            FASTDirectLED._color_bgr: 'bgr',
            FASTDirectLED._color_brg: 'brg'
        }.get(self._color_order_function, 'error')

    @color_order.setter
    def color_order(self, order):
        self._color_order_function = FASTDirectLED._determine_color_order_function(order)

    @staticmethod
    def _determine_color_order_function(order):
        return {
            'rgb': FASTDirectLED._color_rgb,
            'rbg': FASTDirectLED._color_rbg,
            'grb': FASTDirectLED._color_grb,
            'gbr': FASTDirectLED._color_gbr,
            'bgr': FASTDirectLED._color_bgr,
            'brg': FASTDirectLED._color_brg
        }.get(order, FASTDirectLED._color_rgb)

    @staticmethod
    def _color_rgb(color):
        return color.hex

    @staticmethod
    def _color_rbg(color):
        return RGBColor.rgb_to_hex((color.red, color.blue, color.green))

    @staticmethod
    def _color_grb(color):
        return RGBColor.rgb_to_hex((color.green, color.red, color.blue))

    @staticmethod
    def _color_gbr(color):
        return RGBColor.rgb_to_hex((color.green, color.blue, color.red))

    @staticmethod
    def _color_bgr(color):
        return RGBColor.rgb_to_hex((color.blue, color.green, color.red))

    @staticmethod
    def _color_brg(color):
        return RGBColor.rgb_to_hex((color.blue, color.red, color.green))

    def color(self, color):
        """Instantly sets this LED to the color passed.

        Args:
            color: an RGBColor object
        """
        self._current_color = self._color_order_function(color)

    def disable(self):
        """Disables (turns off) this LED instantly. For multi-color LEDs it
        turns all elements off.
        """
        self._current_color = '000000'

    def enable(self):
        self._current_color = 'ffffff'

    @property
    def current_color(self):
        return self._current_color


class FASTDMD(object):

    def __init__(self, machine, sender):
        self.machine = machine
        self.send = sender

        # Clear the DMD
        pass  # todo

        self.dmd_frame = bytearray()

        # Update DMD 30 times per second
        # TODO: Add DMD update interval to config
        self.machine.clock.schedule_interval(self.tick, 1/30.0)

    def update(self, data):

        try:
            self.dmd_frame = bytearray(data)
        except TypeError:
            pass

    def tick(self, dt):
        self.send('BM:' + self.dmd_frame)


class SerialCommunicator(object):

    def __init__(self, machine, platform, port, baud, send_queue, receive_queue):
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
            self.serial_connection.write('ID:\r')
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
            latest_version = DMD_LATEST_FW
            self.dmd = True
        elif self.remote_processor == 'NET':
            min_version = NET_MIN_FW
            latest_version = NET_LATEST_FW
        else:
            min_version = RGB_MIN_FW
            latest_version = RGB_LATEST_FW

        if StrictVersion(min_version) > StrictVersion(self.remote_firmware):
            self.platform.log.critical("Firmware version mismatch. MPF requires"
                                       " the %s processor to be firmware %s, but yours is %s",
                                       self.remote_processor, min_version, self.remote_firmware)
            sys.exit()

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
            self.serial_connection.write('NN:{0}\r'.format(board_id))
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
                                           'Drivers: {4}'.format(node_id, model,
                                           fw, int(sw, 16), int(dr, 16)))

                    if StrictVersion(IO_MIN_FW) > str(fw):
                        self.platform.log.critical("Firmware version mismatch. MPF "
                                                   "requires the IO boards to be firmware {0}, but "
                                                   "your Board {1} ({2}) is v{3}".format(IO_MIN_FW,
                                                                                         node_id, model, fw))
                        firmware_ok = False

        if not firmware_ok:
            self.platform.log.critical("Exiting due to IO board firmware "
                                       "mismatch")
            sys.exit()

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
            while self.serial_connection:
                msg = self.send_queue.get()
                self.serial_connection.write(msg)

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
