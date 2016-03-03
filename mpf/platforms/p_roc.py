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

"""

import logging
import sys
from copy import deepcopy
from mpf.platforms.p_roc_common import PDBConfig, PDBLED, PROCDriver, PROCSwitch, PROCMatrixLight

try:
    import pinproc
    pinproc_imported = True
except ImportError:
    pinproc_imported = False
    pinproc = None

from mpf.core.platform import Platform
from mpf.core.utility_functions import Util

proc_output_module = 3
proc_pdb_bus_addr = 0xC00
# driverboards = ['wpc', 'wpc95', 'sternSAM', 'sternWhitestar']


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
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False
        self.features['variable_debounce_time'] = False
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
                print("Retrying...")

        self.log.info("Successfully connected to P-ROC")

        # Clear out the default program for the aux port since we might need it
        # for a 9th column. Details:
        # http://www.pinballcontrollers.com/forum/index.php?topic=1360
        commands = []
        commands += [pinproc.aux_command_disable()]

        for dummy_iterator in range(1, 255):
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
            self.pdbconfig = PDBConfig(self.proc, self.machine.config, pinproc.DriverCount)

        else:
            self.log.debug("Configuring P-ROC for OEM driver boards")

        self.polarity = self.machine_type == pinproc.MachineTypeSternWhitestar\
            or self.machine_type == pinproc.MachineTypeSternSAM\
            or self.machine_type == pinproc.MachineTypePDB

    def __repr__(self):
        return '<Platform.P-ROC>'

    def stop(self):
        self.proc.reset(1)

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
            proc_driver_object = PROCDriver(proc_num, self.proc, config, self.machine)
        elif device_type == 'light':
            proc_driver_object = PROCMatrixLight(proc_num, self.proc)
        else:
            raise AssertionError("Invalid device type {}".format(device_type))

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

        return switch, proc_num

    def get_hw_switch_states(self):
        # Read in and set the initial switch state
        # The P-ROC uses the following values for hw switch states:
        # 1 - closed (debounced)
        # 2 - open (debounced)
        # 3 - closed (not debounced)
        # 4 - open (not debounced)

        states = self.proc.switch_get_states()

        for switch, state in enumerate(states):
            if state == 3 or state == 1:
                states[switch] = 1
            else:
                states[switch] = 0

        return states

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

    def tick(self, dt):
        """Checks the P-ROC for any events (switch state changes or notification
        that a DMD frame was updated).

        Also tickles the watchdog and flushes any queued commands to the P-ROC.

        """
        del dt
        # Get P-ROC events (switches & DMD frames displayed)
        for event in self.proc.get_events():
            event_type = event['type']
            event_value = event['value']
            if event_type == 99:  # CTRL-C to quit todo does this go here?
                self.machine.stop()
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

    def write_hw_rule(self, switch_obj, sw_activity, driver_obj, driver_action,
                      disable_on_release, drive_now,
                      **driver_settings_overrides):

        driver_settings = deepcopy(driver_obj.hw_driver.driver_settings)

        driver_settings.update(driver_obj.hw_driver.merge_driver_settings(
            **driver_settings_overrides))

        self.log.debug("Setting HW Rule. Switch: %s, Switch_action: %s, Driver:"
                       " %s, Driver action: %s. Driver settings: %s",
                       switch_obj.name, sw_activity, driver_obj.name,
                       driver_action, driver_settings)

        if 'debounced' in driver_settings_overrides:
            if driver_settings_overrides['debounced']:
                debounced = True
            else:
                debounced = False
        elif switch_obj.config['debounce']:
            debounced = True
        else:
            debounced = False

        # Note the P-ROC uses a 125ms non-configurable recycle time. So any
        # non-zero value passed here will enable the 125ms recycle.
        # PinPROC calls this "reload active" (it's an "active reload timer")

        reload_active = False
        if driver_settings['recycle_ms']:
            reload_active = True

        # We only want to notify_host for debounced switch events. We use non-
        # debounced for hw_rules since they're faster, but we don't want to
        # notify the host on them since the host would then get two events
        # one for the nondebounced followed by one for the debounced.

        notify_host = False
        if debounced:
            notify_host = True

        rule = {'notifyHost': notify_host, 'reloadActive': reload_active}

        # Now let's figure out what type of P-ROC action we need to take.

        invert_switch_for_disable = False

        proc_actions = set()

        if driver_action == 'pulse':
            if (driver_settings['pwm_on_ms'] and
                    driver_settings['pwm_off_ms']):
                proc_actions.add('pulsed_patter')
                pulse_ms = driver_settings['pulse_ms']
                pwm_on = driver_settings['pwm_on_ms']
                pwm_off = driver_settings['pwm_off_ms']
            else:
                proc_actions.add('pulse')
                pulse_ms = driver_settings['pulse_ms']

            if disable_on_release:
                proc_actions.add('disable')
                invert_switch_for_disable = True

        elif driver_action == 'hold':
            if (driver_settings['pwm_on_ms'] and
                    driver_settings['pwm_off_ms']):
                proc_actions.add('patter')
                pulse_ms = driver_settings['pulse_ms']
                pwm_on = driver_settings['pwm_on_ms']
                pwm_off = driver_settings['pwm_off_ms']
            else:
                proc_actions.add('enable')

            if disable_on_release:
                proc_actions.add('disable')
                invert_switch_for_disable = True

        elif driver_action == 'disable':
            proc_actions.add('disable')

        for proc_action in proc_actions:
            this_driver = list()
            this_sw_activity = sw_activity

            # The P-ROC ties hardware rules to switches, with a list of linked
            # drivers that should change state based on a switch activity.
            # Since MPF applies the rules one-at-a-time, we have to read the
            # existing linked drivers from the hardware for that switch, add
            # our new driver to the list, then re-update the rule on the hw.

            if proc_action == 'pulse':
                this_driver = [pinproc.driver_state_pulse(
                    driver_obj.hw_driver.state(), pulse_ms)]

            elif proc_action == 'patter':
                this_driver = [pinproc.driver_state_patter(
                    driver_obj.hw_driver.state(), pwm_on, pwm_off, pulse_ms,
                    True)]
                # todo above param True should not be there. Change to now?

            elif proc_action == 'enable':
                this_driver = [pinproc.driver_state_pulse(
                    driver_obj.hw_driver.state(), 0)]

            elif proc_action == 'disable':
                if invert_switch_for_disable:
                    this_sw_activity ^= 1

                this_driver = [pinproc.driver_state_disable(
                    driver_obj.hw_driver.state())]

            elif proc_action == 'pulsed_patter':
                this_driver = [pinproc.driver_state_pulsed_patter(
                    driver_obj.hw_driver.state(), pwm_on, pwm_off,
                    pulse_ms)]

            if this_sw_activity == 0 and debounced:
                event_type = "open_debounced"
            elif this_sw_activity == 0 and not debounced:
                event_type = "open_nondebounced"
            elif this_sw_activity == 1 and debounced:
                event_type = "closed_debounced"
            else:  # if sw_activity == 1 and not debounced:
                event_type = "closed_nondebounced"

            # merge in any previously-configured driver rules for this switch
            final_driver = list(this_driver)  # need to make an actual copy
            sw_rule_string = str(switch_obj.name)+str(event_type)
            if sw_rule_string in self.hw_switch_rules:
                for driver in self.hw_switch_rules[sw_rule_string]:
                    final_driver.append(driver)
                self.hw_switch_rules[sw_rule_string].extend(this_driver)
            else:
                self.hw_switch_rules[sw_rule_string] = this_driver

            self.log.debug("Writing HW rule for switch: %s, driver: %s, event_type: %s, "
                           "rule: %s, final_driver: %s, drive now: %s",
                           switch_obj.name, driver_obj.name, event_type,
                           rule, final_driver, drive_now)
            self.proc.switch_update_rule(switch_obj.number, event_type, rule,
                                         final_driver, drive_now)

    def clear_hw_rule(self, sw_name):
        """Clears a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        Args:
            sw_name : Int of the number of the switch whose rule you want to
                clear.

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

        for entry in list(self.hw_switch_rules.keys()):  # slice for copy
            if entry.startswith(self.machine.switches.number(sw_num).name):

                # disable any drivers from this rule which are active now
                # todo make this an option?
                for driver_dict in self.hw_switch_rules[entry]:
                    self.proc.driver_disable(driver_dict['driverNum'])

                # Remove this rule from our list
                del self.hw_switch_rules[entry]

        # todo need to read in the notifyHost settings and reapply those
        # appropriately.


class PROCDMD(object):
    """Parent class for a physical DMD attached to a P-ROC.

    Args:
        proc: Reference to the MachineController's proc attribute.
        machine: Reference to the MachineController

    Attributes:
        dmd: Reference to the P-ROC's DMD buffer.

    """

    def __init__(self, proc, machine):
        self.proc = proc
        self.machine = machine
        self.dmd = pinproc.DMDBuffer(128, 32)
        # size is hardcoded here since 128x32 is all the P-ROC hw supports

        # dmd_timing defaults should be 250, 400, 180, 800

        if 'P_ROC' in self.machine.config and 'dmd_timing_cycles' in self.machine.config['P_ROC']:

            dmd_timing = Util.string_to_list(
                self.machine.config['P_ROC']['dmd_timing_cycles'])

            dmd_timing = [int(i) for i in dmd_timing]

            self.proc.dmd_update_config(high_cycles=dmd_timing)

        # Update DMD 30 times per second
        # TODO: Add DMD update interval to config
        self.machine.clock.schedule_interval(self.tick, 1/30.0)

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

    def tick(self, dt):
        """Updates the physical DMD with the latest frame data. Meant to be
        called once per machine tick.

        """
        del dt
        self.proc.dmd_draw(self.dmd)
