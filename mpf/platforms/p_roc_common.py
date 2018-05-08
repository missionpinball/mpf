"""Common code for P-Roc and P3-Roc."""
import abc
import asyncio
import logging
import platform
import sys
import time
from typing import Any, List, Union, Callable, Tuple

from mpf.platforms.p_roc_devices import PROCSwitch, PROCMatrixLight
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.core.platform import SwitchPlatform, DriverPlatform, LightsPlatform, SwitchSettings, DriverSettings, \
    SwitchConfig

# pylint: disable-msg=ungrouped-imports
try:    # pragma: no cover
    import pinproc
    pinproc_imported = True
except ImportError:     # pragma: no cover
    try:
        if sys.platform == 'darwin':
            from mpf.platforms.pinproc.osx import pinproc
        elif sys.platform == 'win32':
            if platform.architecture()[0] == '32bit':
                if platform.python_version_tuple()[1] == '6':
                    from mpf.platforms.pinproc.x86.python36 import pinproc
                elif platform.python_version_tuple()[1] == '5':
                    from mpf.platforms.pinproc.x86.python35 import pinproc
                elif platform.python_version_tuple()[1] == '4':
                    from mpf.platforms.pinproc.x86.python34 import pinproc
                else:
                    raise ImportError
            elif platform.architecture()[0] == '64bit':
                if platform.python_version_tuple()[1] == '6':
                    from mpf.platforms.pinproc.x64.python36 import pinproc
                elif platform.python_version_tuple()[1] == '5':
                    from mpf.platforms.pinproc.x64.python35 import pinproc
                elif platform.python_version_tuple()[1] == '4':
                    from mpf.platforms.pinproc.x64.python34 import pinproc
                else:
                    raise ImportError

        pinproc_imported = True

    except ImportError:
        pinproc_imported = False
        pinproc = None


# pylint does not understand that this class is abstract
# pylint: disable-msg=abstract-method
class PROCBasePlatform(LightsPlatform, SwitchPlatform, DriverPlatform, metaclass=abc.ABCMeta):

    """Platform class for the P-Roc and P3-ROC hardware controller.

    Args:
        machine: The MachineController instance.

    Attributes:
        proc: The pinproc.PinPROC device.
        machine_type: Constant of the pinproc.MachineType
    """

    def __init__(self, machine):
        """Make sure pinproc was loaded."""
        super().__init__(machine)

        if not pinproc_imported:
            raise AssertionError('Could not import "pinproc". Most likely you do not '
                                 'have libpinproc and/or pypinproc installed. You can '
                                 'run MPF in software-only "virtual" mode by using '
                                 'the -x command like option for now instead.')

        self.pdbconfig = None
        self.pinproc = pinproc
        self.proc = None
        self.log = None
        self.hw_switch_rules = {}
        self.version = None
        self.revision = None
        self.hardware_version = None

        self.machine_type = pinproc.normalize_machine_type(
            self.machine.config['hardware']['driverboards'])

    @asyncio.coroutine
    def initialize(self):
        """Set machine vars."""
        self.machine.set_machine_var("p_roc_version", self.version)
        '''machine_var: p_roc_version

        desc: Holds the version number of the P-ROC or P3-ROC controller that's
        attached to MPF.
        '''

        self.machine.set_machine_var("p_roc_revision", self.revision)
        '''machine_var: p_roc_revision

        desc: Holds the revision number of the P-ROC or P3-ROC controller
        that's attached to MPF.
        '''

    def stop(self):
        """Stop proc."""
        self.proc.reset(1)

    def connect(self):
        """Connect to the P-ROC.

        Keep trying if it doesn't work the first time.
        """
        self.log.info("Connecting to P-ROC")

        while not self.proc:
            try:
                self.proc = pinproc.PinPROC(self.machine_type)
                self.proc.reset(1)
            except IOError:     # pragma: no cover
                print("Retrying...")
                time.sleep(1)

        version_revision = self.proc.read_data(0x00, 0x01)

        self.revision = version_revision & 0xFFFF
        self.version = (version_revision & 0xFFFF0000) >> 16
        dipswitches = self.proc.read_data(0x00, 0x03)
        self.hardware_version = (dipswitches & 0xF00) >> 8

        self.log.info("Successfully connected to P-ROC/P3-ROC. Firmware Version: %s. Firmware Revision: %s. "
                      "Hardware Board ID: %s",
                      self.version, self.revision, self.hardware_version)

    @classmethod
    def _get_event_type(cls, sw_activity, debounced):
        if sw_activity == 0 and debounced:
            return "open_debounced"
        elif sw_activity == 0 and not debounced:
            return "open_nondebounced"
        elif sw_activity == 1 and debounced:
            return "closed_debounced"
        else:  # if sw_activity == 1 and not debounced:
            return "closed_nondebounced"

    def _add_hw_rule(self, switch: SwitchSettings, coil: DriverSettings, rule, invert=False):
        rule_type = self._get_event_type(switch.invert == invert, switch.debounce)

        # overwrite rules for the same switch and coil combination
        for rule_num, rule_obj in enumerate(switch.hw_switch.hw_rules[rule_type]):
            if rule_obj[0] == switch.hw_switch.number and rule_obj[1] == coil.hw_driver.number:
                del switch.hw_switch.hw_rules[rule_type][rule_num]

        switch.hw_switch.hw_rules[rule_type].append(
            (switch.hw_switch.number, coil.hw_driver.number, rule)
        )

    def _add_pulse_rule_to_switch(self, switch, coil):
        # TODO: properly implement pulse_power. previously implemented pwm_on_ms/pwm_off_ms were incorrect here

        self._add_hw_rule(switch, coil,
                          self.pinproc.driver_state_pulse(coil.hw_driver.state(), coil.pulse_settings.duration))

    def _add_pulse_and_hold_rule_to_switch(self, switch: SwitchSettings, coil: DriverSettings):
        if coil.hold_settings.power < 1.0:
            pwm_on, pwm_off = coil.hw_driver.get_pwm_on_off_ms(coil.hold_settings)
            self._add_hw_rule(switch, coil,
                              self.pinproc.driver_state_patter(
                                  coil.hw_driver.state(), pwm_on, pwm_off, coil.pulse_settings.duration, True))
        else:
            self._add_hw_rule(switch, coil, self.pinproc.driver_state_pulse(coil.hw_driver.state(), 0))

    def _add_release_disable_rule_to_switch(self, switch: SwitchSettings, coil: DriverSettings):
        self._add_hw_rule(switch, coil,
                          self.pinproc.driver_state_disable(coil.hw_driver.state()), invert=True)

    def _add_disable_rule_to_switch(self, switch: SwitchSettings, coil: DriverSettings):
        self._add_hw_rule(switch, coil,
                          self.pinproc.driver_state_disable(coil.hw_driver.state()))

    def _write_rules_to_switch(self, switch, coil, drive_now):
        for event_type, driver_rules in switch.hw_switch.hw_rules.items():
            driver = []
            for x in driver_rules:
                driver.append(x[2])
            rule = {'notifyHost': bool(switch.hw_switch.notify_on_nondebounce) == event_type.endswith("nondebounced"),
                    'reloadActive': bool(coil.recycle)}
            if drive_now is None:
                self.proc.switch_update_rule(switch.hw_switch.number, event_type, rule, driver)
            else:
                self.proc.switch_update_rule(switch.hw_switch.number, event_type, rule, driver, drive_now)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit rule on driver."""
        self.debug_log("Setting HW Rule on pulse on hit. Switch: %s, Driver: %s",
                       enable_switch.hw_switch.number, coil.hw_driver.number)

        self._add_pulse_rule_to_switch(enable_switch, coil)

        self._write_rules_to_switch(enable_switch, coil, False)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and release rule to driver."""
        self.debug_log("Setting HW Rule on pulse on hit and relesae. Switch: %s, Driver: %s",
                       enable_switch.hw_switch.number, coil.hw_driver.number)

        self._add_pulse_rule_to_switch(enable_switch, coil)
        self._add_release_disable_rule_to_switch(enable_switch, coil)

        self._write_rules_to_switch(enable_switch, coil, False)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and relase rule on driver."""
        self.debug_log("Setting Pulse on hit and enable and release HW Rule. Switch: %s, Driver: %s",
                       enable_switch.hw_switch.number, coil.hw_driver.number)

        self._add_pulse_and_hold_rule_to_switch(enable_switch, coil)
        self._add_release_disable_rule_to_switch(enable_switch, coil)

        self._write_rules_to_switch(enable_switch, coil, False)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 disable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and release and disable rule on driver."""
        self.debug_log("Setting Pulse on hit and enable and release and disable HW Rule. Enable Switch: %s,"
                       "Disable Switch: %s, Driver: %s", enable_switch.hw_switch.number,
                       disable_switch.hw_switch.number, coil.hw_driver.number)

        self._add_pulse_and_hold_rule_to_switch(enable_switch, coil)
        self._add_release_disable_rule_to_switch(enable_switch, coil)
        self._add_disable_rule_to_switch(disable_switch, coil)

        self._write_rules_to_switch(enable_switch, coil, False)
        self._write_rules_to_switch(disable_switch, coil, False)

    def clear_hw_rule(self, switch, coil):
        """Clear a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        Args:
            switch: Switch object
            coil: Coil object
        """
        self.debug_log("Clearing HW rule for switch: %s coil: %s", switch.hw_switch.number, coil.hw_driver.number)

        coil_number = False
        for entry, element in switch.hw_switch.hw_rules.items():
            if not element:
                continue
            for rule_num, rule in enumerate(element):
                if rule[0] == switch.hw_switch.number and rule[1] == coil.hw_driver.number:
                    coil_number = rule[2]['driverNum']
                    del switch.hw_switch.hw_rules[entry][rule_num]

        if coil_number:
            self.proc.driver_disable(coil_number)
            self._write_rules_to_switch(switch, coil, None)

        return bool(coil_number)

    def _get_default_subtype(self):
        """Return default subtype for either P3-Roc or P-Roc."""
        raise NotImplementedError

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse light number to a list of channels."""
        if not subtype:
            subtype = self._get_default_subtype()
        if subtype == "matrix":
            return [
                {
                    "number": number
                }
            ]
        elif subtype == "led":
            # split the number (which comes in as a string like w-x-y-z) into parts
            number_parts = str(number).split('-')

            if len(number_parts) != 4:
                raise AssertionError("Invalid address for LED {}".format(number))

            return [
                {
                    "number": number_parts[0] + "-" + number_parts[1]
                },
                {
                    "number": number_parts[0] + "-" + number_parts[2]
                },
                {
                    "number": number_parts[0] + "-" + number_parts[3]
                },
            ]
        else:
            raise AssertionError("Unknown subtype {}".format(subtype))

    def configure_light(self, number, subtype, platform_settings) -> LightPlatformInterface:
        """Configure a light channel."""
        if not subtype:
            subtype = self._get_default_subtype()
        if subtype == "matrix":
            if self.machine_type == self.pinproc.MachineTypePDB:
                proc_num = self.pdbconfig.get_proc_light_number(str(number))
                if proc_num == -1:
                    raise AssertionError("Matrixlight {} cannot be controlled by the P-ROC. ".format(
                        str(number)))

            else:
                proc_num = self.pinproc.decode(self.machine_type, str(number))

            return PROCMatrixLight(proc_num, self.proc, self.machine)
        elif subtype == "led":
            board, index = number.split("-")
            polarity = platform_settings and platform_settings.get("polarity", False)
            return PDBLED(int(board), int(index), polarity, self.proc, self.config.get("debug", False))
        else:
            raise AssertionError("unknown subtype {}".format(subtype))

    def _configure_switch(self, config: SwitchConfig, proc_num):
        """Configure a P3-ROC switch.

        Args:
            config: Dictionary of settings for the switch.
            proc_num: decoded switch number

        Returns:
            switch : A reference to the switch object that was just created.
            proc_num : Integer of the actual hardware switch number the P3-ROC
                uses to refer to this switch. Typically your machine
                configuration files would specify a switch number like `SD12` or
                `7/5`. This `proc_num` is an int between 0 and 255.
        """
        if proc_num == -1:
            raise AssertionError("Switch {} cannot be controlled by the "
                                 "P-ROC/P3-ROC.".format(proc_num))

        switch = PROCSwitch(config, proc_num, config.debounce == "quick", self)
        # The P3-ROC needs to be configured to notify the host computers of
        # switch events. (That notification can be for open or closed,
        # debounced or nondebounced.)
        self.debug_log("Configuring switch's host notification settings. P3-ROC"
                       "number: %s, debounce: %s", proc_num,
                       config.debounce)
        if config.debounce == "quick":
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
        return switch


class PDBConfig(object):

    """Handles PDB Config of the P/P3-Roc.

    This class is only used when using the P3-ROC or when the P-ROC is configured to use PDB
    driver boards such as the PD-16 or PD-8x8. i.e. not when it's operating in
    WPC or Stern mode.
    """

    indexes = []    # type: List[Any]
    proc = None     # type: pinproc.PinPROC

    def __init__(self, proc, config, driver_count):
        """Set up PDB config.

        Will configure driver groups for matrixes, lamps and normal drivers.
        """
        self.log = logging.getLogger('PDBConfig')
        self.log.debug("Processing PDB Driver Board configuration")

        self.proc = proc

        # Set config defaults
        self.lamp_matrix_strobe_time = config['p_roc']['lamp_matrix_strobe_time']
        self.watchdog_time = config['p_roc']['watchdog_time']
        self.use_watchdog = config['p_roc']['use_watchdog']

        # Initialize some lists for data collecting
        coil_bank_list = self._load_coil_bank_list_from_config(config)
        lamp_source_bank_list, lamp_list, lamp_list_for_index = self._load_lamp_lists_from_config(config)

        # Create a list of indexes.  The PDB banks will be mapped into this
        # list. The index of the bank is used to calculate the P-ROC/P3-ROC driver
        # number for each driver.
        num_proc_banks = driver_count // 8
        self.indexes = [{}] * num_proc_banks    # type: List[Union[int, dict]]

        self._initialize_drivers(proc)

        # Set up dedicated driver groups (groups 0-3).
        for group_ctr in range(0, 4):
            # PDB Banks 0-3 are interpreted as dedicated bank here. Therefore, we do not use them.
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

        # Process lamps first. The P-ROC/P3-ROC can only control so many drivers
        # directly. Since software won't have the speed to control lamp
        # matrixes, map the lamps first. If there aren't enough driver
        # groups for coils, the overflow coils can be controlled by software
        # via VirtualDrivers (which should get set up automatically by this
        # code.)

        for i, lamp_dict in enumerate(lamp_list):
            # If the bank is 16 or higher, the P-ROC/P3-ROC can't control it
            # directly. Software can't really control lamp matrixes either
            # (need microsecond resolution).  Instead of doing crazy logic here
            # for a case that probably won't happen, just ignore these banks.
            if group_ctr >= num_proc_banks or lamp_dict['sink_bank'] >= 16:
                raise AssertionError("Lamp matrix banks can't be mapped to index "
                                     "{} because that's outside of the banks the "
                                     "P-ROC/P3-ROC can control.".format(lamp_dict['sink_bank']))
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
            # If the bank is 16 or higher, the P-ROC/P3-ROC can't control it directly.
            # Software will have do the driver logic and write any changes to
            # the PDB bus. Therefore, map these banks to indexes above the
            # driver count, which will force the drivers to be created
            # as VirtualDrivers. Appending the bank avoids conflicts when
            # group_ctr gets too high.

            if group_ctr >= num_proc_banks or coil_bank >= 32:
                self.log.warning("Driver group %d mapped to driver index"
                                 "outside of P-ROC/P3-ROC control.  These Drivers "
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

        # Now set up globals.  First disable them to allow the P-ROC/P3-ROC to set up
        # the polarities on the Drivers.  Then enable them.
        self._configure_lamp_banks(proc, lamp_source_bank_list, False)
        self._configure_lamp_banks(proc, lamp_source_bank_list, True)

    def is_pdb_address(self, addr):
        """Return True if the given address is a valid PDB address."""
        try:
            self.decode_pdb_address(addr=addr)
            return True
        except ValueError:
            return False

    @staticmethod
    def decode_pdb_address(addr):
        """Decode Ax-By-z or x/y/z into PDB address, bank number, and output number.

        Raises a ValueError exception if it is not a PDB address, otherwise returns
        a tuple of (addr, bank, number).

        """
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
            raise ValueError('PDB address delimiter (- or /) not found.')

    def _load_lamp_lists_from_config(self, config):
        lamp_source_bank_list = []
        lamp_list = []
        lamp_list_for_index = []

        # Make a list of unique lamp source banks.  The P-ROC/P3-ROC only supports 2.
        # If this is exceeded we will error out later.
        if 'lights' in config:
            for name in config['lights']:
                item_dict = config['lights'][name]
                if "subtype" not in item_dict or item_dict["subtype"] != "matrix":
                    continue
                lamp = PDBLight(self, str(item_dict['number']))

                # Catalog PDB banks
                # Dedicated lamps don't use PDB banks. They use P-ROC direct
                # driver pins (not available on P3-ROC).
                if lamp.lamp_type == 'dedicated':
                    pass

                elif lamp.lamp_type == 'pdb':
                    if lamp.source_bank() not in lamp_source_bank_list:
                        lamp_source_bank_list.append(lamp.source_bank())

                    # Create dicts of unique sink banks.  The source index is
                    # needed when setting up the driver groups.
                    lamp_dict = {'source_index':
                                 lamp_source_bank_list.index(lamp.source_bank()),
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

        return lamp_source_bank_list, lamp_list, lamp_list_for_index

    def _load_coil_bank_list_from_config(self, config):
        coil_bank_list = []

        # Make a list of unique coil banks
        if 'coils' in config:
            for name in config['coils']:
                item_dict = config['coils'][name]
                coil = PDBCoil(self, str(item_dict['number']))
                if coil.bank() not in coil_bank_list:
                    coil_bank_list.append(coil.bank())

        return coil_bank_list

    @classmethod
    def _initialize_drivers(cls, proc):
        """Loop through all of the drivers, initializing them with the polarity."""
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

    def _configure_lamp_banks(self, proc, lamp_source_bank_list, enable=True):
        proc.driver_update_global_config(enable,
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

        if enable:
            self.log.debug("Configuring PDB Driver Globals:  polarity = %s  "
                           "matrix column index 0 = %d  matrix column index "
                           "1 = %d", True, lamp_source_bank_list[0],
                           lamp_source_bank_list[1])

    def get_proc_coil_number(self, number_str):
        """Get the actual number of a coil from the bank index config.

        Args:
            number_str (str): PDB string
        """
        coil = PDBCoil(self, number_str)
        bank = coil.bank()
        if bank == -1:
            return -1
        index = self.indexes.index(coil.bank())
        num = index * 8 + coil.output()
        return num

    def get_proc_light_number(self, number_str):
        """Get the actual number of a light from the lamp config.

        Args:
            number_str (str): PDB string
        """
        lamp = PDBLight(self, number_str)
        if lamp.lamp_type == 'unknown':
            return -1
        elif lamp.lamp_type == 'dedicated':
            return lamp.dedicated_output()

        lamp_dict_for_index = {'source_board': lamp.source_board(),
                               'sink_bank': lamp.sink_bank(),
                               'source_output': lamp.source_output()}
        if lamp_dict_for_index not in self.indexes:
            raise AssertionError("Light not in lamp dict")
        index = self.indexes.index(lamp_dict_for_index)
        num = index * 8 + lamp.sink_output()
        return num

    def get_proc_switch_number(self, number_str):
        """Get the actual number of a switch based on the string only.

        Args:
            number_str (str): PDB string
        """
        switch = PDBSwitch(self, number_str)
        num = switch.proc_num()
        return num


class PDBSwitch(object):

    """Base class for switches connected to a P-ROC/P3-ROC."""

    def __init__(self, pdb, number_str):
        """Find out the number of the switch."""
        upper_str = number_str.upper()
        if upper_str.startswith('SD'):  # only P-ROC
            self.sw_number = int(upper_str[2:])
        elif upper_str.count("/") == 1:  # only P-ROC
            self.sw_number = self.parse_matrix_num(upper_str)
        else:   # only P3-Roc
            try:
                (boardnum, banknum, inputnum) = pdb.decode_pdb_address(number_str)
                self.sw_number = boardnum * 16 + banknum * 8 + inputnum
            except ValueError:
                try:
                    self.sw_number = int(number_str)
                except ValueError:  # pragma: no cover
                    raise AssertionError('Switch {} is invalid. Use either PDB '
                                         'format or an int'.format(str(number_str)))

    def proc_num(self):
        """Return the number of the switch."""
        return self.sw_number

    @classmethod
    def parse_matrix_num(cls, num_str):
        """Parse a source/sink matrix tuple."""
        cr_list = num_str.split('/')
        return 32 + int(cr_list[0]) * 16 + int(cr_list[1])


class PDBCoil(object):

    """Base class for coils connected to a P-ROC/P3-ROC that are controlled via PDB driver boards.

    (i.e. the PD-16 board).
    """

    def __init__(self, pdb, number_str):
        """Find out number fo coil."""
        upper_str = number_str.upper()
        self.pdb = pdb
        if self.is_direct_coil(upper_str):
            self.coil_type = 'dedicated'
            self.banknum = (int(number_str[1:]) - 1) / 8
            self.outputnum = int(number_str[1:])
        elif self.is_pdb_coil(number_str):
            self.coil_type = 'pdb'
            (self.boardnum, self.banknum, self.outputnum) = pdb.decode_pdb_address(number_str)
        else:
            self.coil_type = 'unknown'

    def bank(self) -> int:
        """Return the bank number."""
        if self.coil_type == 'dedicated':
            return self.banknum
        elif self.coil_type == 'pdb':
            return self.boardnum * 2 + self.banknum

        return -1

    def output(self):
        """Return the output number."""
        return self.outputnum

    @classmethod
    def is_direct_coil(cls, string):
        """Return true if it is a direct coil."""
        if len(string) < 2 or len(string) > 3:
            return False
        if not string[0] == 'C':
            return False
        if not string[1:].isdigit():
            return False
        return True

    def is_pdb_coil(self, string):
        """Return true if string looks like PDB address."""
        return self.pdb.is_pdb_address(string)


class PDBLight(object):

    """Base class for lights connected to a PD-8x8 driver board."""

    def __init__(self, pdb, number_str):
        """Find out light number."""
        self.pdb = pdb
        upper_str = number_str.upper()
        if self.is_direct_lamp(upper_str):
            self.lamp_type = 'dedicated'
            self.output = int(number_str[1:])
        elif self.is_pdb_lamp(number_str):
            # C-Ax-By-z:R-Ax-By-z  or  C-x/y/z:R-x/y/z
            self.lamp_type = 'pdb'
            source_addr, sink_addr = self.split_matrix_addr_parts(number_str)
            (self.source_boardnum, self.source_banknum, self.source_outputnum) = pdb.decode_pdb_address(source_addr)
            (self.sink_boardnum, self.sink_banknum, self.sink_outputnum) = pdb.decode_pdb_address(sink_addr)
        else:
            self.lamp_type = 'unknown'

    def source_board(self):
        """Return source board."""
        return self.source_boardnum

    def source_bank(self):
        """Return source bank."""
        return self.source_boardnum * 2 + self.source_banknum

    def sink_bank(self):
        """Return sink bank."""
        return self.sink_boardnum * 2 + self.sink_banknum

    def source_output(self):
        """Return source output."""
        return self.source_outputnum

    def sink_output(self):
        """Return sink output."""
        return self.sink_outputnum

    def dedicated_output(self):
        """Return dedicated output number."""
        return self.output

    @classmethod
    def is_direct_lamp(cls, string):
        """Return true if it looks like a direct lamp."""
        if len(string) < 2 or len(string) > 3:
            return False
        if not string[0] == 'L':
            return False
        if not string[1:].isdigit():
            return False
        return True

    @classmethod
    def split_matrix_addr_parts(cls, string):
        """Split the string of a matrix lamp address.

        Input is of form C-Ax-By-z:R-Ax-By-z  or  C-x/y/z:R-x/y/z  or
        aliasX:aliasY.  We want to return only the address part: Ax-By-z,
        x/y/z, or aliasX.  That is, remove the two character prefix if present.
        """
        addrs = string.rsplit(':')
        if len(addrs) != 2:
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
        """Return true if it looks like a pdb lamp string."""
        params = self.split_matrix_addr_parts(string)
        if len(params) != 2:
            return False
        for addr in params:
            if not self.pdb.is_pdb_address(addr):
                return False
        return True


class PDBLED(LightPlatformInterface):

    """Represents an RGB LED connected to a PD-LED board."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, board, address, polarity, proc_driver, debug):
        """Initialise PDB LED."""
        self.board = board
        self.address = address
        self.debug = debug
        super().__init__("{}-{}".format(self.board, self.address))
        self.log = logging.getLogger('PDBLED')
        self.proc = proc_driver
        self.polarity = polarity

        self.log.debug("Creating PD-LED item: board: %s, "
                       "RGB output: %s", self.board, self.address)

    def _normalise_color(self, value: int) -> int:
        if self.polarity:
            return 255 - value

        return value

    def set_fade(self, color_and_fade_callback: Callable[[int], Tuple[float, int]]):
        """Set or fade this LED to the color passed.

        Can fade for up to 100 days so do not bother about too long fades.

        Args:
            color_and_fade_callback: brightness of this channel via callback
        """
        brightness, fade_ms = color_and_fade_callback(int(pow(2, 31) * 4))
        if self.debug:
            self.log.debug("Setting color %s with fade_ms %s to %s-%s",
                           self._normalise_color(int(brightness * 255)), fade_ms, self.board, self.address)

        if fade_ms <= 0:
            # just set color
            self.proc.led_color(self.board, self.address, self._normalise_color(int(brightness * 255)))
        else:
            # fade to color
            self.proc.led_fade(self.board, self.address, self._normalise_color(int(brightness * 255)), int(fade_ms / 4))

    def get_board_name(self):
        """Return board of the light."""
        return "PD-LED Board {}".format(self.board)
