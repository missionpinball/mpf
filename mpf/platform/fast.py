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
        self.features['hw_timer'] = True
        self.features['hw_rule_coil_delay'] = False  # todo
        self.features['variable_recycle_time'] = True  # todo
        self.features['variable_debounce_time'] = True  # todo
        self.features['hw_enable_auto_disable'] = True
        # Make the platform features available to everyone
        self.machine.config['platform'] = self.features
        # ----------------------------------------------------------------------

        self.hw_rules = dict()

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

        self.log.info("Fast Config. Ports: %s, Assignments: %s", ports,
                      port_assignments)

        # We need to setup a timer to get the initial switch reads, so we just
        # do this one at 1 sec now. It will be overwritten later when the
        # run loop starts
        fastpinball.fpTimerConfig(self.fast, 1000000)
        fastpinball.fpReadAllSwitches(self.fast)

        event = fastpinball.fpGetEventObject()
        fastpinball.fpGetEventType(event)
        fastpinball.fpEventPoll(self.fast, event)

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

    def timer_initialize(self):
        self.log.debug("Initializing the FAST hardware timer for %sHz",
                       Timing.HZ)
        fastpinball.fpTimerConfig(self.fast,
                                  int(Timing.secs_per_tick * 1000000))
        # timer tick is in microsecs

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

    def run_loop(self):
        """Loop code which checks the controller for any events (switch state
        changes or notification that a DMD frame was updated).

        """
        fast_events = fastpinball.fpGetEventObject()

        self.log.debug("Starting the hardware loop")

        loop_start_time = time.time()
        num_loops = 0

        while self.machine.done is False:

            try:
                self.machine.loop_rate = int(num_loops /
                                             (time.time() - loop_start_time))
            except ZeroDivisionError:
                self.machine.loop_rate = 0

            fastpinball.fpEventPoll(self.fast, fast_events)
            eventType = fastpinball.fpGetEventType(fast_events)

            # eventType options:
            #fastpinball.FP_EVENT_TYPE_NONE
            #fastpinball.FP_EVENT_TYPE_SWITCH_ACTIVE
            #fastpinball.FP_EVENT_TYPE_SWITCH_INACTIVE
            #fastpinball.FP_EVENT_TYPE_NETWORK_SWITCH_ACTIVE
            #fastpinball.FP_EVENT_TYPE_NETWORK_SWITCH_INACTIVE
            #fastpinball.FP_EVENT_TYPE_SWITCHES_UPDATED
            #fastpinball.FP_EVENT_TYPE_NETWORK_SWITCHES_UPDATED
            #fastpinball.FP_EVENT_TYPE_TIMER_TICK

            if eventType == fastpinball.FP_EVENT_TYPE_NONE:
                continue

            elif eventType == fastpinball.FP_EVENT_TYPE_TIMER_TICK:
                num_loops += 1
                self.machine.timer_tick()

            elif eventType == fastpinball.FP_EVENT_TYPE_SWITCH_ACTIVE:
                self.machine.switch_controller.process_switch(state=1,
                    num=(fastpinball.fpGetEventSwitchID(fast_events), 0))

            elif eventType == fastpinball.FP_EVENT_TYPE_SWITCH_INACTIVE:
                self.machine.switch_controller.process_switch(state=0,
                    num=(fastpinball.fpGetEventSwitchID(fast_events), 0))

            elif eventType == fastpinball.FP_EVENT_TYPE_NETWORK_SWITCH_ACTIVE:
                self.machine.switch_controller.process_switch(state=1,
                    num=(fastpinball.fpGetEventSwitchID(fast_events), 1))

            elif eventType == fastpinball.FP_EVENT_TYPE_NETWORK_SWITCH_INACTIVE:
                self.machine.switch_controller.process_switch(state=0,
                    num=(fastpinball.fpGetEventSwitchID(fast_events), 1))

        else:
            if num_loops != 0:
                self.log.info("Hardware loop speed: %sHz",
                              self.machine.loop_rate)

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
            sw:  Which switch you're creating this rule for. The parameter is a
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

        self.log.debug("Setting HW Rule. Switch:%s, Action ms:%s, Coil:%s, "
                       "Pulse:%s, pwm_on:%s, pwm_off:%s, Delay:%s, Recycle:%s,"
                       "Debounced:%s, Now:%s", sw.name, coil_action_ms,
                       coil.name, pulse_ms, pwm_on, pwm_off, delay,
                       recycle_time, debounced, drive_now)

        mode = fastpinball.FP_DRIVER_MODE_PULSED
        pwm = 32

        if pwm_on and pwm_off:  # caculate PWM value 0-32
            pwm = int(pwm_on / float(pwm_on + pwm_off) * 32)

        if coil_action_ms == -1:
                mode = fastpinball.FP_DRIVER_MODE_LATCHED

        if sw_activity == 0:  # fire this rule when switch turns off
            sw_activity = fastpinball.FP_DRIVER_TRIGGER_TYPE_SWITCH_OFF
        elif sw_activity == 1:  # fire this coil when switch turns on
            sw_activity = fastpinball.FP_DRIVER_TRIGGER_TYPE_SWITCH_ON

        self.hw_rules[coil.config['number']] = {'mode': mode,
                                                'switch': sw.number,
                                                'on': pwm_on,
                                                'off': pwm_off}

        self.log.debug("Writing HW Rule to FAST Controller. Coil: %s, "
                       "Mode: %s, Switch: %s, On: %s, Off: %s",
                       coil.number, mode, sw.number,
                       pwm_on, pwm_off)

        fastpinball.fpWriteDriver(self.fast,        # fast board
                                  coil.number[0],   # coil number
                                  mode,             # mode
                                  sw_activity,      # triggerType
                                  sw.number[0],     # switch
                                  pulse_ms,         # on time
                                  recycle_time,     # time before can enable again
                                  pwm,              # pwm (0 - 32)
                                  coil.number[1],   # local or network
                                  )
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
            fastpinball.fpWriteDriver(self.fast,    # fast board
                                      coil[0],      # coil number
                                      0,            # mode
                                      0,            # triggerType
                                      0,            # switch
                                      0,            # on time
                                      0,            # off time
                                      0,            # pwm (0-32)
                                      coil[1],      # local or network
                                      )
            # todo ensure / verify switch & coil are on the same board.

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
    """ Base class for drivers connected to a FAST Controller.

    fpWriteDriver (
                   device
                   id
                   mode (see below)
                   triggerType (see below)
                   triggerSwitch (switch id number)
                   onTime (in ms)
                   offTime (in ms)
                   pwm (int from 0 to 32)
                   target (connection type. 0 = local, 1 = network)
                   )

        mode options
            fastpinball.FP_DRIVER_MODE_PULSED
            fastpinball.FP_DRIVER_MODE_LATCHED
            fastpinball.FP_DRIVER_MODE_DELAY

        triggerType options
            fastpinball.FP_DRIVER_TRIGGER_TYPE_OFF
            fastpinball.FP_DRIVER_TRIGGER_TYPE_MANUAL
            fastpinball.FP_DRIVER_TRIGGER_TYPE_SWITCH_ON
            fastpinball.FP_DRIVER_TRIGGER_TYPE_SWITCH_OFF

    """

    def __init__(self, number, fast_device):
        self.log = logging.getLogger('FASTDriver')
        self.number = number
        self.fast = fast_device

    def disable(self):
        """Disables (turns off) this driver."""
        self.log.debug('Disabling Driver')
        fastpinball.fpWriteDriver(self.fast,        # fast board
                                  self.number[0],   # driver number
                                  fastpinball.FP_DRIVER_MODE_PULSED,  # mode
                                  fastpinball.FP_DRIVER_TRIGGER_TYPE_OFF,  # triggerType
                                  0,                # switch
                                  0,                # on time
                                  0,                # off time
                                  0,                # pwm (0 - 32)
                                  self.number[1],   # local or network
                                  )

    def enable(self):
        """Enables (turns on) this driver."""
        self.log.debug('Enabling Driver')
        fastpinball.fpWriteDriver(self.fast,        # fast board
                                  self.number[0],   # driver number
                                  fastpinball.FP_DRIVER_MODE_LATCHED,  # mode
                                  fastpinball.FP_DRIVER_TRIGGER_TYPE_MANUAL,  # triggerType
                                  0,                # switch
                                  0,                # on time
                                  0,                # off time
                                  32,                # pwm (0 - 32)
                                  self.number[1],   # local or network
                                  )
        # todo change hold to pulse with re-ups

    def pulse(self, milliseconds=None):
        """Pulses this driver.
        """

        self.log.debug('Pulsing Driver for %sms', milliseconds)
        fastpinball.fpWriteDriver(self.fast,        # fast board
                                  self.number[0],   # driver number
                                  fastpinball.FP_DRIVER_MODE_PULSED,  # mode
                                  fastpinball.FP_DRIVER_TRIGGER_TYPE_MANUAL,  # triggerType
                                  0,                # switch
                                  milliseconds,     # on time
                                  0,                # off time
                                  32,                # pwm (0 - 32)
                                  self.number[1],   # local or network
                                  )

    def pwm(self, on_ms=10, off_ms=10, original_on_ms=0, now=True):
        """Enables this driver in a pwm pattern.
        """

        pwm = int(on_ms / float(on_ms + off_ms) * 32)

        self.log.debug("pwm:", pwm)

        fastpinball.fpWriteDriver(self.fast,        # fast board
                                  self.number[0],   # driver number
                                  fastpinball.FP_DRIVER_MODE_LATCHED,  # mode
                                  fastpinball.FP_DRIVER_TRIGGER_TYPE_MANUAL,  # triggerType
                                  0,                # switch
                                  on_ms,            # on time
                                  off_ms,           # off time
                                  pwm,                # pwm (0 - 32)
                                  self.number[1],   # local or network
                                  )


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
        #fastpinball.fpReadAllSwitches(self.fast)


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

        #self.log.debug("fastpinball.fpWriteRgb(self.fast, %s, %s, %s, %s)",
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

        fastpinball.fpWriteDmd(self.fast, bytearray(data))

    def tick(self):
        pass


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
