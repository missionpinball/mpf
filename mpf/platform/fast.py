"""Contains the hardware interface and drivers for the FAST Pinball platform
hardware, including the FAST Core and FAST WPC controllers.

This code is written for the libfastpinball v1.0, released Dec 19, 2014.

https://github.com/fastpinball/libfastpinball

"""

# fast.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import time
import sys


from mpf.system.timing import Timing
from mpf.system.platform import Platform

try:
    import fastpinball
    fastpinball_imported = True
except:
    fastpinball_imported = False


class HardwarePlatform(Platform):
    """Platform class for the FAST hardware controller.

    Args:
        machine: The main ``MachineController`` instance.

    """

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger('FAST')
        self.log.debug("Configuring FAST hardware.")

        if not fastpinball_imported:
            self.log.error('Could not import "fastpinball". Most likely you do '
                           'not have libfastpinball installed. You can run MPF '
                           'in software-only "virtual" mode by using the -x '
                           'command like option for now instead.')
            sys.exit()

        # ----------------------------------------------------------------------
        # Platform-specific hardware features. WARNING: Do not edit these. They
        # are based on what the FAST hardware can and cannot do.
        self.features['max_pulse'] = 255  # todo
        self.features['hw_timer'] = False
        self.features['hw_rule_coil_delay'] = False  # todo
        self.features['variable_recycle_time'] = True  # todo
        self.features['variable_debounce_time'] = True  # todo
        self.features['hw_enable_auto_disable'] = True
        # Make the platform features available to everyone
        self.machine.config['platform'] = self.features
        # ----------------------------------------------------------------------

        self.hw_rules = dict()
        self.fast_events = None

        # Set up the connection to the FAST controller
        self.log.info("Initializing FAST Pinball Controller interface...")

        ports = list()

        if ('port0_name' in self.machine.config['fast'] and
                'port0_baud' in self.machine.config['fast']):

            ports.append((self.machine.config['fast']['port0_name'],
                          self.machine.config['fast']['port0_baud']))

        if ('port1_name' in self.machine.config['fast'] and
                'port1_baud' in self.machine.config['fast']):

            ports.append((self.machine.config['fast']['port1_name'],
                          self.machine.config['fast']['port1_baud']))

        if ('port2_name' in self.machine.config['fast'] and
                'port2_baud' in self.machine.config['fast']):

            ports.append((self.machine.config['fast']['port2_name'],
                          self.machine.config['fast']['port2_baud']))

        self.log.debug("FAST Ports: %s", ports)

        if ('main_port' in self.machine.config['fast'] and
                'led_port' in self.machine.config['fast'] and
                'dmd_port' in self.machine.config['fast']):

            port_assignments = (self.machine.config['fast']['main_port'],
                                self.machine.config['fast']['dmd_port'],
                                self.machine.config['fast']['led_port'])

        else:
            self.log.critical("Error in fast config. Entries needed for "
                              "main_port and led_port and dmd_port.")
            raise Exception()

        self.fast = fastpinball.fpOpen(ports, port_assignments)

        self.log.debug("Fast Config. Ports: %s, Assignments: %s", ports,
                       port_assignments)

        self._initialize_hardware()
        #self.timer_initialize()

        if 'config_number_format' not in self.machine.config['fast']:
            self.machine.config['fast']['config_number_format'] = 'int'

        self.machine_type = (
            self.machine.config['hardware']['driverboards'].upper())

        if self.machine_type == 'WPC':
            self.log.debug("Configuring the FAST Controller for WPC driver "
                           "boards")

        elif self.machine_type == 'FAST':
            self.log.debug("Configuring FAST Controller for FAST driver boards.")

        self.wpc_switch_map = {
            'S11': '00', 'S12': '01', 'S13': '02', 'S14': '03',
            'S15': '04', 'S16': '05', 'S17': '06', 'S18': '07',
            'S21': '08', 'S22': '09', 'S23': '10', 'S24': '11',
            'S25': '12', 'S26': '13', 'S27': '14', 'S28': '15',
            'S31': '16', 'S32': '17', 'S33': '18', 'S34': '19',
            'S35': '20', 'S36': '21', 'S37': '22', 'S38': '23',
            'S41': '24', 'S42': '25', 'S43': '26', 'S44': '27',
            'S45': '28', 'S46': '29', 'S47': '30', 'S48': '31',
            'S51': '32', 'S52': '33', 'S53': '34', 'S54': '35',
            'S55': '36', 'S56': '37', 'S57': '38', 'S58': '39',
            'S61': '40', 'S62': '41', 'S63': '42', 'S64': '43',
            'S65': '44', 'S66': '45', 'S67': '46', 'S68': '47',
            'S71': '48', 'S72': '49', 'S73': '50', 'S74': '51',
            'S75': '52', 'S76': '53', 'S77': '54', 'S78': '55',
            'S81': '56', 'S82': '57', 'S83': '58', 'S84': '59',
            'S85': '60', 'S86': '61', 'S87': '62', 'S88': '63',
            'S91': '64', 'S92': '65', 'S93': '66', 'S94': '67',
            'S95': '68', 'S96': '69', 'S97': '70', 'S98': '71',

            'SD1': '80', 'SD2': '81', 'SD3': '82', 'SD4': '83',
            'SD5': '84', 'SD6': '85', 'SD7': '86', 'SD8': '87',

            'DIP1': '88', 'DIP2': '89', 'DIP3': '90', 'DIP4': '91',
            'DIP5': '92', 'DIP6': '93', 'DIP7': '94', 'DIP8': '95',

            'SF1': '96', 'SF2': '97', 'SF3': '98', 'SF4': '99',
            'SF5': '100', 'SF6': '101', 'SF7': '102', 'SF8': '103',
                               }

        self.wpc_light_map = {
            'L11': '00', 'L12': '01', 'L13': '02', 'L14': '03',
            'L15': '04', 'L16': '05', 'L17': '06', 'L18': '07',
            'L21': '08', 'L22': '09', 'L23': '10', 'L24': '11',
            'L25': '12', 'L26': '13', 'L27': '14', 'L28': '15',
            'L31': '16', 'L32': '17', 'L33': '18', 'L34': '19',
            'L35': '20', 'L36': '21', 'L37': '22', 'L38': '23',
            'L41': '24', 'L42': '25', 'L43': '26', 'L44': '27',
            'L45': '28', 'L46': '29', 'L47': '30', 'L48': '31',
            'L51': '32', 'L52': '33', 'L53': '34', 'L54': '35',
            'L55': '36', 'L56': '37', 'L57': '38', 'L58': '39',
            'L61': '40', 'L62': '41', 'L63': '42', 'L64': '43',
            'L65': '44', 'L66': '45', 'L67': '46', 'L68': '47',
            'L71': '48', 'L72': '49', 'L73': '50', 'L74': '51',
            'L75': '52', 'L76': '53', 'L77': '54', 'L78': '55',
            'L81': '56', 'L82': '57', 'L83': '58', 'L84': '59',
            'L85': '60', 'L86': '61', 'L87': '62', 'L88': '63',
                               }

        self.wpc_driver_map = {
            'C01': '00', 'C02': '01', 'C03': '02', 'C04': '03',
            'C05': '04', 'C06': '05', 'C07': '06', 'C08': '07',
            'C09': '08', 'C10': '09', 'C11': '10', 'C12': '11',
            'C13': '12', 'C14': '13', 'C15': '14', 'C16': '15',
            'C17': '16', 'C18': '17', 'C19': '18', 'C20': '19',
            'C21': '20', 'C22': '21', 'C23': '22', 'C24': '23',
            'C25': '24', 'C26': '25', 'C27': '26', 'C28': '27',
            'C29': '32', 'C30': '33', 'C31': '34', 'C32': '35',
            'C33': '36', 'C34': '37', 'C35': '38', 'C36': '39',
            'FLRM': '32', 'FLRH': '33', 'FLLM': '34', 'FLLH': '35',
            'FURM': '36', 'FURH': '37', 'FULM': '38', 'FULH': '39',
            'C37': '40', 'C38': '41', 'C39': '42', 'C40': '43',
            'C41': '44', 'C42': '45', 'C43': '46', 'C44': '47',
                                }

        self.wpc_gi_map = {
            'G01': '00', 'G02': '01', 'G03': '02', 'G04': '03',
            'G05': '04', 'G06': '05', 'G07': '06', 'G08': '07',
                          }

        # temp until we have a proper reset
        fastpinball.fpWriteAllRgbs(self.fast, 0, 0, 0)

    def _initialize_hardware(self):
        # The fast hardware needs to get a loop setup and needs a few calls
        # to start sending switch data. So we do that here and return once we
        # get valid switch data back.
        self.log.info("Connecting to the FAST hardware...")

        # libfastpinball needs a timer to work, but since we don't use it in MPF
        # we'll set it to 1 sec (1,000,000us) so it doesn't get in our way
        fastpinball.fpTimerConfig(self.fast, 5000)

        self.fast_events = fastpinball.fpGetEventObject()

        fastpinball.fpEventPoll(self.fast, self.fast_events)
        fastpinball.fpEventPoll(self.fast, self.fast_events)
        fastpinball.fpEventPoll(self.fast, self.fast_events)
        fastpinball.fpEventPoll(self.fast, self.fast_events)
        fastpinball.fpEventPoll(self.fast, self.fast_events)

        got_local_switches = False
        got_nw_switches = False

        return  # Uncomment to allow running without a physical connection

        while not got_local_switches or not got_nw_switches:
            time.sleep(0.001)
            fastpinball.fpReadAllSwitches(self.fast)
            fastpinball.fpEventPoll(self.fast, self.fast_events)
            fastpinball.fpEventPoll(self.fast, self.fast_events)
            fastpinball.fpEventPoll(self.fast, self.fast_events)
            fastpinball.fpEventPoll(self.fast, self.fast_events)
            fastpinball.fpEventPoll(self.fast, self.fast_events)
            event_type = fastpinball.fpGetEventType(self.fast_events)

            if event_type == fastpinball.FP_EVENT_TYPE_NETWORK_SWITCHES_UPDATED:
                got_nw_switches = True

            elif event_type == fastpinball.FP_EVENT_TYPE_SWITCHES_UPDATED:
                got_local_switches = True

        self.log.info("Connected to the FAST hardware.")

    def timer_initialize(self):

        # FAST timer tick is in microsecs
        us = int((1.0 / self.machine.config['timing']['hz']) * 1000000)
        self.log.debug("Initializing the FAST hardware timer for %sHz (%s us)",
                       Timing.HZ, us)
        #fastpinball.fpTimerConfig(self.fast, us)

    def configure_driver(self, config, device_type='coil'):

        # If we have WPC driver boards, look up the switch number
        if self.machine_type == 'WPC':
            config['number'] = int(self.wpc_driver_map.get(
                                   config['number_str'].upper()))
            if 'connection' not in config:
                config['connection'] = 0  # local driver (default for WPC)
            else:
                config['connection'] = 1  # network driver

        # If we have fast driver boards, we need to make sure we have ints
        elif self.machine_type == 'FAST':

            if self.machine.config['fast']['config_number_format'] == 'hex':
                config['number'] = int(config['number_str'], 16)

            # Now figure out the connection type
            if 'connection' not in config:
                config['connection'] = 1  # network driver (default for FAST)
            else:
                config['connection'] = 0  # local driver

        # convert the driver number into a tuple which is:
        # (driver number, connection type)
        config['number'] = (config['number'], config['connection'])

        return FASTDriver(config['number'], self.fast), config['number']

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

        if self.machine_type == 'WPC':  # translate switch number to FAST switch
            config['number'] = int(self.wpc_switch_map.get(
                                   config['number_str']))
            if 'connection' not in config:
                config['connection'] = 0  # local switch (default for WPC)
            else:
                config['connection'] = 1  # network switch

        elif self.machine_type == 'FAST':
            if 'connection' not in config:
                config['connection'] = 1  # network switch (default for FAST)
            else:
                config['connection'] = 0  # local switch

            if self.machine.config['fast']['config_number_format'] == 'hex':
                config['number'] = int(config['number_str'], 16)

        # converet the switch number into a tuple which is:
        # (switch number, connection)
        config['number'] = (config['number'], config['connection'])

        if 'debounce_on' not in config:
            if 'default_debounce_on_ms' in self.machine.config['fast']:
                config['debounce_on'] = (self.machine.config['fast']
                                         ['default_debounce_on_ms'])
            else:
                config['debounce_on'] = 20
        if 'debounce_off' not in config:
                if 'default_debounce_off_ms' in self.machine.config['fast']:
                    config['debounce_off'] = (self.machine.config['fast']
                                              ['default_debounce_off_ms'])
                else:
                    config['debounce_off'] = 20

        self.log.debug("FAST Switch hardware tuple: %s", config['number'])

        switch = FASTSwitch(config['number'], config['debounce_on'],
                            config['debounce_off'], self.fast)

        state = fastpinball.fpReadSwitch(self.fast, config['number'][0],
                                         config['number'][1])

        # Return the switch object and an integer of its current state.
        # 1 = active, 0 = inactive
        return switch, config['number'], state

    def configure_led(self, config):
        # if the LED number is in <channel> - <led> format, convert it to a
        # FAST hardware number
        if '-' in config['number_str']:
            num = config['number_str'].split('-')
            config['number'] = int((num[0] * 64) + num[1])
        else:
            config['number'] = str(config['number'])

        # if the config is in hex format, convert it to int
        if self.machine.config['fast']['config_number_format'] == 'hex':
            config['number'] = int(config['number'], 16)

        return FASTDirectLED(config['number'], self.fast)

    def configure_gi(self, config):
        if self.machine_type == 'WPC':  # translate switch number to FAST switch
            config['number'] = int(self.wpc_gi_map.get(config['number_str']))

        return FASTGIString(config['number'], self.fast), config['number']

    def configure_matrixlight(self, config):
        if self.machine_type == 'WPC':  # translate switch number to FAST switch
            config['number'] = int(self.wpc_light_map.get(config['number_str']))
        elif self.machine.config['fast']['config_number_format'] == 'hex':
            config['number'] = int(config['number_str'], 16)

        return FASTMatrixLight(config['number'], self.fast), config['number']

    def configure_dmd(self):
        """Configures a hardware DMD connected to a FAST controller."""
        return FASTDMD(self.machine, self.fast)

    def tick(self):
        no_more_events = False

        while not no_more_events:

            fastpinball.fpEventPoll(self.fast, self.fast_events)
            event_type = fastpinball.fpGetEventType(self.fast_events)

            if event_type == fastpinball.FP_EVENT_TYPE_NONE:
                no_more_events = True

            elif event_type == fastpinball.FP_EVENT_TYPE_TIMER_TICK:
                no_more_events = True

            elif event_type == fastpinball.FP_EVENT_TYPE_SWITCH_ACTIVE:
                self.machine.switch_controller.process_switch(state=1,
                    num=(fastpinball.fpGetEventSwitchID(self.fast_events), 0))

            elif event_type == fastpinball.FP_EVENT_TYPE_SWITCH_INACTIVE:
                self.machine.switch_controller.process_switch(state=0,
                    num=(fastpinball.fpGetEventSwitchID(self.fast_events), 0))

            elif event_type == fastpinball.FP_EVENT_TYPE_NETWORK_SWITCH_ACTIVE:
                self.machine.switch_controller.process_switch(state=1,
                    num=(fastpinball.fpGetEventSwitchID(self.fast_events), 1))

            elif event_type == fastpinball.FP_EVENT_TYPE_NETWORK_SWITCH_INACTIVE:
                self.machine.switch_controller.process_switch(state=0,
                    num=(fastpinball.fpGetEventSwitchID(self.fast_events), 1))

    def write_hw_rule(self, sw, sw_activity, coil_action_ms, coil=None,
                      pulse_ms=0, pwm_on=0, pwm_off=0, delay=0, recycle_time=0,
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
            pwm_on: If the coil should be held on at less than 100% duty cycle,
                this is the "on" time (in ms).
            pwm_off: If the coil should be held on at less than 100% duty cycle,
                this is the "off" time (in ms).
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

        self.log.info("Setting HW Rule. Switch:%s, Action ms:%s, Coil:%s, "
                       "Pulse:%s, pwm_on:%s, pwm_off:%s, Delay:%s, Recycle:%s,"
                       "Debounced:%s, Now:%s", sw.name, coil_action_ms,
                       coil.name, pulse_ms, pwm_on, pwm_off, delay,
                       recycle_time, debounced, drive_now)

        control = 0x01  # Driver enabled
        mode = 0x00
        param1 = 0
        param2 = 0
        param3 = 0
        param4 = 0
        param5 = 0

        # First figure out if this is pulse (timed) or latched

        if coil_action_ms == -1:  # Latched
            mode = fastpinball.FP_DRIVER_MODE_LATCHED

            # do we have pulse+pwm, pwm only, or straight enable?

            # pulse+pwm
            if pulse_ms and pwm_on and pwm_off:
                # pwm = self.pwm_to_byte(pwm_on, pwm_off)
                pass  # todo

            # pwm only
            elif not pulse_ms and pwm_on and pwm_off:
                # pwm = self.pwm_to_byte(pwm_on, pwm_off)
                pass  # todo
            # enable
            else:
                pwm = 0xff

            # build up the args for fpConfigDriver
            param1 = pulse_ms
            param2 = pwm

        elif coil_action_ms > 0:  # Pulsed
            mode = fastpinball.FP_DRIVER_MODE_PULSED

            pwm = coil_action_ms - pulse_ms

            # build up the args for fpConfigDriver
            param1 = pulse_ms
            param2 = pwm

        # Does this rule fire on a switch open?
        if sw_activity == 0:
            control += fastpinball.FP_DRIVER_CONTROL_SWITCH_1_INVERTED

        self.hw_rules[coil.config['number']] = {'mode': mode,
                                                'switch': sw.number,
                                                'on': pwm_on,
                                                'off': pwm_off}

        self.log.info("fpConfigDriver (int): %s,%s,%s,%s,%s,%s,%s,%s,%s,%s",
                      coil.number[0], control, sw.number[0], mode, param1,
                      param2, param3, param4, param5, coil.number[1])

        fastpinball.fpConfigDriver(self.fast,
                                   coil.number[0],
                                   control,
                                   sw.number[0],
                                   mode,
                                   param1,
                                   param2,
                                   param3,
                                   param4,
                                   param5,
                                   coil.number[1])


        """


        DN:00,01,00,10,20,FF,00,00,80 => Flipper Main Coil, Pulse
           id,co,sw,md,p1,p2,p3,p4,p5
        DN:01,01,00,18,20,92,20,00,00 => Flipper Hold Coil, Latched
        DN:04,01,04,10,20,AA,00,00,80 => Slingshot, Pulsed
        DN:0a,01,2D,10,20,AA,00,00,80 => Pop Bumper

        Params - pulse (mode 10)
        ontime1
        pwm1
        ontime2
        pwm2
        resttime

        Params - latches (mode 18)
        pwm1_maxontime
        pwm1
        pwm2
        resttime
        none

            fastpnball. fpConfigDriver(fpDevice,
                                unsigned char id,
                                unsigned char control,
                                unsigned char switchId,
                                unsigned char mode,
                                unsigned char param1,
                                unsigned char param2,
                                unsigned char param3,
                                unsigned char param4,
                                unsigned char param5,
                                int target);

        Control
        FP_DRIVER_CONTROL_OFF                   = 0x00,
        FP_DRIVER_CONTROL_DRIVER_ENABLED        = 0x01,
        FP_DRIVER_CONTROL_TRIGGER_ONESHOT       = 0x08,
        FP_DRIVER_CONTROL_SWITCH_1_INVERTED     = 0x10,
        FP_DRIVER_CONTROL_SWITCH_2_INVERTED     = 0x20,
        FP_DRIVER_CONTROL_MANUAL_MODE_TRIGGER   = 0x40,
        FP_DRIVER_CONTROL_MANUAL_MODE_ENABLED   = 0x80

        Mode
        FP_DRIVER_MODE_OFF                          = 0x00,
        FP_DRIVER_MODE_PULSED                       = 0x10,
        FP_DRIVER_MODE_LATCHED                      = 0x18,
        FP_DRIVER_MODE_FLIPFLOP                     = 0x20,
        FP_DRIVER_MODE_DELAY                        = 0x30,
        FP_DRIVER_MODE_FLIPPER_DUAL                 = 0x40,
        FP_DRIVER_MODE_FLIPPER_DUAL_COMPANION       = 0x41,
        FP_DRIVER_MODE_FLIPPER_DUAL_EOS             = 0x48,
        FP_DRIVER_MODE_FLIPPER_DUAL_EOS_COMPANION   = 0x49,
        FP_DRIVER_MODE_FLIPPER_PWM                  = 0x50,
        FP_DRIVER_MODE_FLIPPER_PWM_EOS              = 0x58,
        FP_DRIVER_MODE_DIVERTER                     = 0x70,
        FP_DRIVER_MODE_DITHER                       = 0x80
        """

        # old
        #fastpinball.fpWriteDriver(self.fast,        # fast board
        #                          coil.number[0],   # coil number
        #                          mode,             # mode
        #                          sw_activity,      # triggerType
        #                          sw.number[0],     # switch
        #                          pulse_ms,         # on time
        #                          recycle_time,     # time before can enable again
        #                          pwm,              # pwm (0 - 32)
        #                          coil.number[1],   # local or network
        #                          )
        # todo ensure / verify switch & coil are on the same board.

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

        self.log.debug("Clearing HW Rule for switch %s", sw_num)

        # find the rule(s) based on this switch
        coils = [k for k, v in self.hw_rules.iteritems() if v == sw_num]

        for coil in coils:
            fastpinball.fpConfigDriver(self.fast,    # fast board
                                       coil[0],      # DRIVER_ID
                                       0,            # CONTROL
                                       0,            # SWITCH_ID
                                       0,            # MODE
                                       0,            # PARAM 1
                                       0,            # PARAM 2
                                       0,            # PARAM 3
                                       0,            # PARAM 4
                                       0,            # PARAM 5
                                       coil[1],      # local or network
                                       )
            # todo ensure / verify switch & coil are on the same board.

        self.log.info("fpConfigDriver (int): %s,%s,%s,%s,%s,%s,%s,%s,%s,%s",
                      coil.number[0], 0, 0, 0, 0, 0, 0, 0, 0, coil.number[1])

    def get_switch_state(self, switch):
        """Returns the hardware state of a switch.

        Args:
            switch: A class `Switch` object.

        Returns:
            Integer 1 if the switch is active, and 0 if the switch is
            inactive. This method does not compensate for NO or NC status,
            rather, it returns the raw hardware state of the switch.

        """
        return fastpinball.fpReadSwitch(self.fast, switch.number[0],
                                        switch.number[1])


class FASTSwitch(object):
    """
    fpWriteSwitchConfig params:
        fp_device (self.fast)
        switch number (switch number as int)
        mode (0 = no report, 1 = report on, 2 = report inverted
        debounce close
        debounce open
        sound
        target (0 = local, 1 = network)

        todo add support for different debounce open and close times

    """

    def __init__(self, number, debounce_on, debounce_off, fast_device):
        self.log = logging.getLogger('FASTSwitch')
        self.fast = fast_device
        self.number = number[0]
        self.connection = number[1]
        self.log.debug("fastpinball.fpWriteSwitchConfig(%s, %s, 1, %s, %s, 0, "
                       "%s)", fast_device, number[0], debounce_on,
                       debounce_off, number[1])
        fastpinball.fpWriteSwitchConfig(fast_device,    # fast board
                                        number[0],      # switch number
                                        1,              # mode (1=report "on")
                                        debounce_on,    # debounce on (close)
                                        debounce_off,   # debounce off (open)
                                        0,              # sound
                                        number[1])      # connection type




class FASTDriver(object):
    """Base class for drivers connected to a FAST Controller.

    """

    def __init__(self, number, fast_device):
        """

        Args:
            config:
            fast_device:

        config dict:
            number: int
            connection: 1=network, 0=local
            pulse_ms: int
            pwm_on:
            pwm_off:
            allow_enable:
        """
        self.log = logging.getLogger('FASTDriver')
        self.number = number
        self.fast = fast_device

    def disable(self):
        """Disables (turns off) this driver.

        FAST Protcol command DL/DN:

        DRIVER_ID
        CONTROL n/a
        SWITCH_ID n/a
        MODE fastpinball.FP_DRIVER_MODE_OFF (0x00)
        PARAM1 n/a
        PARAM2 n/a
        PARAM3 n/a
        PARAM4 n/a
        PARAM5 n/a

        Associated libfastpinball method:

        """

        self.log.debug('Disabling Driver')
        fastpinball.fpConfigDriver(self.fast,                       # FAST BOARD
                                   self.number[0],                  # DRIVER_ID
                                   0,                               # CONTROL
                                   0,                               # SWITCH_ID
                                   fastpinball.FP_DRIVER_MODE_OFF,  # MODE
                                   0,                               # PARAM 1
                                   0,                               # PARAM 2
                                   0,                               # PARAM 3
                                   0,                               # PARAM 4
                                   0,                               # PARAM 5
                                   self.number[1],                  # LOCAL/NW
                                   )

        self.log.info("fpConfigDriver (int): %s,%s,%s,%s,%s,%s,%s,%s,%s,%s",
                      self.number[0], 0, 0, fastpinball.FP_DRIVER_MODE_OFF, 0,
                      0, 0, 0, 0, self.number[1])

    def enable(self):
        """Enables (turns on) this driver.

        FAST Protcol command DL/DN:

        DRIVER_ID
        CONTROL 193
        SWITCH_ID
        MODE fastpinball.FP_DRIVER_MODE_LATCHED (0x18)
        PARAM1 pwm max on time
        PARAM2 pwm 1
        PARAM3 pwm 2
        PARAM4 rest time
        PARAM5 not used with latched config

        CONTROL is 193 (0xC1) which is bitwise or of:
        0x01 Driver enabled
        0x40 Manual mode trigger
        0x80 Manual mode enabled

        """
        self.log.debug('Enabling Driver')
        fastpinball.fpConfigDriver(self.fast,       # fast board
                                   self.number[0],  # driver number
                                   193,             # control
                                   0,               # switch
                                   fastpinball.FP_DRIVER_MODE_LATCHED,  # mode
                                   10,              # pwm max on time
                                   255,             # pwm 1
                                   255,             # pwm 2
                                   0,               # rest time
                                   0,               # not used
                                   self.number[1],  # local or network
                                   )

        self.log.info("fpConfigDriver (int): %s,%s,%s,%s,%s,%s,%s,%s,%s,%s",
                      self.number[0], 193, 0,
                      fastpinball.FP_DRIVER_MODE_LATCHED,
                      10, 255, 255, 0, 0, self.number[1])

        # todo change hold to pulse with re-ups

    def pulse(self, milliseconds=None):
        """Pulses this driver.

        FAST Protcol command DL/DN:

        DRIVER_ID
        CONTROL
        SWITCH_ID
        MODE fastpinball.FP_DRIVER_MODE_PULSED (0x10)
        PARAM1 pwm1 on time
        PARAM2 pwm 1
        PARAM3 pwm2 on time
        PARAM4 pwm 2
        PARAM 5 rest time

        Associated libfastpinball method:


        CONTROL is 193 (0xC1) which is bitwise or of:
        0x01 Driver enabled
        0x40 Manual mode trigger
        0x80 Manual mode enabled


        """

        self.log.debug('Pulsing Driver for %sms', milliseconds)
        fastpinball.fpConfigDriver(self.fast,       # fast board
                                   self.number[0],  # driver number
                                   193,             # control
                                   0,               # switch
                                   fastpinball.FP_DRIVER_MODE_PULSED,  # mode
                                   milliseconds,    # pwm 1 on time
                                   255,             # pwm 1 power
                                   0,               # pwm 2 on time
                                   0,               # pwm 2 power
                                   0,               # rest time
                                   self.number[1],  # local or network
                                   )

        self.log.info("fpConfigDriver (int): %s,%s,%s,%s,%s,%s,%s,%s,%s,%s",
                      self.number[0], 193, 0, fastpinball.FP_DRIVER_MODE_PULSED,
                      milliseconds, 255, 0, 0, 0, self.number[1])

    def pwm(self, on_ms=10, off_ms=10, original_on_ms=0, now=True):
        """Enables this driver in a pwm pattern.

        Pulses this driver.

        FAST Protcol command DL/DN:

        DRIVER_ID
        CONTROL
        SWITCH_ID
        MODE fastpinball.FP_DRIVER_MODE_PULSED (0x10)
        PARAM1 pwm1 on time
        PARAM2 pwm 1
        PARAM3 pwm2 on time
        PARAM4 pwm 2
        PARAM 5 rest time

        Associated libfastpinball method:


        CONTROL is 193 (0xC1) which is bitwise or of:
        0x01 Driver enabled
        0x40 Manual mode trigger
        0x80 Manual mode enabled

        """
        pass

        # not yet implemented. I need to figure out the best way to do the pwm
        # calculations.

        #pwm = Timing.int_to_pwm()
        #
        #self.log.debug("pwm:", pwm)
        #
        #fastpinball.fpConfigDriver(self.fast,       # fast board
        #                           self.number[0],  # driver number
        #                           193,             # control
        #                           0,               # switch
        #                           fastpinball.FP_DRIVER_MODE_LATCHED,  # mode
        #                           10,              # pwm max on time
        #                           pwm,             # pwm 1
        #                           pwm,             # pwm 2
        #                           0,               # rest time
        #                           0,               # not used
        #                           self.number[1],  # local or network
        #                           )


class FASTGIString(object):
    def __init__(self, number, fast_device):
        """ A FAST GI string in a WPC machine.

        TODO: Need to implement the enable_relay and control which strings are
        dimmable.
        """
        self.log = logging.getLogger('FASTGIString.0x' + str(number))
        self.number = number
        self.fast = fast_device

    def off(self):
        self.log.debug("Turning Off GI String")
        fastpinball.fpWriteGiString(self.fast, self.number, 0)
        self.last_time_changed = time.time()
        fastpinball.fpReadAllSwitches(self.fast)

    def on(self, brightness=255, fade_ms=0, start=0):
        if brightness >= 255:
            self.log.debug("Turning On GI String")
            fastpinball.fpWriteGiString(self.fast, self.number, 100)
        elif brightness == 0:
            self.off()
        else:
            fastpinball.fpWriteGiString(self.fast, self.number,
                                        int(brightness/255.0*100))

        self.last_time_changed = time.time()


class FASTMatrixLight(object):

    def __init__(self, number, fast_device):
        self.log = logging.getLogger('FASTMatrixLight')
        self.number = number
        self.fast = fast_device

    def off(self):
        """Disables (turns off) this driver."""
        fastpinball.fpWriteLamp(self.fast, self.number, 0)
        self.last_time_changed = time.time()

    def on(self, brightness=255, fade_ms=0, start=0):
        """Enables (turns on) this driver."""
        if brightness >= 255:
            fastpinball.fpWriteLamp(self.fast, self.number, 1)
        elif brightness == 0:
            self.off()
        else:
            pass
            # patter rates of 10/1 through 2/9

        self.last_time_changed = time.time()


class FASTDirectLED(object):

    def __init__(self, number, fast_device):
        self.log = logging.getLogger('FASTLED')
        self.fast = fast_device
        self.number = number

        self.current_color = [0, 0, 0]

        # All FAST LEDs are 3 element RGB

        self.log.debug("Creating FAST RGB LED at hardware address: %s",
                       self.number)

    def color(self, color):
        """Instantly sets this LED to the color passed.

        Args:
            color: a 3-item list of integers representing R, G, and B values,
            0-255 each.
        """
        # Pad the color with zeros to make sure we have as many colors as
        # elements
        # todo verify this is needed with FAST. It might just work without

        color += [0] * (3 - len(color))

        #self.log.info("fastpinball.fpWriteRgb(self.fast, %s, %s, %s, %s)",
        #               self.number, color[0], color[1], color[2])

        fastpinball.fpWriteRgb(self.fast, self.number, color[0], color[1],
                               color[2])

    def fade(self, color, fade_ms):
        # todo
        # not yet implemented. For now we'll just immediately set the color
        self.color(color, fade_ms)

    def disable(self):
        """Disables (turns off) this LED instantly. For multi-color LEDs it
        turns all elements off.
        """

        fastpinball.fpWriteRgb(self.fast, self.number, 0, 0, 0)

    def enable(self):
        self.color([255, 255, 255])


class FASTDMD(object):

    def __init__(self, machine, fast_device):
        self.machine = machine
        self.fast = fast_device

        # Clear the DMD
        fastpinball.fpClearDmd(self.fast)

        self.dmd_frame = bytearray()

        self.machine.events.add_handler('timer_tick', self.tick)

    def update(self, data):

        try:
            self.dmd_frame = bytearray(data)
        except TypeError:
            pass

    def tick(self):
        fastpinball.fpWriteDmd(self.fast, self.dmd_frame)


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
