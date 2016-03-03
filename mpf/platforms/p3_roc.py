"""Contains the drivers and interface code for pinball machines which
use the Multimorphic P3-ROC hardware controllers.

Much of this code is from the P-ROC drivers section of the pyprocgame project,
written by Adam Preble and Gerry Stellenberg. It was originally released under
the MIT license and is released here under the MIT License.

More info on the P3-ROC hardware platform: http://pinballcontrollers.com/

Original code source on which this module was based:
https://github.com/preble/pyprocgame
"""

import logging
import time
import math
from copy import deepcopy
from mpf.platforms.p_roc_common import PDBConfig, PDBLED, PROCDriver, PROCSwitch, PROCMatrixLight

try:
    import pinproc
    pinproc_imported = True
except ImportError:
    pinproc_imported = False
    pinproc = None

from mpf.core.platform import Platform

proc_output_module = 3
proc_pdb_bus_addr = 0xC00


class HardwarePlatform(Platform):
    """Platform class for the P3-ROC hardware controller.

    Args:
        machine: The MachineController instance.

    Attributes:
        machine: The MachineController instance.
        proc: The P3-ROC pinproc.PinPROC device.
    """

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger('P3-ROC')
        self.log.debug("Configuring P3-ROC hardware.")

        if not pinproc_imported:
            raise AssertionError('Could not import "pinproc". Most likely you do not '
                                 'have libpinproc and/or pypinproc installed. You can'
                                 ' run MPF in software-only "virtual" mode by using '
                                 'the -x command like option for now instead.')

        # ----------------------------------------------------------------------
        # Platform-specific hardware features. WARNING: Do not edit these. They
        # are based on what the P3-ROC hardware can and cannot do.
        self.features['max_pulse'] = 255
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False
        self.features['variable_debounce_time'] = False
        self.features['hw_led_fade'] = True
        # todo need to add differences between patter and pulsed_patter

        # Make the platform features available to everyone
        self.machine.config['platform'] = self.features
        # ----------------------------------------------------------------------

        machine_type = pinproc.normalize_machine_type(
            self.machine.config['hardware']['driverboards'])

        if machine_type != pinproc.MachineTypePDB:
            raise AssertionError("P3-Roc can only handle PDB driver boards")

        # Connect to the P3-ROC. Keep trying if it doesn't work the first time.

        self.proc = None

        self.log.info("Connecting to P3-ROC")

        while not self.proc:
            try:
                self.proc = pinproc.PinPROC(machine_type)
                self.proc.reset(1)
            except IOError:
                self.log.warning("Failed to connect to P3-ROC. Will retry!")
                time.sleep(.5)

        self.log.info("Successfully connected to P3-ROC")

        # Because PDBs can be configured in many different ways, we need to
        # traverse the YAML settings to see how many PDBs are being used.
        # Then we can configure the P3-ROC appropriately to use those PDBs.
        # Only then can we relate the YAML coil/light #'s to P3-ROC numbers for
        # the collections.

        self.log.debug("Configuring P3-ROC for P-ROC driver boards.")
        self.pdbconfig = PDBConfig(self.proc, self.machine.config, pinproc.DriverCount)

        self.acceleration = [0] * 3
        self.accelerometer_device = None

    def __repr__(self):
        return '<Platform.P3-ROC>'

    def i2c_write8(self, address, register, value):
        self.proc.write_data(7, address << 9 | register, value)

    def i2c_read8(self, address, register):
        return self.proc.read_data(7, address << 9 | register) & 0xFF

    def i2c_read16(self, address, register):
        return self.proc.read_data(7, address << 9 | 1 << 8 | register)

    def stop(self):
        self.proc.reset(1)

    def scale_accelerometer_to_g(self, raw_value):
        # raw value is 0 to 16384 -> 14 bit
        # scale is -2g to 2g (2 complement)
        if raw_value & (1 << 13):
            raw_value -= 1 << 14

        g_value = float(raw_value) / (1 << 12)

        return g_value

    def configure_accelerometer(self, device, number, use_high_pass):
        if number != "1":
            raise AssertionError("P3-ROC only has one accelerometer. Use number 1")

        self.accelerometer_device = device
        self._configure_accelerometer(periodic_read=True, read_with_high_pass=use_high_pass, tilt_interrupt=False)

    def _configure_accelerometer(self, periodic_read=False, tilt_interrupt=True, tilt_threshold=0.2,
                                 read_with_high_pass=False):

        enable = 0
        if periodic_read:
            # enable polling every 128ms
            enable |= 0x0F

        if tilt_interrupt:
            # configure interrupt at P3-ROC
            enable |= 0x1E00

        # configure some P3-Roc registers
        self.proc.write_data(6, 0x000, enable)

        # CTRL_REG1 - set to standby
        self.proc.write_data(6, 0x12A, 0)

        if periodic_read:
            # XYZ_DATA_CFG - enable/disable high pass filter, scale 0 to 2g
            self.proc.write_data(6, 0x10E, 0x00 | (bool(read_with_high_pass) * 0x10))

        if tilt_interrupt:
            # HP_FILTER_CUTOFF - cutoff at 2Hz
            self.proc.write_data(6, 0x10F, 0x03)

            # FF_TRANSIENT_COUNT - set debounce counter
            # number of timesteps where the threshold has to be reached
            # time step is 1.25ms
            self.proc.write_data(6, 0x120, 1)

            # transient_threshold * 0.063g
            # Theoretically up to 8g
            # Since we use low noise mode limited to 4g (value of 63)
            transient_threshold_raw = int(math.ceil(float(tilt_threshold) / 0.063))
            if transient_threshold_raw > 63:
                self.log.warning("Tilt Threshold is too high. Limiting to 4g")
                transient_threshold_raw = 63

            # TRANSIENT_THS - Set threshold (0-127)
            self.proc.write_data(6, 0x11F, transient_threshold_raw & 0x7F)

            # Set FF_TRANSIENT_CONFIG (0x1D)
            # enable latching, all axis, no high pass filter bypass
            self.proc.write_data(6, 0x11D, 0x1E)

            # CTRL_REG4 - Enable transient interrupt
            self.proc.write_data(6, 0x12D, 0x20)

            # CTRL_REG5 - Enable transient interrupt (goes to INT1 by default)
            self.proc.write_data(6, 0x12E, 0x20)

        # CTRL_REG1 - set device to active and in low noise mode
        # 800HZ output data rate
        self.proc.write_data(6, 0x12A, 0x05)

        # CTRL_REG2 - set no sleep, high resolution mode
        self.proc.write_data(6, 0x12B, 0x02)

        # for auto-polling of accelerometer every 128 ms (8 times a sec). set 0x0F
        # disable polling + IRQ status addr FF_MT_SRC
        self.proc.write_data(6, 0x000, 0x1E0F)
        # flush data to proc
        self.proc.flush()

    def configure_driver(self, config, device_type='coil'):
        """ Creates a P3-ROC driver.

        Typically drivers are coils or flashers, but for the P3-ROC this is
        also used for matrix-based lights.

        Args:
            config: Dictionary of settings for the driver.
            device_type: String with value of either 'coil' or 'switch'.

        Returns:
            A reference to the PROCDriver object which is the actual object you
            can use to pulse(), patter(), enable(), etc.

        """
        # todo need to add virtual driver support for driver counts > 256

        # Find the P3-ROC number for each driver. For P3-ROC driver boards, the
        # P3-ROC number is specified via the Ax-By-C format.

        proc_num = self.pdbconfig.get_proc_number(device_type,
                                                  str(config['number']))
        if proc_num == -1:
            raise AssertionError("Coil %s cannot be controlled by the P3-ROC. ",
                                 str(config['number']))

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
        """Configures a P3-ROC switch.

        Args:
            config: Dictionary of settings for the switch. In the case
                of the P3-ROC, it uses the following:

        Returns:
            switch : A reference to the switch object that was just created.
            proc_num : Integer of the actual hardware switch number the P3-ROC
                uses to refer to this switch. Typically your machine
                configuration files would specify a switch number like `SD12` or
                `7/5`. This `proc_num` is an int between 0 and 255.
        """
        proc_num = self.pdbconfig.get_proc_number('switch',
                                                  str(config['number']))
        if proc_num == -1:
            raise AssertionError("Switch %s cannot be controlled by the "
                                 "P3-ROC.", str(config['number']))

        switch = PROCSwitch(proc_num)
        # The P3-ROC needs to be configured to notify the host computers of
        # switch events. (That notification can be for open or closed,
        # debounced or nondebounced.)
        self.log.debug("Configuring switch's host notification settings. P3-ROC"
                       "number: %s, debounce: %s", proc_num,
                       config['debounce'])
        if config['debounce'] is False:
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
            # Note: The P3-ROC will return a state of "3" for switches from non-
            # connected SW-16 boards, so that's why we only check for "1" below
            if state == 1:
                states[switch] = 1
            else:
                states[switch] = 0

        return states

    def configure_led(self, config):
        """ Configures a P3-ROC RGB LED controlled via a PD-LED."""

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
        """Configures a P3-ROC matrix light."""
        # On the P3-ROC, matrix lights are drivers
        return self.configure_driver(config, 'light')

    def configure_gi(self, config):
        """Configures a P3-ROC GI string light."""
        # On the P3-ROC, GI strings are drivers
        return self.configure_driver(config, 'light')

    def configure_dmd(self):
        """The P3-ROC does not support a physical DMD, so this method does
        nothing. It's included here in case it's called by mistake.

        """
        raise AssertionError("An attempt was made to configure a physical DMD, "
                             "but the P3-ROC does not support physical DMDs.")

    def tick(self, dt):
        """Checks the P3-ROC for any events (switch state changes).

        Also tickles the watchdog and flushes any queued commands to the P3-ROC.
        """
        del dt
        # Get P3-ROC events
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

            # The P3-ROC will always send all three values sequentially.
            # Therefore, we will trigger after the Z value
            elif event_type == pinproc.EventTypeAccelerometerX:
                self.acceleration[0] = event_value
            #                self.log.debug("Got Accelerometer value X. Value: %s", event_value)
            elif event_type == pinproc.EventTypeAccelerometerY:
                self.acceleration[1] = event_value
            #                self.log.debug("Got Accelerometer value Y. Value: %s", event_value)
            elif event_type == pinproc.EventTypeAccelerometerZ:
                self.acceleration[2] = event_value

                # trigger here
                if self.accelerometer_device:
                    self.accelerometer_device.update_acceleration(
                        self.scale_accelerometer_to_g(self.acceleration[0]),
                        self.scale_accelerometer_to_g(self.acceleration[1]),
                        self.scale_accelerometer_to_g(self.acceleration[2]))
                #                self.log.debug("Got Accelerometer value Z. Value: %s", event_value)

            # The P3-ROC sends interrupts when
            elif event_type == pinproc.EventTypeAccelerometerIRQ:
                self.log.debug("Got Accelerometer value IRQ. Value: %s", event_value)
                # trigger here
                if self.accelerometer_device:
                    self.accelerometer_device.received_hit()

            else:
                self.log.warning("Received unrecognized event from the P3-ROC. "
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
            sw_rule_string = str(switch_obj.name) + str(event_type)
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
            sw_name : Name of the switch whose rule you want to clear.
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
