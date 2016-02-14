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
import re
import time
import math
from copy import deepcopy
from mpf.core.utility_functions import Util
from mpf.platform.interfaces.rgb_led_platform_interface import RGBLEDPlatformInterface
from mpf.platform.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface
from mpf.platform.interfaces.driver_platform_interface import DriverPlatformInterface
from mpf.core.rgb_color import RGBColor

try:
    import pinproc
    pinproc_imported = True
except ImportError:
    pinproc_imported = False

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
        self.pdbconfig = PDBConfig(self.proc, self.machine.config)

        self.polarity = True

        self.acceleration = [0] * 3
        self.accelerometer_device = False

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
            raw_value = raw_value - (1 << 14)

        g_value = float(raw_value) / (1 << 12)

        return g_value

    def configure_accelerometer(self, device, number, useHighPass):
        if number != "1":
            raise AssertionError("P3-ROC only has one accelerometer. Use number 1")

        self.accelerometer_device = device
        self._configure_accelerometer(periodicRead=True, readWithHighPass=useHighPass, tiltInterrupt=False)

    def _configure_accelerometer(self, periodicRead=False, tiltInterrupt=True, tiltThreshold=0.2,
                                 readWithHighPass=False):

        enable = 0
        if periodicRead:
            # enable polling every 128ms
            enable |= 0x0F

        if tiltInterrupt:
            # configure interrupt at P3-ROC
            enable |= 0x1E00

        # configure some P3-Roc registers
        self.proc.write_data(6, 0x000, enable)

        # CTRL_REG1 - set to standby
        self.proc.write_data(6, 0x12A, 0)

        if periodicRead:
            # XYZ_DATA_CFG - enable/disable high pass filter, scale 0 to 2g
            self.proc.write_data(6, 0x10E, 0x00 | (bool(readWithHighPass) * 0x10))

        if tiltInterrupt:
            # HP_FILTER_CUTOFF - cutoff at 2Hz
            self.proc.write_data(6, 0x10F, 0x03)

            # FF_TRANSIENT_COUNT - set debounce counter
            # number of timesteps where the threshold has to be reached
            # time step is 1.25ms
            self.proc.write_data(6, 0x120, 1)

            # transient_threshold * 0.063g
            # Theoretically up to 8g
            # Since we use low noise mode limited to 4g (value of 63)
            transient_threshold_raw = int(math.ceil(float(tiltThreshold) / 0.063))
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


class PDBLED(RGBLEDPlatformInterface):
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
            color: an RGBColor object
        """

        # self.log.debug("Setting Color. Board: %s, Address: %s, Color: %s",
        #               self.board, self.address, color)

        self.proc.led_color(self.board, self.address[0], color.red)
        self.proc.led_color(self.board, self.address[1], color.green)
        self.proc.led_color(self.board, self.address[2], color.blue)

    def disable(self):
        """Disables (turns off) this LED instantly. For multi-color LEDs it
        turns all elements off.
        """
        self.color(RGBColor())

    def enable(self):
        """Enables (turns on) this LED instantly. For multi-color LEDs it turns
        all elements on.
        """
        self.color(RGBColor('White'))


class PDBSwitch(object):
    """Base class for switches connected to a P3-ROC."""

    def __init__(self, pdb, number_str):
        del pdb  # unused. why?

        upper_str = number_str.upper()
        if upper_str.startswith('SD'):
            self.sw_type = 'dedicated'
            self.sw_number = int(upper_str[2:])
        elif '/' in upper_str:
            self.sw_type = 'matrix'
            self.sw_number = self.parse_matrix_num(upper_str)
        else:
            self.sw_type = 'proc'
            try:
                (boardnum, banknum, inputnum) = decode_pdb_address(number_str, [])
                self.sw_number = boardnum * 16 + banknum * 8 + inputnum
            except ValueError:
                try:
                    self.sw_number = int(number_str)
                except:
                    raise ValueError('Switch %s is invalid. Use either PDB '
                                     'format or an int', str(number_str))

    def proc_num(self):
        return self.sw_number

    def parse_matrix_num(self, num_str):
        cr_list = num_str.split('/')
        return 32 + int(cr_list[0]) * 16 + int(cr_list[1])


class PDBCoil(object):
    """Base class for coils connected to a P3-ROC that are controlled via P3-ROC
    driver boards (i.e. the PD-16 board).

    """

    def __init__(self, pdb, number_str):
        self.pdb = pdb
        upper_str = number_str.upper()
        if self.is_direct_coil(upper_str):
            self.coil_type = 'dedicated'
            self.banknum = (int(number_str[1:]) - 1) / 8
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
            (self.source_boardnum, self.source_banknum, self.source_outputnum) \
                = decode_pdb_address(source_addr, self.pdb.aliases)
            (self.sink_boardnum, self.sink_banknum, self.sink_outputnum) \
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


class PROCDriver(DriverPlatformInterface):
    """ Base class for drivers connected to a P3-ROC. This class is used for all
    drivers, regardless of whether they're connected to a P-ROC driver board
    (such as the PD-16 or PD-8x8) or an OEM driver board.

    """

    def __init__(self, number, proc_driver, config, machine):
        self.log = logging.getLogger('PROCDriver')
        self.number = number
        self.proc = proc_driver

        self.driver_settings = self.create_driver_settings(machine, **config)

        self.driver_settings['number'] = number

        self.driver_settings.update(self.merge_driver_settings(**config))

        self.log.debug("Driver Settings for %s: %s", self.number,
                       self.driver_settings)

    def create_driver_settings(self, machine, pulse_ms=None, **kwargs):
        return_dict = dict()
        if pulse_ms is None:
            pulse_ms = machine.config['mpf']['default_pulse_ms']

        try:
            return_dict['allow_enable'] = kwargs['allow_enable']
        except KeyError:
            return_dict['allow_enable'] = False

        return_dict['pulse_ms'] = int(pulse_ms)
        return_dict['recycle_ms'] = 0
        return_dict['pwm_on_ms'] = 0
        return_dict['pwm_off_ms'] = 0

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
                              **kwargs
                              ):
        del kwargs

        if pulse_power:
            raise NotImplementedError('"pulse_power" has not been '
                                      'implemented yet')

        if pulse_power32:
            raise NotImplementedError('"pulse_power32" has not been '
                                      'implemented yet')

        if hold_power32:
            raise NotImplementedError('"hold_power32" has not been '
                                      'implemented yet')

        if pulse_pwm_mask:
            raise NotImplementedError('"pulse_pwm_mask" has not been '
                                      'implemented yet')

        if hold_pwm_mask:
            raise NotImplementedError('"hold_pwm_mask" has not been '
                                      'implemented yet')

        return_dict = dict()

        # figure out what kind of enable we need:

        if hold_power:
            return_dict['pwm_on_ms'], return_dict['pwm_off_ms'] = (
                Util.pwm8_to_on_off(hold_power))

        elif pwm_off_ms and pwm_on_ms:
            return_dict['pwm_on_ms'] = int(pwm_on_ms)
            return_dict['pwm_off_ms'] = int(pwm_off_ms)

        if pulse_ms is not None:
            return_dict['pulse_ms'] = int(pulse_ms)
        elif 'pwm_on_ms' in return_dict:
            return_dict['pulse_ms'] = 0

        if recycle_ms and int(recycle_ms) == 125:
            return_dict['recycle_ms'] = 125
        elif recycle_ms and recycle_ms is not None:
            raise ValueError('P-ROC requires recycle_ms of 0 or 125')

        found_pwm_on = False
        found_pwm_off = False
        if 'pwm_on_ms' in return_dict and return_dict['pwm_on_ms']:
            found_pwm_on = True
        if 'pwm_off_ms' in return_dict and return_dict['pwm_off_ms']:
            found_pwm_off = True

        if (found_pwm_off and not found_pwm_on) or (
                    found_pwm_on and not found_pwm_off):
            raise ValueError("Error: Using pwm requires both pwm_on and "
                             "pwm_off values.")

        return return_dict

    def disable(self):
        """Disables (turns off) this driver."""
        self.log.debug('Disabling Driver')
        self.proc.driver_disable(self.number)

    def enable(self):
        """Enables (turns on) this driver."""

        if (self.driver_settings['pwm_on_ms'] and
                self.driver_settings['pwm_off_ms']):

            self.log.debug('Enabling. Initial pulse_ms:%s, pwm_on_ms: %s'
                           'pwm_off_ms: %s',
                           self.driver_settings['pwm_on_ms'],
                           self.driver_settings['pwm_off_ms'],
                           self.driver_settings['pulse_ms'])

            self.proc.driver_patter(self.number,
                                    self.driver_settings['pwm_on_ms'],
                                    self.driver_settings['pwm_off_ms'],
                                    self.driver_settings['pulse_ms'], True)
        else:
            self.log.debug('Enabling at 100%')

            if not ('allow_enable' in self.driver_settings and
                        self.driver_settings['allow_enable']):
                raise AssertionError("Received a command to enable this coil "
                                     "without pwm, but 'allow_enable' has not been"
                                     "set to True in this coil's configuration.")

            self.proc.driver_schedule(number=self.number, schedule=0xffffffff,
                                      cycle_seconds=0, now=True)

    def pulse(self, milliseconds=None):
        """Enables this driver for `milliseconds`.

        ``ValueError`` will be raised if `milliseconds` is outside of the range
        0-255.
        """

        if not milliseconds:
            milliseconds = self.driver_settings['pulse_ms']

        self.log.debug('Pulsing for %sms', milliseconds)
        self.proc.driver_pulse(self.number, milliseconds)

        return milliseconds

    def get_pulse_ms(self):
        return self.driver_settings['pulse_ms']

    def state(self):
        """Returns a dictionary representing this driver's current
        configuration state.
        """
        return self.proc.driver_get_state(self.number)

    def tick(self):
        pass


class PROCMatrixLight(MatrixLightPlatformInterface):
    def __init__(self, number, proc_driver):
        self.log = logging.getLogger('PROCMatrixLight')
        self.number = number
        self.proc = proc_driver

    def off(self):
        """Disables (turns off) this driver."""
        self.proc.driver_disable(self.number)
        self.last_time_changed = self.machine.clock.get_time()

    def on(self, brightness=255):
        """Enables (turns on) this driver."""
        if brightness >= 255:
            self.proc.driver_schedule(number=self.number, schedule=0xffffffff,
                                      cycle_seconds=0, now=True)
        elif brightness == 0:
            self.off()
        else:
            pass
            # patter rates of 10/1 through 2/9

        self.last_time_changed = self.machine.clock.get_time()

        """
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
        """     # pylint: disable=W0105


class PDBConfig(object):
    """ This class is only used when the P3-ROC is configured to use P3-ROC
    driver boards such as the PD-16 or PD-8x8. i.e. not when it's operating in
    WPC or Stern mode.

    """
    indexes = []
    proc = None
    aliases = None  # set in __init__

    def __init__(self, proc, config):

        self.log = logging.getLogger('PDBConfig')
        self.log.debug("Processing P3-ROC Driver Board configuration")

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

        # Make a list of unique lamp source banks.  The P3-ROC only supports 2.
        # TODO: What should be done if 2 is exceeded?
        if 'matrix_lights' in config:
            for name in config['matrix_lights']:
                item_dict = config['matrix_lights'][name]
                lamp = PDBLight(self, str(item_dict['number']))

                # Catalog PDB banks
                # Dedicated lamps don't use PDB banks. They use P3-ROC direct
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
        # list. The index of the bank is used to calculate the P3-ROC driver
        # number for each driver.
        num_proc_banks = pinproc.DriverCount // 8
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

        # next group is 4
        group_ctr = 4

        # Process lamps first. The P3-ROC can only control so many drivers
        # directly. Since software won't have the speed to control lamp
        # matrixes, map the lamps first. If there aren't enough P3-ROC driver
        # groups for coils, the overflow coils can be controlled by software
        # via VirtualDrivers (which should get set up automatically by this
        # code.)

        for i, lamp_dict in enumerate(lamp_list):
            # If the bank is 16 or higher, the P3-ROC can't control it
            # directly. Software can't really control lamp matrixes either
            # (need microsecond resolution).  Instead of doing crazy logic here
            # for a case that probably won't happen, just ignore these banks.
            if group_ctr >= num_proc_banks or lamp_dict['sink_bank'] >= 16:
                raise AssertionError("Lamp matrix banks can't be mapped to index "
                                     "%d because that's outside of the banks the "
                                     "P3-ROC can control.", lamp_dict['sink_bank'])
            else:
                self.log.debug("Driver group %02d (lamp sink): slow_time=%d "
                               "enable_index=%d row_activate_index=%d "
                               "row_enable_index=%d matrix=%s", group_ctr,
                               self.lamp_matrix_strobe_time,
                               lamp_dict['sink_bank'],
                               lamp_dict['source_output'],
                               lamp_dict['source_index'], True)
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
            # If the bank is 16 or higher, the P3-ROC can't control it directly.
            # Software will have do the driver logic and write any changes to
            # the PDB bus. Therefore, map these banks to indexes above the
            # P3-ROC's driver count, which will force the drivers to be created
            # as VirtualDrivers. Appending the bank avoids conflicts when
            # group_ctr gets too high.

            if group_ctr >= num_proc_banks or coil_bank >= 32:
                self.log.warning("Driver group %d mapped to driver index"
                                 "outside of P3-ROC control.  These Drivers "
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

        # Now set up globals.  First disable them to allow the P3-ROC to set up
        # the polarities on the Drivers.  Then enable them.
        self.configure_globals(proc, lamp_source_bank_list, False)
        self.configure_globals(proc, lamp_source_bank_list, True)

    def initialize_drivers(self, proc):
        # Loop through all of the drivers, initializing them with the polarity.
        for i in range(0, 255):
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
                           lamp_source_bank_list[1])
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
        """Returns the P3-ROC number for the requested driver string.

        This method uses the driver string to look in the indexes list that
        was set up when the PDBs were configured.  The resulting P3-ROC index
        * 3 is the first driver number in the group, and the driver offset is
        to that.

        """
        if device_type == 'coil':
            coil = PDBCoil(self, number_str)
            bank = coil.bank()
            if bank == -1:
                return -1
            index = self.indexes.index(coil.bank())
            num = index * 8 + coil.output()
            return num

        if device_type == 'light':
            lamp = PDBLight(self, number_str)
            if lamp.lamp_type == 'unknown':
                return -1
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


def is_pdb_address(addr, aliases=None):
    """Returne True if the given address is a valid PDB address."""
    if aliases is None:
        aliases = []
    try:
        decode_pdb_address(addr=addr, aliases=aliases)
        return True
    except ValueError:
        return False


def decode_pdb_address(addr, aliases=None):
    """Decodes Ax-By-z or x/y/z into PDB address, bank number, and output
    number.

    Raises a ValueError exception if it is not a PDB address, otherwise returns
    a tuple of (addr, bank, number).

    """
    if aliases is None:
        aliases = []
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
        return board, bank, output

    elif '/' in addr:  # x/y/z form
        params = addr.rsplit('/')
        if len(params) != 3:
            raise ValueError('pdb address must have 3 components')
        board = int(params[0])
        bank = int(params[1])
        output = int(params[2])
        return board, bank, output

    else:
        raise ValueError('PDB address delimeter (- or /) not found.')
