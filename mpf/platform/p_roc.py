"""Contains the drivers and interface code for pinball machines which
use the Multimorphic R-ROC or P3-ROC hardware controllers.

This code can be used with P-ROC driver boards, or with Stern SAM, Stern
Whitestar, Williams WPC, or Williams WPC95  driver boards.

Most of this code is from the P-ROC drivers section of the pyprocgame project,
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

# Documentation and more info at http://missionpinball.com/framework

import logging
import pinproc  # If this fails it's because you don't have pypinproc.
import re
import time
import sys
from mpf.system.hardware import (
    Platform, HardwareObject, HardwareDriver, HardwareSwitch,
    HardwareDirectLED)
from mpf.system.timing import Timing

proc_output_module = 3
proc_pdb_bus_addr = 0xC00


class HardwarePlatform(object):
    """Base class of the hardware controller.

    """

    def __init__(self, machine):
        self.log = logging.getLogger('P-ROC Platform')
        self.log.debug("Configuring machine for P-ROC hardware.")
        self.machine = machine
        self.machine.hw_polling = True

        self.machine_type = pinproc.normalize_machine_type(
            self.machine.config['Hardware']['DriverBoards'])
        self.proc = self.create_pinproc()
        self.proc.reset(1)
        self.HZ = None
        self.secs_per_tick = None
        self.next_tick_time = None
        self.platform_features = {}
        self.hw_switch_rules = {}

        self.parent = Platform(self, machine)

        # Setup the dictionary of platform features. This is how we let the
        # framework know about certain capabilities of the hardware platform
        self.platform_features['max_pulse'] = 255
        self.platform_features['hw_rule_coil_delay'] = False
        self.platform_features['variable_recycle_time'] = False

    def create_pinproc(self):
        """Instantiates and returns the class to use as the P-ROC device.

        Checks the machine controller's attribute *physical_hw* to see whether
        it should use a physical PinPROC or the FakePinPROC class to setup the
        P-ROC.

        """
        if self.machine.physical_hw:  # move to platform? todo
            proc_class_name = "pinproc.PinPROC"

        else:
            proc_class_name = "procgame.fakepinproc.FakePinPROC"

        proc_class = self.get_class(proc_class_name)
        return proc_class(self.machine_type)

    def get_class(self, kls, path_adj='/.'):
        """Returns a class for the given fully qualified class name, *kls*.

        Source: http://stackoverflow.com/questions/452969/
        does-python-have-an-equivalent-to-java-class-forname
        """
        sys.path.append(sys.path[0]+path_adj)
        parts = kls.split('.')
        module = ".".join(parts[:-1])
        m = __import__(module)
        for comp in parts[1:]:
            m = getattr(m, comp)
        return m

    def process_hw_config(self):
        """Processes the P-ROC hardware configuration items in the config
        files.

        This includes sections for:
            * Coils
            * Lamps
            * Switches
            * LEDs

        """

        pairs = [('Coils', self.machine.coils, PROCDriver),
                 ('Lamps', self.machine.lamps, PROCDriver),
                 ('Switches', self.machine.switches, PROCSwitch),
                 ('LEDs', self.machine.leds, PROCLED)]

        new_virtual_drivers = []
        polarity = self.machine_type == pinproc.MachineTypeSternWhitestar or \
            self.machine_type == pinproc.MachineTypeSternSAM or \
            self.machine_type == pinproc.MachineTypePDB


        # Because PDBs can be configured in many different ways, we need to
        # traverse the YAML settings to see how many PDBs are being used.
        # Then we can configure the P-ROC appropriately to use those PDBs.
        # Only then can we relate the YAML coil/lamp #'s to P-ROC numbers for
        # the collections.

        if self.machine_type == pinproc.MachineTypePDB:
            self.log.debug("Configuring P-ROC for P-ROC driver boards.")
            pdb_config = PDBConfig(self.proc, self.machine.config)

        else:
            self.log.debug("Configuring P-ROC for OEM driver boards.")

        for section, collection, klass in pairs:
            if section in self.machine.config:
                sect_dict = self.machine.config[section]
                for name in sect_dict:

                    item_dict = sect_dict[name]


                    # Find the P-ROC number for each item in the YAML sections.
                    # For PDBs the number is based on the PDB configuration
                    # determined above.  For other machine types, pinproc's
                    # decode() method can provide the number.

                    if self.machine_type == pinproc.MachineTypePDB:
                        number = pdb_config.get_proc_number(section,
                            str(item_dict['number']))
                        if number == -1:
                            self.log.error("%s Item: %s cannot be "
                                              "controlled by the P-ROC.  "
                                              "Ignoring...", section, name)
                            continue
                    else:
                        number = pinproc.decode(self.machine_type,
                                                str(item_dict['number']))

                    item = None
                    if ('bus' in item_dict and item_dict['bus'] == 'AuxPort') \
                            or number >= pinproc.DriverCount:
                        item = VirtualDriver(self, name, number, polarity)
                        new_virtual_drivers += [number]
                    else:
                        yaml_number = str(item_dict['number'])
                        if klass == PROCLED:
                            number = yaml_number

                        item = klass(self, name, number)
                        item.yaml_number = yaml_number

                        # We write the label, type, & tags to the parent item
                        if 'label' in item_dict:
                            item.parent.label = item_dict['label']

                        if 'type' in item_dict:
                            item.parent.type = item_dict['type']
                        #else:
                        #    item.parent.type = 'NO'

                        if 'tags' in item_dict:
                            tags = item_dict['tags']
                            if type(tags) == str:
                                item.parent.tags = tags.split(',')
                            elif type(tags) == list:
                                item.parent.tags = tags
                            else:
                                self.log.warning('Configuration item named '
                                    '"%s" has unexpected tags type %s. Should '
                                    'be list or comma-delimited string.'
                                    % (name, type(tags)))

                        if klass == PROCSwitch:
                            if (('debounced' in item_dict and
                                 item_dict['debounced'] is False) or number >=
                                 pinproc.SwitchNeverDebounceFirst):
                                item.debounced = False
                        if klass == PROCDriver:
                            if ('pulseTime' in item_dict):
                                item.pulse_time = \
                                    item_dict['pulseTime']
                            if ('polarity' in item_dict):
                                item.reconfigure(item_dict['polarity'])
                        if klass == PROCLED:
                            if ('polarity' in item_dict):
                                item.invert = not item_dict['polarity']

                    collection[name] = item.parent  # was 'item'
                    #item.parent.tags = collection[name].tags
                    self.log.debug("Creating P-ROC hardware device: %s: "
                                     "%s:%s", section, name, number)

        # In the P-ROC, VirtualDrivers will conflict with regular drivers on
        # the same group. So if any VirtualDrivers were added, the regular
        # drivers in that group must be changed to VirtualDrivers as well.

        for virtual_driver in new_virtual_drivers:
            base_group_number = virtual_driver/8
            for collection in [self.machine.coils, self.machine.lamps]:
                items_to_remove = []
                for item in collection:
                    if item.number/8 == base_group_number:
                        items_to_remove += [{name: item.name,
                                             number: item.number}]
                for item in items_to_remove:
                    self.log.debug("Removing %s from %s", item[name],
                                     str(collection))
                    collection.remove(item[name], item[number])
                    # todo change to like above
                    self.log.debug("Adding %s to VirtualDrivers", item[name])
                    collection.add(item[name], VirtualDriver(self, item[name],
                                                             item[number],
                                                             polarity))

        # We want to receive events for all of the defined switches:
        self.log.debug("Programming switch rules...")
        for sw_name, sw_object in self.machine.switches.iteritems():
            if sw_object.debounced:
                self.proc.switch_update_rule(sw_object.number,
                                             'closed_debounced',
                                             {'notifyHost': True,
                                              'reloadActive': False}, [],
                                             False)
                self.proc.switch_update_rule(sw_object.number,
                                             'open_debounced',
                                             {'notifyHost': True,
                                              'reloadActive': False}, [],
                                             False)
            else:
                self.proc.switch_update_rule(sw_object.number,
                                             'closed_nondebounced',
                                             {'notifyHost': True,
                                             'reloadActive': False}, [], False)
                self.proc.switch_update_rule(sw_object.number,
                                             'open_nondebounced',
                                             {'notifyHost': True,
                                             'reloadActive': False}, [], False)

        # Configure the initial switch states:
        # todo remove since switch controller does this now?
        states = self.proc.switch_get_states()
        for sw_name, sw_object in self.machine.switches.iteritems():
            sw_object._set_state(states[sw_object.number] == 1)

    def hw_loop(self):
        """Loop code which checks the P-ROC for any events (switch state
        changes or notification that a DMD frame was updated).

        Also tickles the watchdog and flushes any queued commands to the P-ROC.

        """

        # Get P-ROC events (switches & DMD frames displayed)

        for event in self.proc.get_events():
            event_type = event['type']
            event_value = event['value']
            #event_time = event['time']  # not using this, maybe in the future?
            if event_type == 99:  # CTRL-C to quit todo does this go here?
                self.machine.end_run_loop()
            elif event_type == pinproc.EventTypeDMDFrameDisplayed:
                # DMD events
                pass
                #self.dmd_event()

            elif event_type == pinproc.EventTypeSwitchClosedDebounced:
                self.machine.switch_controller.process_switch(state=1,
                                                           num=event_value)
            elif event_type == pinproc.EventTypeSwitchOpenDebounced:
                self.machine.switch_controller.process_switch(state=0,
                                                           num=event_value)
            else:
                pass
                # todo we still have event types:
                # pinproc.EventTypeSwitchClosedNondebounced
                # pinproc.EventTypeSwitchOpenNondebounced
                # Do we do anything with them?

        self.tick_virtual_drivers()

        if self.proc:
            self.proc.watchdog_tickle()
            self.proc.flush()

        if Timing.HZ:
            if self.next_tick_time <= time.time():
                self.machine.timer_tick()
                self.next_tick_time += Timing.secs_per_tick
                # todo add detection to see if the system is running behind?
                # if you ask for 100HZ and the system can only do 50, that is
                # not good

    def tick_virtual_drivers(self):
        pass
        # todo fix this
        #for coil_name, coil_object in self.machine.coils.iteritems():
        #    coil_object.tick()
        #for lamp_name, lamp_object in self.machine.lamps.iteritems():
        #    lamp_object.tick()

    def timer_initialize(self):
        """ Run this before the machine loop starts. I want to do it here so we
        don't need to check for initialization on each machine loop. (Or is this
        premature optimization?)
        """
        self.next_tick_time = time.time()

    def set_hw_rule(self,
                    sw,
                    sw_activity,
                    coil_action_time,  # 0 = disable, -1 = hold forever
                    coil=None,
                    pulse_time=0,
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
            coil_action_time : int
                The total time (in ms) that this coil action should take place.
                A value of -1 means it's forever.
            coil : coil object
                Which coil is this rule controlling
            pulse_time : int
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
                       "Debounced:%s, Now:%s", sw.name, coil_action_time,
                       coil.name, pulse_time, pwm_on, pwm_off, delay,
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

        if coil_action_time == -1:  # hold coil forever
            if patter:
                proc_action = 'patter'
            else:
                proc_action = 'enable'
        elif coil_action_time > 0:  # timed action of some sort
            if coil_action_time <= pulse_time:
                proc_action = 'pulse'
                pulse_time = coil_action_time
            elif patter:
                if pulse_time:
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
                coil.platform_driver.state(), pulse_time)]

        elif proc_action == 'patter':
            this_driver = [pinproc.driver_state_patter(
                coil.platform_driver.state(), pwm_on, pwm_off, pulse_time)]

        elif proc_action == 'enable':
            this_driver = [pinproc.driver_state_pulse(
                coil.platform_driver.state(), 0)]

        elif proc_action == 'disable':
            this_driver = [pinproc.driver_state_disable(
                coil.platform_driver.state())]

        elif proc_action == 'pulsed_patter':
            this_driver = [pinproc.driver_state_pulsed_patter(
                coil.platform_driver.state(), pwm_on, pwm_off,
                coil_action_time)]

        # merge in any previously-configured driver rules for this switch

        final_driver = list(this_driver)  # need to make an actual copy
        sw_rule_string = str(sw.name)+str(event_type)
        if sw_rule_string in self.hw_switch_rules:
            for driver in self.hw_switch_rules[sw_rule_string]:
                final_driver.append(driver)
            self.hw_switch_rules[sw_rule_string].extend(this_driver)
        else:
            self.hw_switch_rules[sw_rule_string] = this_driver

        self.proc.switch_update_rule(sw.number, event_type, rule, final_driver,
                                     drive_now)

    def clear_hw_rule(self, sw_num):
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
        self.proc.switch_update_rule(sw_num, 'open_nondebounced',
                                     {'notifyHost': False,
                                      'reloadActive': False}, [], False)
        self.proc.switch_update_rule(sw_num, 'closed_nondebounced',
                                     {'notifyHost': False,
                                      'reloadActive': False}, [], False)
        self.proc.switch_update_rule(sw_num, 'open_debounced',
                                     {'notifyHost': True,
                                      'reloadActive': False}, [], False)
        self.proc.switch_update_rule(sw_num, 'closed_debounced',
                                     {'notifyHost': True,
                                      'reloadActive': False}, [], False)

        for entry in self.hw_switch_rules.keys():  # slice for copy
            if entry.startswith(self.machine.switches.get_from_number(sw_num).name):
                del self.hw_switch_rules[entry]

        # todo need to read in the notifyHost settings and reapply those
        # appropriately.


class PROCHardwareObject(HardwareObject):
    """Base class for P-ROC Hardware Objects."""
    yaml_number = None

    def __init__(self, machine, name, number):
        super(PROCHardwareObject, self).__init__(machine, name, number)


class PROCSwitch(object):
    """Represents a switch in a pinball machine connected to a P-ROC."""
    def __init__(self, machine, name, number):
        self.parent = HardwareSwitch(machine, name, number,
                                                  platform_driver=self)

    # todo add methods that query hardware-specific things of P-ROC switches,
    # if there are any??


class PROCLED(object):
    """Represents an LED connected to a PD-LED board.

    This code is not yet implemented.

    """

    def __init__(self, machine, name, number):
        """machine = Game object, name, number = LED name, number from
        machine.yaml
        """
        self.log = logging.getLogger('PROCLED')
        self.parent = HardwareDirectLED(machine, name, number,
                                                     platform_driver=self)
        self.name = name
        self.number = number
        self.machine = machine  # todo remove?

        cr_list = number.split('-')  # split the LED number into a list
        # pull the digit from first list entry to be the board address
        self.board_addr = int(cr_list[0][1:])
        self.addrs = []
        self.current_color = []
        # Loop through the remaining list entries to populate the color
        # addresses for that LED
        for color in cr_list[1:]:
            self.addrs.append(int(color[1:]))
            self.current_color.append(0)

        self.log.debug("Creating PD-LED item: %s, board_addr: %s, "
                         "color_addrs: %s", self.name, self.board_addr,
                         self.addrs)

    def color(self, color):

        super(color, self).color(color)

        # If the number of colors is the same or greater than the number of LED
        # outputs:
        if len(color) >= len(self.addrs):
            for i in range(len(self.addrs)):
                self.machine.proc.led_color(self.board_addr, self.addrs[i],
                                         color[i] *
                                         self.brightness_compensation[i])
                self.current_color[i] = color[i]

        else:  # The LED has more outputs than the color we're sending it.
            for i in range(len(color)):
                # Write the colors we can, ignore the rest.
                self.machine.proc.led_color(self.board_addr, self.addrs[i],
                                         color[i] *
                                         self.brightness_compensation[i])
                self.current_color[i] = color[i]

    def fade(self, color, fadetime):
        # todo have to decide whether we do fadetime in software or hardware
        # for the PD-LED

        super(fade, self).fade(color, fadetime)

        fadetime = int(fadetime/4)

        if len(color) >= len(self.addrs):
            # if the number of colors is the same or greater than the number
            # of LED outputs

            for i in range(len(self.addrs)):
                self.machine.proc.led_fade(self.board_addr,
                                        self.addrs[i],
                                        color[i] *
                                        self.brightness_compensation[i],
                                        fadetime)
                self.current_color[i] = color[i]

        else:  # The LED has more outputs than the color we're sending it
            for i in range(len(color)):
                # write the colors we can, ignore the rest
                self.machine.proc.led_fade(self.board_addr,
                                        self.addrs[i],
                                        color[i] *
                                        self.brightness_compensation[i],
                                        fadetime)
                self.current_color[i] = color[i]

    def disable(self):
        """Disables (turns off) this LED instantly. For multi-color LEDs it
        turns all elements off.
        """

        super(disable, self).disable()

        # loop through the count based on the number of LED outputs
        for i in range(len(self.addrs)):
            self.machine.proc.led_color(self.board_addr, self.addrs[i], 0)
            self.current_color[i] = 0

    def enable(self):
        """Enables (turns on) this LED instantly.
        For multi-color LEDs it turns all elements on.
        """

        super(enable, self).enable()

        # loop through the count based on the number of LED outputs
        for i in range(len(self.addrs)):
            self.machine.proc.led_color(self.board_addr, self.addrs[i],
                                     255 * self.brightness_compensation[i])
            self.current_color[i] = 255


class PDBSwitch(object):
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


class PDBLamp(object):
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


class PlatformDriver(object):
    pass


class PROCDriver(PlatformDriver):

    def __init__(self, machine, name, number):
        self.log = logging.getLogger('PROCDriver')
        self.machine = machine
        self.number = number
        self.parent = HardwareDriver(machine, name, number, self)

    def disable(self):
        """Disables (turns off) this driver."""
        self.machine.proc.driver_disable(self.number)

    def pulse(self, milliseconds=None):
        """Enables this driver for `milliseconds`.

        ``ValueError`` will be raised if `milliseconds` is outside of the range
        0-255.
        """
        if not milliseconds in range(256):
            raise ValueError('milliseconds must be in range 0-255.')
        self.machine.proc.driver_pulse(self.number, milliseconds)

    def future_pulse(self, milliseconds=None, timestamp=0):
        """Enables this driver for `milliseconds` at P-ROC timestamp:
        `timestamp`. If no parameter is provided for `milliseconds`,
        :attr:`pulse_time` is used. If no parameter is provided or
        `timestamp`, 0 is used. ``ValueError`` will be raised if `milliseconds`
        is outside of the range 0-255.
        """
        if milliseconds is None:
            milliseconds = self.pulse_time
        if not milliseconds in range(256):
            raise ValueError('milliseconds must be in range 0-255.')
        self.log.debug("Driver %s - future pulse %d", self.name,
                          milliseconds, timestamp)
        self.machine.proc.driver_future_pulse(self.number, milliseconds,
                                           timestamp)

    def patter(self, on_time=10, off_time=10, original_on_time=0, now=True):
        """Enables a pitter-patter sequence.

        It starts by activating the driver for `original_on_time` milliseconds.
        Then it repeatedly turns the driver on for `on_time` milliseconds and
        off for `off_time` milliseconds.
        """

        if not original_on_time in range(256):
            raise ValueError('original_on_time must be in range 0-255.')
        if not on_time in range(128):
            raise ValueError('on_time must be in range 0-127.')
        if not off_time in range(128):
            raise ValueError('off_time must be in range 0-127.')

        self.log.debug("Driver %s - patter on:%d, off:%d, orig_on:%d, "
                          "now:%s", self.name, on_time, off_time,
                          original_on_time, now)
        self.machine.proc.driver_patter(self.number, on_time, off_time,
                                     original_on_time, now)

    def pulsed_patter(self, on_time=10, off_time=10, run_time=0, now=True):
        """Enables a pitter-patter sequence that runs for `run_time`
        milliseconds.

        Until it ends, the sequence repeatedly turns the driver on for
        `on_time`  milliseconds and off for `off_time` milliseconds.
        """

        if not run_time in range(256):
            raise ValueError('run_time must be in range 0-255.')
        if not on_time in range(128):
            raise ValueError('on_time must be in range 0-127.')
        if not off_time in range(128):
            raise ValueError('off_time must be in range 0-127.')

        self.log.debug("Driver %s - pulsed patter on:%d, off:%d,"
                          "run_time:%d, now:%s", self.name, on_time, off_time,
                          run_time, now)
        self.machine.proc.driver_pulsed_patter(self.number, on_time, off_time,
                                            run_time, now)
        self.last_time_changed = time.time()

    def schedule(self, schedule, cycle_seconds=0, now=True):
        """Schedules this driver to be enabled according to the given
        `schedule` bitmask."""
        self.log.debug("Driver %s - schedule %08x", self.name, schedule)
        self.machine.proc.driver_schedule(number=self.number, schedule=schedule,
                                       cycle_seconds=cycle_seconds, now=now)
        self.last_time_changed = time.time()

    def state(self):
        """Returns a dictionary representing this driver's current
        configuration state.
        """
        return self.machine.proc.driver_get_state(self.number)

    def tick(self):
        pass

    def reconfigure(self, polarity):
        state = self.machine.proc.driver_get_state(self.number)
        state['polarity'] = polarity
        self.machine.proc.driver_update_state(state)


class PDBConfig(object):
    """ This class is only used when the P-ROC is configured to use P-ROC
    driver boards. i.e. not when it's operating in WPC or Stern mode.
    """
    indexes = []
    proc = None
    aliases = None  # set in __init__

    def __init__(self, proc, config):

        self.log = logging.getLogger('PDBConfig')
        self.log.debug("Processing P-ROC Driver Board configuration")

        self.proc = proc

        # Grab globals from the config data
        self.get_globals(config)

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
        for name in config['Coils']:
            item_dict = config['Coils'][name]
            coil = PDBCoil(self, str(item_dict['number']))
            if coil.bank() not in coil_bank_list:
                coil_bank_list.append(coil.bank())

        # Make a list of unique lamp source banks.  The P-ROC only supports 2.
        # TODO: What should be done if 2 is exceeded?
        if 'Lamps' in config:
            for name in config['Lamps']:
                item_dict = config['Lamps'][name]
                lamp = PDBLamp(self, str(item_dict['number']))

                # Catalog PDB banks
                # Dedicated lamps don't use PDB banks.  They use P-ROC direct
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
        while len(lamp_source_bank_list) < 2: lamp_source_bank_list.append(0)

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

    def get_globals(self, config):
        if 'PRDriverGlobals' in config and 'lamp_matrix_strobe_time' \
                in config['PRDriverGlobals']:
            self.lamp_matrix_strobe_time = int(config['PRDriverGlobals']
                                               ['lamp_matrix_strobe_time'])
        else:
            self.lamp_matrix_strobe_time = 200

        if 'PRDriverGlobals' in config and 'watchdog_time' \
                in config['PRDriverGlobals']:
            self.watchdog_time = int(config['PRDriverGlobals']
                                           ['watchdog_time'])
        else:
            self.watchdog_time = 1000

        if 'PRDriverGlobals' in config and 'use_watchdog' \
                in config['PRDriverGlobals']:
            self.use_watchdog = bool(config['PRDriverGlobals']['use_watchdog'])
        else:
            self.use_watchdog = True

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

    def get_proc_number(self, section, number_str):
        """Returns the P-ROC number for the requested driver string.

        This method uses the driver string to look in the indexes list that
        was set up when the PDBs were configured.  The resulting P-ROC index
        * 3 is the first driver number in the group, and the driver offset is
        to that.

        """
        if section == 'Coils':
            coil = PDBCoil(self, number_str)
            bank = coil.bank()
            if bank == -1:
                return (-1)
            index = self.indexes.index(coil.bank())
            num = index * 8 + coil.output()
            return num

        if section == 'Lamps':
            lamp = PDBLamp(self, number_str)
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

        if section == 'Switches':
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
        t = decode_pdb_address(addr=addr, aliases=aliases)
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


class VirtualDriver(HardwareDriver):
    """Represents a driver in a pinball machine, such as a lamp, coil/solenoid,
    or flasher that should be driver by Auxiliar Port logic rather directly by
    P-ROC hardware.  This means any automatic logic to determine when to turn
    on or off the driver is implemented in software in this class.

    Subclass of :class:`HardwareDriver`.

    """
    curr_state = False
    """The current state of the driver.  Active is True.  Inactive is False."""
    curr_value = False
    """The current value of the driver taking into account the desired state
    and polarity."""
    time_ms = 0
    """The time the driver's currently active function should end."""
    next_action_time_ms = 0
    """The next time the driver's state should change."""
    function = None
    """The currently assigned function (pulse, schedule, patter,
    pulsed_patter)."""
    function_active = False
    """Whether or not a function is currently active."""
    state_change_handler = None
    """Function to be called when the driver needs to change state."""

    def __init__(self, machine, name, number, polarity):
        super(VirtualDriver, self).__init__(machine, name, number)

        self.state = {'polarity':polarity,
                      'timeslots':0x0,
                      'patterEnable':False,
                      'driverNum':number,
                      'patterOnTime':0,
                      'patterOffTime':0,
                      'state':0,
                      'outputDriveTime':0,
                      'waitForFirstTimeSlot':0,
                      'futureEnable':False}

        self.curr_value = not (self.curr_state ^ self.state['polarity'])
        self.log = logging.getLogger('machine.vdriver')

    def update_state(self, state):
        """ Generic state change request that represents the P-ROC's
        PRDriverUpdateState function.

        """
        self.state = state.copy()
        if not state['state']:
            self.disable()
        elif state['timeslots'] == 0:
            self.pulse(state['outputDriveTime'])
        else:
            self.schedule(state['timeslots'], state['outputDriveTime'],
                          state['waitForFirstTimeSlot'])

    def disable(self):
        """Disables (turns off) this driver."""
        self.log.debug("VirtualDriver %s - disable", self.name)
        self.function_active = False
        self.change_state(False)

    def pulse(self, milliseconds=None):
        """Enables this driver for `milliseconds`.

        If no parameters are provided or `milliseconds` is `None`,
        :attr:`pulse_time` is used.

        """
        self.function = 'pulse'
        self.function_active = True
        if milliseconds is None:
            milliseconds = self.pulse_time
        self.change_state(True)
        if milliseconds == 0:
            self.time_ms = 0
        else:
            self.time_ms = time.time() + milliseconds / 1000.0
        self.log.debug("Time: %f: VirtualDriver %s - pulse %d. End time: %f",
                       time.time(), self.name, milliseconds, self.time_ms)

    def schedule(self, schedule, cycle_seconds=0, now=True):
        """Schedules this driver to be enabled according to the given
        `schedule` bitmask.

        """
        self.function = 'schedule'
        self.function_active = True
        self.state['timeslots'] = schedule
        if cycle_seconds == 0:
            self.time_ms = 0
        else:
            self.time_ms = time.time() + cycle_seconds
        self.log.debug("VirtualDriver %s - schedule %08x", self.name,
                          schedule)
        self.change_state(schedule & 0x1)
        self.next_action_time_ms = time.time() + 0.03125

    def enable(self):
        # todo need to change this so it sets a pulse that's 2.5x machine loop
        self.schedule(0xffffffff, 0, True)

    def change_state(self, new_state):
        self.curr_state = new_state
        self.curr_value = not (self.curr_state ^ self.state['polarity'])
        self.last_time_changed = time.time()
        if self.state_change_handler:
            self.state_change_handler()
        self.log.debug("VirtualDriver %s - state change: %d", self.name,
                          self.curr_state)

    def tick(self):
        if self.function_active:
            # Check for time expired.  time_ms == 0 is a special case that
            # never expires.
            if time.time() >= self.time_ms and self.time_ms > 0:
                self.disable()
            elif self.function == 'schedule':
                if time.time() >= self.next_action_time_ms:
                    self.inc_schedule()

    def inc_schedule(self):
        self.next_action_time_ms += .0325

        # See if the state needs to change.
        next_state = (self.state['timeslots'] >> 1) & 0x1
        if next_state != self.curr_state:
            self.change_state(next_state)

        # Rotate schedule down.
        self.state['timeslots'] = self.state['timeslots'] >> 1 | \
            ((self.state['timeslots'] << 31) & 0x80000000)

# The MIT License (MIT)

# Oringal code on which this module was based:
# Copyright (c) 2009-2011 Adam Preble and Gerry Stellenberg

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

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
