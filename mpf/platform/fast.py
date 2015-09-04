"""Contains the hardware interface and drivers for the FAST Pinball platform
hardware, including the FAST Core and WPC controllers as well as FAST I/O
boards.

"""

# fast.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import time
import sys
import threading
import Queue
import traceback
import io
from distutils.version import StrictVersion

from mpf.system.platform import Platform
from mpf.system.config import Config

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
RGB_LATEST_FW = '0.87'
IO_LATEST_FW = '0.89'

PWM8_TO_HEX_STR = {0: '00', 1: '01', 2: '88', 3: '92', 4: 'AA',
                   5: 'BA', 6: 'EE', 7: 'FE', 8: 'FF'}


class HardwarePlatform(Platform):
    """Platform class for the FAST hardware controller.

    Args:
        machine: The main ``MachineController`` instance.

    """

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger('FAST')
        self.log.debug("Configuring FAST hardware.")

        if not serial_imported:
            self.log.error('Could not import "pySerial". This is required for '
                           'the FAST platform interface')
            sys.exit()

        # ----------------------------------------------------------------------
        # Platform-specific hardware features. WARNING: Do not edit these. They
        # are based on what the FAST hardware can and cannot do.
        self.features['max_pulse'] = 255  # todo
        self.features['hw_timer'] = False
        self.features['hw_rule_coil_delay'] = True  # todo
        self.features['variable_recycle_time'] = True  # todo
        self.features['variable_debounce_time'] = True  # todo
        self.features['hw_enable_auto_disable'] = True
        # Make the platform features available to everyone
        self.machine.config['platform'] = self.features
        # ----------------------------------------------------------------------

        self.hw_rules = dict()
        self.dmd_connection = None
        self.net_connection = None
        self.rgb_connection = None
        self.fast_nodes = list()
        self.connection_threads = set()
        self.receive_queue = Queue.Queue()
        self.fast_leds = set()
        self.flag_led_tick_registered = False
        self.fast_io_boards = list()
        self.waiting_for_switch_data = False

        config_spec = '''
                    ports: list
                    baud: int|921600
                    config_number_format: string|hex
                    watchdog: ms|1000
                    default_debounce_open: ms|30
                    default_debounce_close: ms|30
                    debug: boolean|False
                    '''

        self.config = Config.process_config(config_spec=config_spec,
                                            source=self.machine.config['fast'])

        self.watchdog_command = 'WD:' + str(hex(self.config['watchdog']))[2:]

        self.machine_type = (
            self.machine.config['hardware']['driverboards'].lower())

        if self.machine_type == 'wpc':
            self.log.debug("Configuring the FAST Controller for WPC driver "
                           "board")
        else:
            self.log.debug("Configuring FAST Controller for FAST IO boards.")

        self._connect_to_hardware()

        if 'config_number_format' not in self.machine.config['fast']:
            self.machine.config['fast']['config_number_format'] = 'int'

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

        self.pwm8_to_int = {
            0: 0, 1: 1, 2: 136, 3: 146, 4: 170, 5: 186, 6: 238,
            7: 254, 8: 255
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

    def __repr__(self):
        return '<Platform.FAST>'

    def process_received_message(self, msg):
        """Sends an incoming message from the FAST controller to the proper
        method for servicing.

        """

        if msg[2:3] == ':':
            cmd = msg[0:2]
            payload = msg[3:].replace('\r','')
        else:
            print msg
            return

        # Can't use try since it swallows too many errors for now
        if cmd in self.fast_commands:
            self.fast_commands[cmd](payload)
        else:
            self.log.warning("Received unknown serial command? %s. (This is ok "
                             "to ignore for now while the FAST platform is in "
                             "development)", msg)

    def _connect_to_hardware(self):
        # Connect to each port from the config. This procuess will cause the
        # connection threads to figure out which processor they've connected to
        # and to register themselves.
        for port in self.config['ports']:
            self.connection_threads.add(SerialCommunicator(machine=self.machine,
                platform=self, port=port, baud=self.config['baud'],
                send_queue=Queue.Queue(), receive_queue=self.receive_queue))

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
            self.rgb_connection.send('RA:000000')  # turn off all LEDs

    def update_leds(self):
        """Updates all the LEDs connected to a FAST controller. This is done
        once per game loop for efficiency (i.e. all LEDs are sent as a single
        update rather than lots of individual ones).

        Also, every LED is updated every loop, even if it doesn't change. This
        is in case some interference causes a LED to change color. Since we
        update every loop, it will only be the wrong color for one tick.

        """

        msg = 'RS:'

        for led in self.fast_leds:
            msg += (led.number + led.current_color + ',')  # todo change to join

        msg = msg[:-1]  # trim the final comma

        self.rgb_connection.send(msg)

    def get_hw_switch_states(self):
        self.hw_switch_data = None
        self.net_connection.send('SA:')

        while not self.hw_switch_data:
            time.sleep(.01)
            self.tick()

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

        self.log.debug("Received SA: %s", msg)

        hw_states = dict()

        num_local, local_states, num_nw, nw_states = msg.split(',')

        for offset, byte in enumerate(bytearray.fromhex(nw_states)):
            for i in range(8):
                num = Config.int_to_hex_string((offset * 8) + i)
                if byte & (2**i):
                    hw_states[(num, 1)] = 1
                else:
                    hw_states[(num, 1)] = 0

        for offset, byte in enumerate(bytearray.fromhex(local_states)):
            for i in range(8):

                num = Config.int_to_hex_string((offset * 8) + i)

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
                                                config['number_str'].upper())
            if ('connection' in config and
                    config['connection'].lower() == 'network'):
                config['connection'] = 1
            else:
                config['connection'] = 0  # local driver (default for WPC)

        # If we have fast driver boards, we need to make sure we have hex strs
        elif self.machine_type == 'fast':

            if self.config['config_number_format'] == 'int':
                config['number'] = Config.int_to_hex_string(config['number'])
            else:
                config['number'] = Config.normalize_hex_string(config['number'])

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

        return (FASTDriver(config, self.net_connection.send),
            (config['number'], config['connection']))

        # todo set the rest time, default pulse times, etc.?

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
            self.log.critical("A request was made to configure a FAST switch, "
                              "but no connection to a NET processor is "
                              "available")
            sys.exit()

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

            if self.config['config_number_format'] == 'int':
                config['number'] = Config.int_to_hex_string(config['number'])
            else:
                config['number'] = Config.normalize_hex_string(config['number'])

        # convert the switch number into a tuple which is:
        # (switch number, connection)
        config['number'] = (config['number'], config['connection'])

        if 'debounce_open' not in config:
            config['debounce_open'] = self.config['default_debounce_open']

        if 'debounce_close' not in config:
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
            self.machine.events.add_handler('timer_tick', self.update_leds)
            self.flag_led_tick_registered = True

        # if the LED number is in <channel> - <led> format, convert it to a
        # FAST hardware number
        if '-' in config['number_str']:
            num = config['number_str'].split('-')
            config['number'] = int((num[0] * 64) + num[1])
        else:
            config['number'] = str(config['number'])

        if self.config['config_number_format'] == 'int':
            config['number'] = Config.int_to_hex_string(config['number'])
        else:
            config['number'] = Config.normalize_hex_string(config['number'])

        this_fast_led = FASTDirectLED(config['number'])
        self.fast_leds.add(this_fast_led)

        return this_fast_led

    def configure_gi(self, config):

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
            config['number'] = Config.int_to_hex_string(config['number'])
        else:
            config['number'] = Config.normalize_hex_string(config['number'])

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

    def tick(self):
        while not self.receive_queue.empty():
            self.process_received_message(self.receive_queue.get(False))

        self.net_connection.send(self.watchdog_command)

    def write_hw_rule(self, sw, sw_activity, coil_action_ms, coil=None,
                      pulse_ms=0, pwm_on=8, pwm_off=8, delay=0, recycle_time=0,
                      debounced=True, drive_now=False):
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
            sw: Which switch you're creating this rule for. The parameter is a
                reference to the switch object itsef.
            sw_activity: Int which specifies whether this coil should fire when
                the switch becomes active (1) or inactive (0)
            coil_action_ms: Int of the total time (in ms) that this coil action
                should take place. A value of -1 means it's forever. A value of
                0 means the coil disables itself when this switch goes into the
                state specified.
            coil: The coil object this rule is for.
            pulse_ms: How long should the coil be pulsed (ms)
            pwm_on: Integer 0 (off) through 8 (100% on) for the initial pwm
                power of this coil
            pwm_off: pwm level 0-8 of the power of this coil during the hold
                phase (after the initial kick).
            delay: Not currently implemented
            recycle_time: How long (in ms) should this switch rule wait before
                firing again. Put another way, what's the "fastest" this rule
                can fire? This is used to prevent "machine gunning" of
                slingshots and pop bumpers. Do not use it with flippers.
            debounced: Should the hardware fire this coil after the switch has
                been debounced?
            drive_now: Should the hardware check the state of the switches when
                this rule is firts applied, and fire the coils if they should
                be? Typically this is True, especially with flippers because you
                want them to fire if the player is holding in the buttons when
                the machine enables the flippers (which is done via several
                calls to this method.)

        """

        if not coil_action_ms:
            return  # with fast this is built into the main coil rule

        self.log.debug("Setting HW Rule. Switch:%s, Action ms:%s, Coil:%s, "
                       "Pulse:%s, pwm1:%s, pwm2:%s, Delay:%s, Recycle:%s,"
                       "Debounced:%s, Now:%s", sw.name, coil_action_ms,
                       coil.name, pulse_ms, pwm_on, pwm_off, delay,
                       recycle_time, debounced, drive_now)

        if not pwm_on:
            pwm_on = 8

        if not pwm_off:
            pwm_off = 8

        pwm_on = self.pwm8_to_int[pwm_on]
        pwm_off = self.pwm8_to_int[pwm_off]

        control = 0x01  # Driver enabled
        if drive_now:
            control += 0x08

        if sw_activity == 0:
            control += 0x10

        control = Config.int_to_hex_string(int(control))
        mode = '00'
        param1 = 0
        param2 = 0
        param3 = 0
        param4 = 0
        param5 = 0

        # First figure out if this is pulse (timed) or latched

        if coil_action_ms == -1:  # Latched
            mode = '18'
            param1 = pulse_ms   # max on time
            param2 = pwm_on     # pwm 1
            param3 = pwm_off    # pwm 2
            param4 = recycle_time
            #param5

        elif coil_action_ms > 0:  # Pulsed
            mode = '10'
            param1 = pulse_ms                   # initial pulse
            param2 = pwm_on                     # pwm for initial pulse
            param3 = coil_action_ms - pulse_ms  # second on time
            param4 = pwm_off                    # pwm for second pulse
            param5 = recycle_time

        if coil.number[1] == 1:
            cmd = 'DN:'
        else:
            cmd = 'DL:'

        param1 = Config.int_to_hex_string(param1)
        param2 = Config.int_to_hex_string(param2)
        param3 = Config.int_to_hex_string(param3)
        param4 = Config.int_to_hex_string(param4)
        param5 = Config.int_to_hex_string(param5)

        # hw_rules key = ('05', 1)
        # all values are strings

        self.hw_rules[coil] = {'mode': mode,
                               'param1': param1,
                               'param2': param2,
                               'param3': param3,
                               'param4': param4,
                               'param5': param5,
                               'switch': sw.number}

        cmd = (cmd + coil.number[0] + ',' + control  + ',' + sw.number[0] + ','
               + mode + ',' + param1 + ',' + param2 + ',' + param3 + ',' +
               param4 + ',' + param5)  # todo change to join()

        coil.autofire = cmd
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
        coils = [k for k, v in self.hw_rules.iteritems() if v['switch'] == sw_num]

        self.log.debug("Clearing HW Rule for switch: %s %s, coils: %s", sw_name,
                       sw_num, coils)

        for coil in coils:

            del self.hw_rules[coil]

            if coil.number[1] == 1:
                cmd = 'DN:'
            else:
                cmd = 'DL:'
            driver = coil.number[0]
            mode = '81'

            coil.autofire = None

            self.log.debug("Clearing hardware rule: %s",
                          cmd + driver + ',' + mode)

            self.net_connection.send(cmd + driver + ',' + mode)




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


class FASTDriver(object):
    """Base class for drivers connected to a FAST Controller.

    """

    def __init__(self, config, sender):
        """

        """

        self.autofire = None

        self.config = dict()

        self.config['trigger'] = '81'  # enabled, but with manual control
        self.config['mode'] = '10'  # pulsed
        self.config['param1'] = '00'
        self.config['param2'] = '00'
        self.config['param3'] = '00'
        self.config['param4'] = '00'
        self.config['param5'] = '00'

        self.log = logging.getLogger('FASTDriver')
        self.config['number'] = config['number']
        self.send = sender

        if config['connection'] == 1:
            self.config['config_cmd'] = 'DN:'
            self.config['trigger_cmd'] = 'TN:'
        else:
            self.config['config_cmd'] = 'DL:'
            self.config['trigger_cmd'] = 'TL:'

        if 'recycle_ms' in config:
            self.config['recycle_ms'] = str(config['recycle_ms'])
        else:
            self.config['recycle_ms'] = '00'

        if 'hold_pwm' in config:
            self.config['hold_pwm'] = PWM8_TO_HEX_STR[config['hold_pwm']]
        else:
            self.config['hold_pwm'] = 'FF'

        # send this driver's pulse / pwm settings

        if 'fast_param1' in config:
            self.config['param1'] = config['fast_param1']

        if 'fast_param2' in config:
            self.config['param2'] = config['fast_param2']

        if 'fast_param3' in config:
            self.config['param3'] = config['fast_param3']

        if 'fast_param4' in config:
            self.config['param4'] = config['fast_param4']

        if 'fast_param5' in config:
            self.config['param5'] = config['fast_param5']

    def disable(self):
        """Disables (turns off) this driver. """

        cmd = self.config['trigger_cmd'] + self.config['number'] + ',' + '02'

        self.log.debug("Sending Disable Command: %s", cmd)
        self.send(cmd)

    def enable(self):
        """Enables (turns on) this driver. """

        if self.autofire:
            cmd = (self.config['trigger_cmd'] + self.config['number'] + ',' +
                   '03')
        else:
            cmd = (self.config['config_cmd'] + self.config['number'] +
                   ',C1,00,18,00,ff,' + self.config['hold_pwm'] + ',' +
                   self.config['recycle_ms'])

        self.log.debug("Sending Enable Command: %s", cmd)
        self.send(cmd)
        # todo change hold to pulse with re-ups

    def pulse(self, milliseconds=None):
        """Pulses this driver. """

        if 0 <= milliseconds <= 255:
            milliseconds = format(milliseconds, 'x').upper().zfill(2)

        if self.autofire:
            cmd = (self.config['trigger_cmd'] + self.config['number'] + ',' +
            '01')
        else:
            cmd = (self.config['config_cmd'] + self.config['number'] +
                   ',89,00,10,' + str(milliseconds) + ',ff,00,00,' +
                   self.config['recycle_ms'])

        self.log.debug("Sending Pulse Command: %s", cmd)
        self.send(cmd)

    def pwm(self, on_ms=10, off_ms=10, original_on_ms=0, now=True):
        """Enables this driver in a pwm pattern.  """

        if self.autofire:
            cmd = (self.config['trigger_cmd'] + self.config['number'] + ',' +
                   '03')
        else:
            cmd = (self.config['config_cmd'] + self.config['number'] +
                   ',89,00,18,' + str(original_on_ms) + ',' + str(on_ms) + ','
                   + str(off_ms) + ',' + self.config['recycle_ms'])

        self.log.debug("Sending PWM Hold Command: %s", cmd)
        self.send(cmd)


class FASTGIString(object):
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
        self.last_time_changed = time.time()

    def on(self, brightness=255, fade_ms=0, start=0):
        if brightness >= 255:
            self.log.debug("Turning On GI String")
            self.send('GI:' + self.number + ',FF')
        elif brightness == 0:
            self.off()
        else:
            brightness = str(hex(brightness))[2:]
            self.send('GI:' + self.number + ',' + brightness)

        self.last_time_changed = time.time()


class FASTMatrixLight(object):

    def __init__(self, number, sender):
        self.log = logging.getLogger('FASTMatrixLight')
        self.number = number
        self.send = sender

    def off(self):
        """Disables (turns off) this matrix light."""
        self.send('L1:' + self.number + ',00')
        self.last_time_changed = time.time()

    def on(self, brightness=255, fade_ms=0, start=0):
        """Enables (turns on) this driver."""
        if brightness >= 255:
            self.send('L1:' + self.number + ',FF')
        elif brightness == 0:
            self.off()
        else:
            pass
            # patter rates of 10/1 through 2/9

        self.last_time_changed = time.time()


class FASTDirectLED(object):

    def __init__(self, number):
        self.log = logging.getLogger('FASTLED')
        self.number = number

        self.current_color = '000000'

        # All FAST LEDs are 3 element RGB

        self.log.debug("Creating FAST RGB LED at hardware address: %s",
                       self.number)

    def hex_to_rgb(self, value):
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    def rgb_to_hex(self, rgb):
        return '%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])

    def color(self, color):
        """Instantly sets this LED to the color passed.

        Args:
            color: a 3-item list of integers representing R, G, and B values,
            0-255 each.
        """

        self.current_color = self.rgb_to_hex(color)
        # todo this is crazy inefficient right now. todo change it so it can use
        # hex strings as the color throughout

    def fade(self, color, fade_ms):
        # todo
        # not yet implemented. For now we'll just immediately set the color
        self.color(color, fade_ms)

    def disable(self):
        """Disables (turns off) this LED instantly. For multi-color LEDs it
        turns all elements off.
        """

        self.current_color = '000000'

    def enable(self):
        self.current_color = 'ffffff'


class FASTDMD(object):

    def __init__(self, machine, sender):
        self.machine = machine
        self.send = sender

        # Clear the DMD
        pass  # todo

        self.dmd_frame = bytearray()

        self.machine.events.add_handler('timer_tick', self.tick)

    def update(self, data):

        try:
            self.dmd_frame = bytearray(data)
        except TypeError:
            pass

    def tick(self):
        self.send('BM:' + self.dmd_frame)


class SerialCommunicator(object):

    def __init__(self, machine, platform, port, baud, send_queue, receive_queue):
        self.machine = machine
        self.platform = platform
        self.send_queue = send_queue
        self.receive_queue = receive_queue
        self.debug = False
        self.log = None

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

                node_id, model, fw, sw, dr, _, _, _, _, _, _ = msg.split(',')
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

        try:
            while self.serial_connection:
                msg = self.serial_io.readline()[:-1]  # strip the \r

                if debug:
                    self.platform.log.info("Received: %s", msg)

                if msg not in self.ignored_messages:
                    self.receive_queue.put(msg)

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            msg = ''.join(line for line in lines)
            self.machine.crash_queue.put(msg)

# The MIT License (MIT)

# Oringal code on which this module was based:
# Copyright (c) 2009-2011 Adam Preble and Gerry Stellenberg

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
