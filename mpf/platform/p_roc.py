"""Contains the drivers and interface code for pinball machines which
use the Multimorphic R-ROC hardware controllers.

This code can be used with P-ROC driver boards, or with Stern SAM, Stern
Whitestar, Williams WPC, or Williams WPC95 driver boards.

Much of this code is from the P-ROC drivers section of the pyprocgame project,
written by Adam Preble and Gerry Stellenberg. It was originally released under
the MIT license and is released here under the MIT License.

More info on the P-ROC hardware platform: http://pinballcontrollers.com/

Original code source on which this module was based:
https://github.com/preble/pyprocgame

If you want to use the Mission Pinball Framework with P-ROC hardware, you also
need libpinproc and pypinproc. More info:
http://www.pinballcontrollers.com/forum/index.php?board=10.0

"""
# p_roc.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import re
import time
import sys

try:
    import pinproc
    pinproc_imported = True
except:
    pinproc_imported = False

from mpf.system.platform import Platform
from mpf.system.config import Config

proc_output_module = 3
proc_pdb_bus_addr = 0xC00


class HardwarePlatform(Platform):
    """Platform class for the P-ROC hardware controller.

    Args:
        machine: The MachineController instance.

    Attributes:
        machine: The MachineController instance.
        proc: The P-ROC pinproc.PinPROC device.
        machine_type: Constant of the pinproc.MachineType
    """

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger('P-ROC')
        self.log.debug("Configuring P-ROC hardware")

        if not pinproc_imported:
            self.log.error('Could not import "pinproc". Most likely you do not '
                           'have libpinproc and/or pypinproc installed. You can'
                           ' run MPF in software-only "virtual" mode by using '
                           'the -x command like option for now instead.')
            sys.exit()

        # ----------------------------------------------------------------------
        # Platform-specific hardware features. WARNING: Do not edit these. They
        # are based on what the P-ROC hardware can and cannot do.
        self.features['max_pulse'] = 255
        self.features['hw_timer'] = False
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False
        self.features['variable_debounce_time'] = False
        self.features['hw_enable_auto_disable'] = False
        self.features['hw_led_fade'] = True
        # todo need to add differences between patter and pulsed_patter

        # Make the platform features available to everyone
        self.machine.config['platform'] = self.features
        # ----------------------------------------------------------------------

        self.machine_type = pinproc.normalize_machine_type(
            self.machine.config['hardware']['driverboards'])

        # Connect to the P-ROC. Keep trying if it doesn't work the first time.

        self.proc = None

        self.log.info("Connecting to P-ROC")

        while not self.proc:
            try:
                self.proc = pinproc.PinPROC(self.machine_type)
                self.proc.reset(1)
            except IOError:
                print "Retrying..."

        self.log.info("Successfully connected to P-ROC")

        # Clear out the default program for the aux port since we might need it
        # for a 9th column. Details:
        # http://www.pinballcontrollers.com/forum/index.php?topic=1360
        commands = []
        commands += [pinproc.aux_command_disable()]

        for i in range(1, 255):
            commands += [pinproc.aux_command_jump(0)]

        self.proc.aux_send_commands(0, commands)
        # End of the clear out the default program for the aux port.

        # Because PDBs can be configured in many different ways, we need to
        # traverse the YAML settings to see how many PDBs are being used.
        # Then we can configure the P-ROC appropriately to use those PDBs.
        # Only then can we relate the YAML coil/light #'s to P-ROC numbers for
        # the collections.
        if self.machine_type == pinproc.MachineTypePDB:
            self.log.debug("Configuring P-ROC for PDBs (P-ROC driver boards)")
            self.pdbconfig = PDBConfig(self.proc, self.machine.config)

        else:
            self.log.debug("Configuring P-ROC for OEM driver boards")

        self.polarity = self.machine_type == pinproc.MachineTypeSternWhitestar\
            or self.machine_type == pinproc.MachineTypeSternSAM\
            or self.machine_type == pinproc.MachineTypePDB

    def __repr__(self):
        return '<Platform.P-ROC>'

    def configure_driver(self, config, device_type='coil'):
        """Creates a P-ROC driver.

        Typically drivers are coils or flashers, but for the P-ROC this is
        also used for matrix-based lights.

        Args:
            config: Dictionary of settings for the driver.
            device_type: String with value of either 'coil' or 'switch'.

        Returns:
            A reference to the PROCDriver object which is the actual object you
            can use to pulse(), patter(), enable(), etc.

        """
        # todo need to add Aux Bus support
        # todo need to add virtual driver support for driver counts > 256

        # Find the P-ROC number for each driver. For P-ROC driver boards, the
        # P-ROC number is specified via the Ax-By-C format. For OEM driver
        # boards configured via driver numbers, libpinproc's decode() method
        # can provide the number.

        if self.machine_type == pinproc.MachineTypePDB:
            proc_num = self.pdbconfig.get_proc_number(device_type,
                                                      str(config['number']))
            if proc_num == -1:
                self.log.error("Coil cannot be controlled by the P-ROC. "
                               "Ignoring.")
                return
        else:
            proc_num = pinproc.decode(self.machine_type, str(config['number']))

        if device_type in ['coil', 'flasher']:
            proc_driver_object = PROCDriver(proc_num, self.proc)
        elif device_type == 'light':
            proc_driver_object = PROCMatrixLight(proc_num, self.proc)

        if 'polarity' in config:
            state = proc_driver_object.proc.driver_get_state(config['number'])
            state['polarity'] = config['polarity']
            proc_driver_object.proc.driver_update_state(state)

        return proc_driver_object, config['number']

    def configure_switch(self, config):
        """Configures a P-ROC switch.

        Args:
            config: Dictionary of settings for the switch. In the case
                of the P-ROC, it uses the following:
            number : The number (or number string) for the switch as specified
                in the machine configuration file.
            debounce : Boolean which specifies whether the P-ROC should debounce
                this switch first before sending open and close notifications to
                the host computer.

        Returns:
            switch : A reference to the switch object that was just created.
            proc_num : Integer of the actual hardware switch number the P-ROC
                uses to refer to this switch. Typically your machine
                configuration files would specify a switch number like `SD12` or
                `7/5`. This `proc_num` is an int between 0 and 255.
            state : An integer of the current hardware state of the switch, used
                to set the initial state state in the machine. A value of 0
                means the switch is open, and 1 means it's closed. Note this
                state is the physical state of the switch, so if you configure
                the switch to be normally-closed (i.e. "inverted" then your code
                will have to invert it too.) MPF handles this automatically if
                the switch type is 'NC'.

        """

        if self.machine_type == pinproc.MachineTypePDB:
            proc_num = self.pdbconfig.get_proc_number('switch',
                                                      str(config['number']))
            if config['number'] == -1:
                self.log.error("Switch cannot be controlled by the P-ROC. "
                               "Ignoring.")
                return
        else:
            proc_num = pinproc.decode(self.machine_type, str(config['number']))

        switch = PROCSwitch(proc_num)
        # The P-ROC needs to be configured to notify the host computers of
        # switch events. (That notification can be for open or closed,
        # debounced or nondebounced.)
        self.log.debug("Configuring switch's host notification settings. P-ROC"
                       "number: %s, debounce: %s", proc_num,
                       config['debounce'])
        if config['debounce'] is False or \
                proc_num >= pinproc.SwitchNeverDebounceFirst:
            self.proc.switch_update_rule(proc_num, 'closed_nondebounced',
                                         {'notifyHost': True,
                                          'reloadActive': False}, [], False)
            self.proc.switch_update_rule(proc_num, 'open_nondebounced',
                                         {'notifyHost': True,
                                          'reloadActive': False}, [], False)
        else:
            self.proc.switch_update_rule(proc_num, 'closed_debounced',
                                         {'notifyHost': True,
                                          'reloadActive': False}, [], False)
            self.proc.switch_update_rule(proc_num, 'open_debounced',
                                         {'notifyHost': True,
                                          'reloadActive': False}, [], False)

        # Read in and set the initial switch state
        # The P-ROC uses the following values for hw switch states:
        # 1 - closed (debounced)
        # 2 - open (debounced)
        # 3 - closed (not debounced)
        # 4 - open (not debounced)

        states = self.proc.switch_get_states()
        if states[proc_num] == 1 or states[proc_num] == 3:
            state = 1
        else:
            state = 0

        # Return the switch object and an integer of its current state.
        # 1 = active, 0 = inactive
        return switch, proc_num, state

    def configure_led(self, config):
        """ Configures a P-ROC RGB LED controlled via a PD-LED."""

        # todo add polarity

        # split the number (which comes in as a string like w-x-y-z) into parts
        config['number'] = config['number_str'].split('-')

        if 'polarity' in config:
            invert = not config['polarity']
        else:
            invert = False

        return PDBLED(board=int(config['number'][0]),
                      address=[int(config['number'][1]),
                               int(config['number'][2]),
                               int(config['number'][3])],
                      proc_driver=self.proc,
                      invert=invert)

    def configure_matrixlight(self, config):
        """Configures a P-ROC matrix light."""
        # On the P-ROC, matrix lights are drivers
        return self.configure_driver(config, 'light')

    def configure_gi(self, config):
        """Configures a P-ROC GI string light."""
        # On the P-ROC, GI strings are drivers
        return self.configure_driver(config, 'light')

    def configure_dmd(self):
        """Configures a hardware DMD connected to a classic P-ROC."""
        return PROCDMD(self.proc, self.machine)

    def tick(self):
        """Checks the P-ROC for any events (switch state changes or notification
        that a DMD frame was updated).

        Also tickles the watchdog and flushes any queued commands to the P-ROC.

        """
        # Get P-ROC events (switches & DMD frames displayed)
        for event in self.proc.get_events():
            event_type = event['type']
            event_value = event['value']
            if event_type == 99:  # CTRL-C to quit todo does this go here?
                self.machine.quit()
            elif event_type == pinproc.EventTypeDMDFrameDisplayed:
                pass
            elif event_type == pinproc.EventTypeSwitchClosedDebounced:
                self.machine.switch_controller.process_switch(state=1,
                                                              num=event_value)
            elif event_type == pinproc.EventTypeSwitchOpenDebounced:
                self.machine.switch_controller.process_switch(state=0,
                                                              num=event_value)
            elif event_type == pinproc.EventTypeSwitchClosedNondebounced:
                self.machine.switch_controller.process_switch(state=1,
                                                              num=event_value,
                                                              debounced=False)
            elif event_type == pinproc.EventTypeSwitchOpenNondebounced:
                self.machine.switch_controller.process_switch(state=0,
                                                              num=event_value,
                                                              debounced=False)
            else:
                self.log.warning("Received unrecognized event from the P-ROC. "
                                 "Type: %s, Value: %s", event_type, event_value)

        self.proc.watchdog_tickle()
        self.proc.flush()

    def write_hw_rule(self,
                        sw,
                        sw_activity,
                        coil_action_ms,  # 0 = disable, -1 = hold forever
                        coil=None,
                        pulse_ms=0,
                        pwm_on=0,
                        pwm_off=0,
                        delay=0,
                        recycle_time=0,
                        debounced=True,
                        drive_now=False):

        """Used to write (or update) a hardware rule to the P-ROC.

        *Hardware Rules* are used to configure the P-ROC to automatically
        change driver states based on switch changes. These rules are
        completely handled by the P-ROC hardware (i.e. with no interaction from
        the Python game code). They're used for things that you want to happen
        fast, like firing coils when flipper buttons are pushed, slingshots,
        pop bumpers, etc.

        You can overwrite existing hardware rules at any time to change or
        remove them.

        Parameters
        ----------
            sw : switch object
                Which switch you're creating this rule for. The parameter is a
                reference to the switch object itsef.
            sw_activity : int
                Do you want this coil to fire when the switch becomes active
                (1) or inactive (0)
            coil_action_ms : int
                The total time (in ms) that this coil action should take place.
                A value of -1 means it's forever.
            coil : coil object
                Which coil is this rule controlling
            pulse_ms : int
                How long should the coil be pulsed (ms)
            pwm_on : int
                If the coil should be held on at less than 100% duty cycle,
                this is the "on" time (in ms).
            pwm_off : int
                If the coil should be held on at less than 100% duty cycle,
                this is the "off" time (in ms).
            delay : int
                Not currently implemented for the P-ROC hardware
            recycle_time : int
                How long (in ms) should this switch rule wait before firing
                again. Put another way, what's the "fastest" this rule can
                fire? This is used to prevent "machine gunning" of slingshots
                and pop bumpers. Do not use it with flippers. Note the P-ROC
                has a non-configurable delay time of 125ms. (So it's either
                125ms or 0.) So if you set this delay to anything other than
                0, it will be 125ms.
            debounced : bool
                Should the P-ROC fire this coil after the switch has been
                debounced? Typically no.
            drive_now : bool
                Should the P-ROC check the state of the switches when this
                rule is firts applied, and fire the coils if they should be?
                Typically this is True, especially with flippers because you
                want them to fire if the player is holding in the buttons when
                the machine enables the flippers (which is done via several
                calls to this method.)

        """

        self.log.debug("Setting HW Rule. Switch:%s, Action ms:%s, Coil:%s, "
                       "Pulse:%s, pwm_on:%s, pwm_off:%s, Delay:%s, Recycle:%s,"
                       "Debounced:%s, Now:%s", sw.name, coil_action_ms,
                       coil.name, pulse_ms, pwm_on, pwm_off, delay,
                       recycle_time, debounced, drive_now)

        if (sw_activity == 0 and debounced):
            event_type = "open_debounced"
        elif (sw_activity == 0 and not debounced):
            event_type = "open_nondebounced"
        elif (sw_activity == 1 and debounced):
            event_type = "closed_debounced"
        else:  # if sw_activity == 1 and not debounced:
            event_type = "closed_nondebounced"

        # Note the P-ROC uses a 125ms non-configurable recycle time. So any
        # non-zero value passed here will enable the 125ms recycle.

        reloadActive = False
        if recycle_time:
            reloadActive = True

        # We only want to notifyHost for debounced switch events. We use non-
        # debounced for hw_rules since they're faster, but we don't want to
        # notify the host on them since the host would then get two events
        # one for the nondebounced followed by one for the debounced.

        notifyHost = False
        if debounced:
            notifyHost = True

        rule = {'notifyHost': notifyHost, 'reloadActive': reloadActive}

        # Now let's figure out what type of P-ROC action we need to take.
        # We're going to 'brtue force' this here because it's the easiest to
        # understand. (Which makes it the most pythonic, right? :)

        proc_action = 'disable'

        patter = False  # makes it easier to understand later...
        if pwm_on and pwm_off:
            patter = True

        if coil_action_ms == -1:  # hold coil forever
            if patter:
                proc_action = 'patter'
            else:
                proc_action = 'enable'
        elif coil_action_ms > 0:  # timed action of some sort
            if coil_action_ms <= pulse_ms:
                proc_action = 'pulse'
                pulse_ms = coil_action_ms
            elif patter:
                if pulse_ms:
                    pass
                    # todo error, P-ROC can't do timed patter with pulse
                else:  # no initial pulse
                    proc_action = 'pulsed_patter'

        this_driver = []
        final_driver = []

        # The P-ROC ties hardware rules to switches, with a list of linked
        # drivers that should change state based on a switch activity.
        # Since our framework applies the rules one-at-a-time, we have to read
        # the existing linked drivers from the hardware for that switch, add
        # our new driver to the list, then re-update the rule on the hardware.

        if proc_action == 'pulse':
            this_driver = [pinproc.driver_state_pulse(
                coil.hw_driver.state(), pulse_ms)]

        elif proc_action == 'patter':
            this_driver = [pinproc.driver_state_patter(
                coil.hw_driver.state(), pwm_on, pwm_off, pulse_ms, True)]
            # todo above param True should not be there. Change to now?

        elif proc_action == 'enable':
            this_driver = [pinproc.driver_state_pulse(
                coil.hw_driver.state(), 0)]

        elif proc_action == 'disable':
            this_driver = [pinproc.driver_state_disable(
                coil.hw_driver.state())]

        elif proc_action == 'pulsed_patter':
            this_driver = [pinproc.driver_state_pulsed_patter(
                coil.hw_driver.state(), pwm_on, pwm_off,
                coil_action_ms)]

        # merge in any previously-configured driver rules for this switch

        final_driver = list(this_driver)  # need to make an actual copy
        sw_rule_string = str(sw.name)+str(event_type)
        if sw_rule_string in self.hw_switch_rules:
            for driver in self.hw_switch_rules[sw_rule_string]:
                final_driver.append(driver)
            self.hw_switch_rules[sw_rule_string].extend(this_driver)
        else:
            self.hw_switch_rules[sw_rule_string] = this_driver

        self.log.debug("Writing HW rule for switch: %s, event_type: %s,"
                       "rule: %s, final_driver: %s, drive now: %s",
                       sw.number, event_type,
                       rule, final_driver, drive_now)
        self.proc.switch_update_rule(sw.number, event_type, rule, final_driver,
                                     drive_now)

    def clear_hw_rule(self, sw_name):
        """Clears a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        Parameters
        ----------

        sw_num : int
            The number of the switch whose rule you want to clear.

        """
        sw_num = self.machine.switches[sw_name].number

        self.log.debug("Clearing HW rule for switch: %s", sw_num)

        self.proc.switch_update_rule(sw_num, 'open_nondebounced',
                                     {'notifyHost': False,
                                      'reloadActive': False}, [])
        self.proc.switch_update_rule(sw_num, 'closed_nondebounced',
                                     {'notifyHost': False,
                                      'reloadActive': False}, [])
        self.proc.switch_update_rule(sw_num, 'open_debounced',
                                     {'notifyHost': True,
                                      'reloadActive': False}, [])
        self.proc.switch_update_rule(sw_num, 'closed_debounced',
                                     {'notifyHost': True,
                                      'reloadActive': False}, [])

        for entry in self.hw_switch_rules.keys():  # slice for copy
            if entry.startswith(self.machine.switches.number(sw_num).name):

                # disable any drivers from this rule which are active now
                # todo make this an option?
                for driver_dict in self.hw_switch_rules[entry]:
                    self.proc.driver_disable(driver_dict['driverNum'])

                # Remove this rule from our list
                del self.hw_switch_rules[entry]

        # todo need to read in the notifyHost settings and reapply those
        # appropriately.


class PDBLED(object):
    """Represents an RGB LED connected to a PD-LED board."""

    def __init__(self, board, address, proc_driver, invert=False):
        self.log = logging.getLogger('PDBLED')
        self.board = board
        self.address = address
        self.proc = proc_driver
        self.invert = invert

        # todo make sure self.address is a 3-element list

        self.log.debug("Creating PD-LED item: board: %s, "
                       "RGB outputs: %s", self.board,
                        self.address)

    def color(self, color):
        """Instantly sets this LED to the color passed.

        Args:
            color: a 3-item list of integers representing R, G, and B values,
            0-255 each.
        """

        #self.log.debug("Setting Color. Board: %s, Address: %s, Color: %s",
        #               self.board, self.address, color)

        self.proc.led_color(self.board, self.address[0],
                            self.normalize_color(color[0]))
        self.proc.led_color(self.board, self.address[1],
                            self.normalize_color(color[1]))
        self.proc.led_color(self.board, self.address[2],
                            self.normalize_color(color[2]))

    def fade(self, color, fade_ms):
        # todo
        # not implemented. For now we'll just immediately set the color
        self.color(color, fade_ms)

    def disable(self):
        """Disables (turns off) this LED instantly. For multi-color LEDs it
        turns all elements off.
        """

        self.proc.led_color(self.board, self.address[0],
                            self.normalize_color(0))
        self.proc.led_color(self.board, self.address[1],
                            self.normalize_color(0))
        self.proc.led_color(self.board, self.address[2],
                            self.normalize_color(0))

    def enable(self):
        """Enables (turns on) this LED instantly. For multi-color LEDs it turns
        all elements on.
        """

        self.color(self.normalize_color(255),
                   self.normalize_color(255),
                   self.normalize_color(255)
                   )

    def normalize_color(self, color):
        if self.invert:
            return 255-color
        else:
            return color


class PDBSwitch(object):
    """Base class for switches connected to a P-ROC."""
    def __init__(self, pdb, number_str):
        upper_str = number_str.upper()
        if upper_str.startswith('SD'):
            self.sw_type = 'dedicated'
            self.sw_number = int(upper_str[2:])
        elif '/' in upper_str:
            self.sw_type = 'matrix'
            self.sw_number = self.parse_matrix_num(upper_str)
        else:
            self.sw_type = 'proc'
            self.sw_number = int(number_str)

    def proc_num(self):
        return self.sw_number

    def parse_matrix_num(self, num_str):
        cr_list = num_str.split('/')
        return (32 + int(cr_list[0])*16 + int(cr_list[1]))


class PDBCoil(object):
    """Base class for coils connected to a P-ROC that are controlled via P-ROC
    driver boards (i.e. the PD-16 board).

    """
    def __init__(self, pdb, number_str):
        self.pdb = pdb
        upper_str = number_str.upper()
        if self.is_direct_coil(upper_str):
            self.coil_type = 'dedicated'
            self.banknum = (int(number_str[1:]) - 1)/8
            self.outputnum = int(number_str[1:])
        elif self.is_pdb_coil(number_str):
            self.coil_type = 'pdb'
            (self.boardnum, self.banknum, self.outputnum) = decode_pdb_address(
                number_str, self.pdb.aliases)
        else:
            self.coil_type = 'unknown'

    def bank(self):
        if self.coil_type == 'dedicated':
            return self.banknum
        elif self.coil_type == 'pdb':
            return self.boardnum * 2 + self.banknum
        else:
            return -1

    def output(self):
        return self.outputnum

    def is_direct_coil(self, string):
        if len(string) < 2 or len(string) > 3:
            return False
        if not string[0] == 'C':
            return False
        if not string[1:].isdigit():
            return False
        return True

    def is_pdb_coil(self, string):
        return is_pdb_address(string, self.pdb.aliases)


class PDBLight(object):
    """Base class for lights connected to a PD-8x8 driver board."""
    def __init__(self, pdb, number_str):
        self.pdb = pdb
        upper_str = number_str.upper()
        if self.is_direct_lamp(upper_str):
            self.lamp_type = 'dedicated'
            self.output = int(number_str[1:])
        elif self.is_pdb_lamp(number_str):
            # C-Ax-By-z:R-Ax-By-z  or  C-x/y/z:R-x/y/z
            self.lamp_type = 'pdb'
            source_addr, sink_addr = self.split_matrix_addr_parts(number_str)
            (self.source_boardnum, self.source_banknum, self.source_outputnum)\
                = decode_pdb_address(source_addr, self.pdb.aliases)
            (self.sink_boardnum, self.sink_banknum, self.sink_outputnum)\
                = decode_pdb_address(sink_addr, self.pdb.aliases)
        else:
            self.lamp_type = 'unknown'

    def source_board(self):
        return self.source_boardnum

    def sink_board(self):
        return self.sink_boardnum

    def source_bank(self):
        return self.source_boardnum * 2 + self.source_banknum

    def sink_bank(self):
        return self.sink_boardnum * 2 + self.sink_banknum

    def source_output(self):
        return self.source_outputnum

    def sink_output(self):
        return self.sink_outputnum

    def dedicated_bank(self):
        return self.banknum

    def dedicated_output(self):
        return self.output

    def is_direct_lamp(self, string):
        if len(string) < 2 or len(string) > 3:
            return False
        if not string[0] == 'L':
            return False
        if not string[1:].isdigit():
            return False
        return True

    def split_matrix_addr_parts(self, string):
        """ Input is of form C-Ax-By-z:R-Ax-By-z  or  C-x/y/z:R-x/y/z  or
        aliasX:aliasY.  We want to return only the address part: Ax-By-z,
        x/y/z, or aliasX.  That is, remove the two character prefix if present.
        """
        addrs = string.rsplit(':')
        if len(addrs) is not 2:
            return []
        addrs_out = []
        for addr in addrs:
            bits = addr.split('-')
            if len(bits) is 1:
                addrs_out.append(addr)  # Append unchanged.
            else:  # Generally this will be len(bits) 2 or 4.
                # Remove the first bit and rejoin.
                addrs_out.append('-'.join(bits[1:]))
        return addrs_out

    def is_pdb_lamp(self, string):
        params = self.split_matrix_addr_parts(string)
        if len(params) != 2:
            return False
        for addr in params:
            if not is_pdb_address(addr, self.pdb.aliases):
                return False
        return True


class PROCSwitch(object):
    def __init__(self, number):
        self.log = logging.getLogger('PROCSwitch')
        self.number = number


class PROCDriver(object):
    """ Base class for drivers connected to a P-ROC. This class is used for all
    drivers, regardless of whether they're connected to a P-ROC driver board
    (such as the PD-16 or PD-8x8) or an OEM driver board.

    """

    def __init__(self, number, proc_driver):
        self.log = logging.getLogger('PROCDriver')
        self.number = number
        self.proc = proc_driver

    def disable(self):
        """Disables (turns off) this driver."""
        self.log.debug('Disabling Driver')
        self.proc.driver_disable(self.number)

    def enable(self):
        """Enables (turns on) this driver."""
        self.log.debug('Enabling Driver')
        self.proc.driver_schedule(number=self.number, schedule=0xffffffff,
                                  cycle_seconds=0, now=True)

    def pulse(self, milliseconds=None):
        """Enables this driver for `milliseconds`.

        ``ValueError`` will be raised if `milliseconds` is outside of the range
        0-255.
        """
        if not milliseconds in range(256):
            raise ValueError('milliseconds must be in range 0-255.')
        self.log.debug('Pulsing Driver %s for %sms', self.number, milliseconds)
        self.proc.driver_pulse(self.number, milliseconds)

    def future_pulse(self, milliseconds=None, timestamp=0):
        """Enables this driver for `milliseconds` at P-ROC timestamp:
        `timestamp`. If no parameter is provided for `milliseconds`,
        :attr:`pulse_ms` is used. If no parameter is provided or
        `timestamp`, 0 is used. ``ValueError`` will be raised if `milliseconds`
        is outside of the range 0-255.
        """
        if milliseconds is None:
            milliseconds = self.config['pulse_ms']
        if not milliseconds in range(256):
            raise ValueError('milliseconds must be in range 0-255.')
        self.log.debug("Driver %s - future pulse %d", self.name,
                          milliseconds, timestamp)
        self.proc.driver_future_pulse(self.number, milliseconds,
                                           timestamp)

    def pwm(self, on_ms=10, off_ms=10, original_on_ms=0, now=True):
        """Enables a pitter-patter sequence.

        It starts by activating the driver for `original_on_ms` milliseconds.
        Then it repeatedly turns the driver on for `on_ms` milliseconds and
        off for `off_ms` milliseconds.
        """

        if not original_on_ms in range(256):
            raise ValueError('original_on_ms must be in range 0-255.')
        if not on_ms in range(128):
            raise ValueError('on_ms must be in range 0-127.')
        if not off_ms in range(128):
            raise ValueError('off_ms must be in range 0-127.')

        self.log.debug("Patter on:%d, off:%d, orig_on:%d, now:%s", on_ms,
                       off_ms, original_on_ms, now)
        self.proc.driver_patter(self.number, on_ms, off_ms, original_on_ms, now)

    def timed_pwm(self, on_ms=10, off_ms=10, run_time=0, now=True):
        """Enables a pitter-patter sequence that runs for `run_time`
        milliseconds.

        Until it ends, the sequence repeatedly turns the driver on for
        `on_ms`  milliseconds and off for `off_ms` milliseconds.
        """

        if not run_time in range(256):
            raise ValueError('run_time must be in range 0-255.')
        if not on_ms in range(128):
            raise ValueError('on_ms must be in range 0-127.')
        if not off_ms in range(128):
            raise ValueError('off_ms must be in range 0-127.')

        self.log.debug("Driver %s - pulsed patter on:%d, off:%d,"
                          "run_time:%d, now:%s", self.name, on_ms, off_ms,
                          run_time, now)
        self.proc.driver_pulsed_patter(self.number, on_ms, off_ms,
                                            run_time, now)
        self.last_time_changed = time.time()

    def schedule(self, schedule, cycle_seconds=0, now=True):
        """Schedules this driver to be enabled according to the given
        `schedule` bitmask."""
        self.log.debug("Driver %s - schedule %08x", self.name, schedule)
        self.proc.driver_schedule(number=self.number, schedule=schedule,
                                       cycle_seconds=cycle_seconds, now=now)
        self.last_time_changed = time.time()

    def state(self):
        """Returns a dictionary representing this driver's current
        configuration state.
        """
        return self.proc.driver_get_state(self.number)

    def tick(self):
        pass


class PROCMatrixLight(object):

    def __init__(self, number, proc_driver):
        self.log = logging.getLogger('PROCMatrixLight')
        self.number = number
        self.proc = proc_driver

    def off(self):
        """Disables (turns off) this driver."""
        self.proc.driver_disable(self.number)
        self.last_time_changed = time.time()

    def on(self, brightness=255, fade_ms=0, start=0):
        """Enables (turns on) this driver."""
        if brightness >= 255:
            self.proc.driver_schedule(number=self.number, schedule=0xffffffff,
                                      cycle_seconds=0, now=True)
        elif brightness == 0:
            self.off()
        else:
            pass
            # patter rates of 10/1 through 2/9

        self.last_time_changed = time.time()

        '''
        Koen's fade code he posted to pinballcontrollers:
        def mode_tick(self):
            if self.fade_counter % 10 == 0:
                for lamp in self.game.lamps:
                    if lamp.name.find("gi0") == -1:
                        var = 4.0*math.sin(0.02*float(self.fade_counter)) + 5.0
                        on_time = 11-round(var)
                        off_time = round(var)
                        lamp.patter(on_time, off_time)
                self.fade_counter += 1
        '''


class PDBConfig(object):
    """ This class is only used when the P-ROC is configured to use P-ROC
    driver boards such as the PD-16 or PD-8x8. i.e. not when it's operating in
    WPC or Stern mode.

    """
    indexes = []
    proc = None
    aliases = None  # set in __init__

    def __init__(self, proc, config):

        self.log = logging.getLogger('PDBConfig')
        self.log.debug("Processing P-ROC Driver Board configuration")

        self.proc = proc

        # Set config defaults
        if 'P_ROC' in config and 'lamp_matrix_strobe_time' \
                in config['P_ROC']:
            self.lamp_matrix_strobe_time = int(config['P_ROC']
                                               ['lamp_matrix_strobe_time'])
        else:
            self.lamp_matrix_strobe_time = 100

        if 'P_ROC' in config and 'watchdog_time' \
                in config['P_ROC']:
            self.watchdog_time = int(config['P_ROC']
                                           ['watchdog_time'])
        else:
            self.watchdog_time = 1000

        if 'P_ROC' in config and 'use_watchdog' \
                in config['P_ROC']:
            self.use_watchdog = config['P_ROC']['use_watchdog']
        else:
            self.use_watchdog = True

        # Initialize some lists for data collecting
        coil_bank_list = []
        lamp_source_bank_list = []
        lamp_list = []
        lamp_list_for_index = []

        self.aliases = []
        if 'PRDriverAliases' in config:
            for alias_dict in config['PRDriverAliases']:
                alias = DriverAlias(alias_dict['expr'], alias_dict['repl'])
                self.aliases.append(alias)

        # Make a list of unique coil banks
        if 'coils' in config:
            for name in config['coils']:
                item_dict = config['coils'][name]
                coil = PDBCoil(self, str(item_dict['number']))
                if coil.bank() not in coil_bank_list:
                    coil_bank_list.append(coil.bank())

        # Make a list of unique lamp source banks.  The P-ROC only supports 2.
        # TODO: What should be done if 2 is exceeded?
        if 'matrix_lights' in config:
            for name in config['matrix_lights']:
                item_dict = config['matrix_lights'][name]
                lamp = PDBLight(self, str(item_dict['number']))

                # Catalog PDB banks
                # Dedicated lamps don't use PDB banks. They use P-ROC direct
                # driver pins.
                if lamp.lamp_type == 'dedicated':
                    pass

                elif lamp.lamp_type == 'pdb':
                    if lamp.source_bank() not in lamp_source_bank_list:
                        lamp_source_bank_list.append(lamp.source_bank())

                    # Create dicts of unique sink banks.  The source index is
                    # needed when setting up the driver groups.
                    lamp_dict = {'source_index':
                                 lamp_source_bank_list.index(
                                 lamp.source_bank()),
                                 'sink_bank': lamp.sink_bank(),
                                 'source_output': lamp.source_output()}

                    # lamp_dict_for_index.  This will be used later when the
                    # p-roc numbers are requested.  The requestor won't know
                    # the source_index, but it will know the source board.
                    # This is why two separate lists are needed.
                    lamp_dict_for_index = {'source_board': lamp.source_board(),
                                           'sink_bank': lamp.sink_bank(),
                                           'source_output':
                                           lamp.source_output()}

                    if lamp_dict not in lamp_list:
                        lamp_list.append(lamp_dict)
                        lamp_list_for_index.append(lamp_dict_for_index)

        # Create a list of indexes.  The PDB banks will be mapped into this
        # list. The index of the bank is used to calculate the P-ROC driver
        # number for each driver.
        num_proc_banks = pinproc.DriverCount/8
        self.indexes = [99] * num_proc_banks

        self.initialize_drivers(proc)

        # Set up dedicated driver groups (groups 0-3).
        for group_ctr in range(0, 4):
            # TODO: Fix this.  PDB Banks 0-3 are also interpreted as dedicated
            # bank here.
            enable = group_ctr in coil_bank_list
            self.log.debug("Driver group %02d (dedicated): Enable=%s",
                           group_ctr, enable)
            proc.driver_update_group_config(group_ctr,
                                            0,
                                            group_ctr,
                                            0,
                                            0,
                                            False,
                                            True,
                                            enable,
                                            True)

        group_ctr += 1

        # Process lamps first. The P-ROC can only control so many drivers
        # directly. Since software won't have the speed to control lamp
        # matrixes, map the lamps first. If there aren't enough P-ROC driver
        # groups for coils, the overflow coils can be controlled by software
        # via VirtualDrivers (which should get set up automatically by this
        # code.)

        for i, lamp_dict in enumerate(lamp_list):
            # If the bank is 16 or higher, the P-ROC can't control it
            # directly. Software can't really control lamp matrixes either
            # (need microsecond resolution).  Instead of doing crazy logic here
            # for a case that probably won't happen, just ignore these banks.
            if (group_ctr >= num_proc_banks or lamp_dict['sink_bank'] >= 16):
                self.log.error("Lamp matrix banks can't be mapped to index "
                                  "%d because that's outside of the banks the "
                                  "P-ROC can control.", lamp_dict['sink_bank'])
            else:
                self.log.debug("Driver group %02d (lamp sink): slow_time=%d "
                                 "enable_index=%d row_activate_index=%d "
                                 "row_enable_index=%d matrix=%s", group_ctr,
                                 self.lamp_matrix_strobe_time,
                                 lamp_dict['sink_bank'],
                                 lamp_dict['source_output'],
                                 lamp_dict['source_index'], True )
                self.indexes[group_ctr] = lamp_list_for_index[i]
                proc.driver_update_group_config(group_ctr,
                                                self.lamp_matrix_strobe_time,
                                                lamp_dict['sink_bank'],
                                                lamp_dict['source_output'],
                                                lamp_dict['source_index'],
                                                True,
                                                True,
                                                True,
                                                True)
                group_ctr += 1

        for coil_bank in coil_bank_list:
            # If the bank is 16 or higher, the P-ROC can't control it directly.
            # Software will have do the driver logic and write any changes to
            # the PDB bus. Therefore, map these banks to indexes above the
            # P-ROC's driver count, which will force the drivers to be created
            # as VirtualDrivers. Appending the bank avoids conflicts when
            # group_ctr gets too high.

            if (group_ctr >= num_proc_banks or coil_bank >= 16):
                self.log.warning("Driver group %d mapped to driver index"
                                 "outside of P-ROC control.  These Drivers "
                                 "will become VirtualDrivers.  Note, the "
                                 "index will not match the board/bank "
                                 "number; so software will need to request "
                                 "those values before updating the "
                                 "drivers.", coil_bank)
                self.indexes.append(coil_bank)
            else:
                self.log.debug("Driver group %02d: slow_time=%d Enable "
                                 "Index=%d", group_ctr, 0, coil_bank)
                self.indexes[group_ctr] = coil_bank
                proc.driver_update_group_config(group_ctr,
                                                0,
                                                coil_bank,
                                                0,
                                                0,
                                                False,
                                                True,
                                                True,
                                                True)
                group_ctr += 1

        for i in range(group_ctr, 26):
            self.log.debug("Driver group %02d: disabled", i)
            proc.driver_update_group_config(i,
                                            self.lamp_matrix_strobe_time,
                                            0,
                                            0,
                                            0,
                                            False,
                                            True,
                                            False,
                                            True)

        # Make sure there are two indexes.  If not, fill them in.
        while len(lamp_source_bank_list) < 2:
            lamp_source_bank_list.append(0)

        # Now set up globals.  First disable them to allow the P-ROC to set up
        # the polarities on the Drivers.  Then enable them.
        self.configure_globals(proc, lamp_source_bank_list, False)
        self.configure_globals(proc, lamp_source_bank_list, True)

    def initialize_drivers(self, proc):
        # Loop through all of the drivers, initializing them with the polarity.
        for i in range(0, 208):
            state = {'driverNum': i,
                     'outputDriveTime': 0,
                     'polarity': True,
                     'state': False,
                     'waitForFirstTimeSlot': False,
                     'timeslots': 0,
                     'patterOnTime': 0,
                     'patterOffTime': 0,
                     'patterEnable': False,
                     'futureEnable': False}

            proc.driver_update_state(state)

    def configure_globals(self, proc, lamp_source_bank_list, enable=True):

        if enable:
            self.log.debug("Configuring PDB Driver Globals:  polarity = %s  "
                           "matrix column index 0 = %d  matrix column index "
                           "1 = %d", True, lamp_source_bank_list[0],
                             lamp_source_bank_list[1]);
        proc.driver_update_global_config(enable,  # Don't enable outputs yet
                                         True,  # Polarity
                                         False,  # N/A
                                         False,  # N/A
                                         1,  # N/A
                                         lamp_source_bank_list[0],
                                         lamp_source_bank_list[1],
                                         False,  # Active low rows? No
                                         False,  # N/A
                                         False,  # Stern? No
                                         False,  # Reset watchdog trigger
                                         self.use_watchdog,  # Enable watchdog
                                         self.watchdog_time)

        # Now set up globals
        proc.driver_update_global_config(True,  # Don't enable outputs yet
                                         True,  # Polarity
                                         False,  # N/A
                                         False,  # N/A
                                         1,  # N/A
                                         lamp_source_bank_list[0],
                                         lamp_source_bank_list[1],
                                         False,  # Active low rows? No
                                         False,  # N/A
                                         False,  # Stern? No
                                         False,  # Reset watchdog trigger
                                         self.use_watchdog,  # Enable watchdog
                                         self.watchdog_time)

    def get_proc_number(self, device_type, number_str):
        """Returns the P-ROC number for the requested driver string.

        This method uses the driver string to look in the indexes list that
        was set up when the PDBs were configured.  The resulting P-ROC index
        * 3 is the first driver number in the group, and the driver offset is
        to that.

        """
        if device_type == 'coil':
            coil = PDBCoil(self, number_str)
            bank = coil.bank()
            if bank == -1:
                return (-1)
            index = self.indexes.index(coil.bank())
            num = index * 8 + coil.output()
            return num

        if device_type == 'light':
            lamp = PDBLight(self, number_str)
            if lamp.lamp_type == 'unknown':
                return (-1)
            elif lamp.lamp_type == 'dedicated':
                return lamp.dedicated_output()

            lamp_dict_for_index = {'source_board': lamp.source_board(),
                                   'sink_bank': lamp.sink_bank(),
                                   'source_output': lamp.source_output()}
            if lamp_dict_for_index not in self.indexes:
                return -1
            index = self.indexes.index(lamp_dict_for_index)
            num = index * 8 + lamp.sink_output()
            return num

        if device_type == 'switch':
            switch = PDBSwitch(self, number_str)
            num = switch.proc_num()
            return num


class DriverAlias(object):
    def __init__(self, key, value):
        self.expr = re.compile(key)
        self.repl = value

    def matches(self, addr):
        return self.expr.match(addr)

    def decode(self, addr):
        return self.expr.sub(repl=self.repl, string=addr)


def is_pdb_address(addr, aliases=[]):
    """Returne True if the given address is a valid PDB address."""
    try:
        decode_pdb_address(addr=addr, aliases=aliases)
        return True
    except:
        return False


def decode_pdb_address(addr, aliases=[]):
    """Decodes Ax-By-z or x/y/z into PDB address, bank number, and output
    number.

    Raises a ValueError exception if it is not a PDB address, otherwise returns
    a tuple of (addr, bank, number).

    """
    for alias in aliases:
        if alias.matches(addr):
            addr = alias.decode(addr)
            break

    if '-' in addr:  # Ax-By-z form
        params = addr.rsplit('-')
        if len(params) != 3:
            raise ValueError('pdb address must have 3 components')
        board = int(params[0][1:])
        bank = int(params[1][1:])
        output = int(params[2][0:])
        return (board, bank, output)

    elif '/' in addr:  # x/y/z form
        params = addr.rsplit('/')
        if len(params) != 3:
            raise ValueError('pdb address must have 3 components')
        board = int(params[0])
        bank = int(params[1])
        output = int(params[2])
        return (board, bank, output)

    else:
        raise ValueError('PDB address delimeter (- or /) not found.')


class PROCDMD(object):
    """Parent class for a physical DMD attached to a P-ROC.

    Args:
        proc: Reference to the MachineController's proc attribute.
        machine: Reference to the MachineController

    Attributes:
        dmd: Rerence to the P-ROC's DMD buffer.

    """

    def __init__(self, proc, machine):
        self.proc = proc
        self.machine = machine
        self.dmd = pinproc.DMDBuffer(128, 32)
        # size is hardcoded here since 128x32 is all the P-ROC hw supports

        # dmd_timing defaults should be 250, 400, 180, 800

        if 'P_ROC' in self.machine.config and (
            'dmd_timing_cycles' in self.machine.config['P_ROC']):

            dmd_timing = Config.string_to_list(
                self.machine.config['P_ROC']['dmd_timing_cycles'])

            dmd_timing = [int(i) for i in dmd_timing]

            self.proc.dmd_update_config(high_cycles=dmd_timing)

        self.machine.events.add_handler('timer_tick', self.tick)

    def update(self, data):
        """Updates the DMD with a new frame.

        Args:
            data: A 4096-byte raw string.

        """
        if len(data) == 4096:
            self.dmd.set_data(data)
        else:
            self.machine.log.warning("Received a DMD frame of length %s instead"
                                     "of 4096. Discarding...", len(data))

    def tick(self):
        """Updates the physical DMD with the latest frame data. Meant to be
        called once per machine tick.

        """
        self.proc.dmd_draw(self.dmd)


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
