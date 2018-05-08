"""Contains the drivers and interface code for pinball machines which use the Multimorphic R-ROC hardware controllers.

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
import asyncio

from mpf.core.platform import DmdPlatform, DriverConfig, SwitchConfig, SegmentDisplayPlatform
from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface
from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface
from mpf.platforms.p_roc_common import PDBConfig, PROCBasePlatform
from mpf.core.utility_functions import Util
from mpf.platforms.p_roc_devices import PROCDriver


class PRocHardwarePlatform(PROCBasePlatform, DmdPlatform, SegmentDisplayPlatform):

    """Platform class for the P-ROC hardware controller.

    Args:
        machine: The MachineController instance.

    Attributes:
        machine: The MachineController instance.
    """

    def __init__(self, machine):
        """Initialise P-ROC."""
        super().__init__(machine)
        self.log = logging.getLogger('P-ROC')
        self.debug_log("Configuring P-ROC hardware")

        # validate config for p_roc
        self.config = self.machine.config_validator.validate_config("p_roc", self.machine.config['p_roc'])

        self.dmd = None
        self.alpha_display = None

        self.connect()

        self.aux_port = AuxPort(self)
        self.aux_port.reset()

        # Because PDBs can be configured in many different ways, we need to
        # traverse the YAML settings to see how many PDBs are being used.
        # Then we can configure the P-ROC appropriately to use those PDBs.
        # Only then can we relate the YAML coil/light #'s to P-ROC numbers for
        # the collections.
        if self.machine_type == self.pinproc.MachineTypePDB:
            self.debug_log("Configuring P-ROC for PDBs (P-ROC driver boards)")
            self.pdbconfig = PDBConfig(self.proc, self.machine.config, self.pinproc.DriverCount)

        else:
            self.debug_log("Configuring P-ROC for OEM driver boards")

    def _get_default_subtype(self):
        """Return default subtype for P-Roc."""
        return "matrix"

    def __repr__(self):
        """Return string representation."""
        return '<Platform.P-ROC>'

    def get_info_string(self):
        """Dump infos about boards."""
        infos = "Firmware Version: {} Firmware Revision: {} Hardware Board ID: {}\n".format(
            self.version, self.revision, self.hardware_version)
        return infos

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
        """Create a P-ROC driver.

        Typically drivers are coils or flashers, but for the P-ROC this is
        also used for matrix-based lights.

        Args:
            config: Dictionary of settings for the driver.

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

        if self.machine_type == self.pinproc.MachineTypePDB:
            proc_num = self.pdbconfig.get_proc_coil_number(str(number))
            if proc_num == -1:
                raise AssertionError("Driver {} cannot be controlled by the P-ROC. ".format(str(number)))
        else:
            proc_num = self.pinproc.decode(self.machine_type, str(number))

        return PROCDriver(proc_num, config, self, number)

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict):
        """Configure a P-ROC switch.

        Args:
            number: String number of the switch to configure.
            config: SwitchConfig settings.

        Returns: A configured switch object.

        """
        del platform_config
        if self.machine_type == self.pinproc.MachineTypePDB:
            proc_num = self.pdbconfig.get_proc_switch_number(str(number))
            if proc_num == -1:
                raise AssertionError("Switch {} cannot be controlled by the P-ROC. ".format(str(number)))

        else:
            proc_num = self.pinproc.decode(self.machine_type, str(number))
        return self._configure_switch(config, proc_num)

    @asyncio.coroutine
    def get_hw_switch_states(self):
        """Read in and set the initial switch state.

        The P-ROC uses the following values for hw switch states:
        1 - closed (debounced)
        2 - open (debounced)
        3 - closed (not debounced)
        4 - open (not debounced)
        """
        states = self.proc.switch_get_states()

        for switch, state in enumerate(states):
            if state == 3 or state == 1:
                states[switch] = 1
            else:
                states[switch] = 0

        return states

    def configure_dmd(self):
        """Configure a hardware DMD connected to a classic P-ROC."""
        self.dmd = PROCDMD(self.pinproc, self.proc, self.machine)
        return self.dmd

    def configure_segment_display(self, number: str) -> "SegmentDisplayPlatformInterface":
        """Configure display."""
        number_int = int(number)
        if 0 < number_int >= 4:
            raise AssertionError("Number must be between 0 and 3 for p_roc segment display.")

        if not self.alpha_display:
            self.alpha_display = AuxAlphanumericDisplay(self, self.aux_port)

        return PRocAlphanumericDisplay(self.alpha_display, number_int)

    def tick(self):
        """Check the P-ROC for any events (switch state changes or notification that a DMD frame was updated).

        Also tickles the watchdog and flushes any queued commands to the P-ROC.
        """
        # Get P-ROC events (switches & DMD frames displayed)
        for event in self.proc.get_events():
            event_type = event['type']
            event_value = event['value']
            if event_type == self.pinproc.EventTypeDMDFrameDisplayed:
                pass
            elif event_type == self.pinproc.EventTypeSwitchClosedDebounced:
                self.machine.switch_controller.process_switch_by_num(
                    state=1, num=event_value, platform=self)
            elif event_type == self.pinproc.EventTypeSwitchOpenDebounced:
                self.machine.switch_controller.process_switch_by_num(
                    state=0, num=event_value, platform=self)
            elif event_type == self.pinproc.EventTypeSwitchClosedNondebounced:
                self.machine.switch_controller.process_switch_by_num(
                    state=1, num=event_value, platform=self)
            elif event_type == self.pinproc.EventTypeSwitchOpenNondebounced:
                self.machine.switch_controller.process_switch_by_num(
                    state=0, num=event_value, platform=self)
            else:
                self.log.warning("Received unrecognized event from the P-ROC. "
                                 "Type: %s, Value: %s", event_type, event_value)

        self.proc.watchdog_tickle()
        self.proc.flush()


class PROCDMD(DmdPlatformInterface):

    """Parent class for a physical DMD attached to a P-ROC.

    Args:
        proc: Reference to the MachineController's proc attribute.
        machine: Reference to the MachineController

    Attributes:
        dmd: Reference to the P-ROC's DMD buffer.

    """

    def __init__(self, pinproc, proc, machine):
        """Set up DMD."""
        self.proc = proc
        self.machine = machine

        # size is hardcoded here since 128x32 is all the P-ROC hw supports
        self.dmd = pinproc.DMDBuffer(128, 32)

        # dmd_timing defaults should be 250, 400, 180, 800
        if self.machine.config['p_roc']['dmd_timing_cycles']:
            dmd_timing = Util.string_to_list(
                self.machine.config['p_roc']['dmd_timing_cycles'])

            self.proc.dmd_update_config(high_cycles=dmd_timing)

    def set_brightness(self, brightness: float):
        """Set brightness."""
        # currently not supported. can be implemented using dmd_timing_cycles
        assert brightness == 1.0

    def update(self, data):
        """Update the DMD with a new frame.

        Args:
            data: A 4096-byte raw string.

        """
        if len(data) == 4096:
            self.dmd.set_data(data)
            self.proc.dmd_draw(self.dmd)
        else:
            self.machine.log.warning("Received DMD frame of length %s instead"
                                     "of 4096. Discarding...", len(data))


class AuxPort(object):

    """Aux port on the P-Roc."""

    def __init__(self, platform):
        """Initialise aux port."""
        self.platform = platform
        self._commands = []

    def reset(self):
        """Reset aux port."""
        commands = [self.platform.pinproc.aux_command_disable()]

        for _ in range(1, 255):
            commands += [self.platform.pinproc.aux_command_jump(0)]

        self.platform.proc.aux_send_commands(0, commands)

    def reserve_index(self):
        """Return index of next free command slot and reserve it."""
        self._commands += [[]]
        return len(self._commands) - 1

    def update(self, index, commands):
        """Update command slot with command."""
        self._commands[index] = commands
        self._write_commands()

    def _write_commands(self):
        """Write commands to hardware."""
        # disable program
        commands = [self.platform.pinproc.aux_command_disable()]
        # build command list
        for command_set in self._commands:
            commands += command_set
        self.platform.proc.aux_send_commands(0, commands)

        # jump from slot 0 to slot 1. overwrites the disable
        self.platform.proc.aux_send_commands(0, [self.platform.pinproc.aux_command_jump(1)])


class PRocAlphanumericDisplay(SegmentDisplayPlatformInterface):

    """Since AuxAlphanumericDisplay updates all four displays wrap it and set the correct offset."""

    def __init__(self, display, index):
        """Initialise alpha numeric display."""
        super().__init__(index)
        self.display = display

    def set_text(self, text: str, flashing: bool):
        """Set digits to display."""
        # TODO: handle flashing using delay
        self.display.set_text(text, self.number)


class AuxAlphanumericDisplay(object):

    """An alpha numeric display connected to the aux port on the P-Roc."""

    # Start at ASCII table offset 32: ' '
    asciiSegments = [0x0000,  # ' '
                     0x016a,  # '!' Random Debris Character 1
                     0x3014,  # '"' Random Debris Character 2
                     0x5d80,  # '#' Random Debris Character 3
                     0x00a4,  # '$' Random Debris Character 4
                     0x3270,  # '%' Random Debris Character 5
                     0x4640,  # '&' Random Debris Character 6
                     0x0200,  # '''
                     0x1400,  # '('
                     0x4100,  # ')'
                     0x7f40,  # '*'
                     0x2a40,  # '+'
                     0x8080,  # ','
                     0x0840,  # '-'
                     0x8000,  # '.'
                     0x4400,  # '/'

                     0x003f,  # '0'
                     0x0006,  # '1'
                     0x085b,  # '2'
                     0x084f,  # '3'
                     0x0866,  # '4'
                     0x086d,  # '5'
                     0x087d,  # '6'
                     0x0007,  # '7'
                     0x087f,  # '8'
                     0x086f,  # '9'

                     0x0821,  # ':' Random Debris Character 7
                     0x1004,  # ';' Random Debris Character 8
                     0x1c00,  # '<' Left Arrow
                     0x1386,  # '=' Random Debris Character 9
                     0x4140,  # '>' Right Arrow
                     0x0045,  # '?' Random Debris Character 10
                     0x4820,  # '@' Random Debris Character 11

                     0x0877,  # 'A'
                     0x2a4f,  # 'B'
                     0x0039,  # 'C'
                     0x220f,  # 'D'
                     0x0879,  # 'E'
                     0x0871,  # 'F'
                     0x083d,  # 'G'
                     0x0876,  # 'H'
                     0x2209,  # 'I'
                     0x001e,  # 'J'
                     0x1470,  # 'K'
                     0x0038,  # 'L'
                     0x0536,  # 'M'
                     0x1136,  # 'N'
                     0x003f,  # 'O'
                     0x0873,  # 'P'
                     0x103f,  # 'Q'
                     0x1873,  # 'R'
                     0x086d,  # 'S'
                     0x2201,  # 'T'
                     0x003e,  # 'U'
                     0x4430,  # 'V'
                     0x5036,  # 'W'
                     0x5500,  # 'X'
                     0x2500,  # 'Y'
                     0x4409,  # 'Z'

                     0x6004,  # '[' Random Debris Character 12
                     0x6411,  # '\' Random Debris Character 13
                     0x780a,  # ']' Random Debris Character 14
                     0x093a,  # '^' Random Debris Character 15
                     0x0008,  # '_'
                     0x2220,  # '`' Random Debris Character 16

                     0x0c56,  # 'a' Broken Letter a
                     0x684e,  # 'b' Broken Letter b
                     0x081c,  # 'c' Broken Letter c
                     0x380e,  # 'd' Broken Letter d
                     0x1178,  # 'e' Broken Letter e
                     0x4831,  # 'f' Broken Letter f
                     0x083d,  # 'g' Broken Letter g NOT CREATED YET
                     0x0854,  # 'h' Broken Letter h
                     0x2209,  # 'i' Broken Letter i NOT CREATED YET
                     0x001e,  # 'j' Broken Letter j NOT CREATED YET
                     0x1070,  # 'k' Broken Letter k
                     0x0038,  # 'l' Broken Letter l NOT CREATED YET
                     0x0536,  # 'm' Broken Letter m NOT CREATED YET
                     0x1136,  # 'n' Broken Letter n NOT CREATED YET
                     0x085c,  # 'o' Broken Letter o
                     0x0873,  # 'p' Broken Letter p NOT CREATED YET
                     0x103f,  # 'q' Broken Letter q NOT CREATED YET
                     0x1c72,  # 'r' Broken Letter r
                     0x116c,  # 's' Broken Letter s
                     0x2120,  # 't' Broken Letter t
                     0x003e,  # 'u' Broken Letter u NOT CREATED YET
                     0x4430,  # 'v' Broken Letter v NOT CREATED YET
                     0x5036,  # 'w' Broken Letter w NOT CREATED YET
                     0x5500,  # 'x' Broken Letter x NOT CREATED YET
                     0x2500,  # 'y' Broken Letter y NOT CREATED YET
                     0x4409   # 'z' Broken Letter z NOT CREATED YET
                     ]

    strobes = [8, 9, 10, 11, 12]
    full_intensity_delay = 350  # microseconds
    inter_char_delay = 40       # microseconds

    def __init__(self, platform, aux_controller):
        """Initialise the alphanumeric display."""
        self.platform = platform
        self.aux_controller = aux_controller
        self.aux_index = aux_controller.reserve_index()
        self.texts = ["        "] * 4

    def set_text(self, text, index):
        """Set text for display."""
        if len(text) != 8:
            text = text[0:8].rjust(8, ' ')
        self.texts[index] = text

        # build expected format
        input_strings = [self.texts[0] + self.texts[1], self.texts[2] + self.texts[3]]
        self.display(input_strings)

    def display(self, input_strings, intensities=None):
        """Set display text."""
        strings = []

        if intensities is None:
            intensities = [[1] * 16] * 2

        # Make sure strings are at least 16 chars.
        # Then convert each string to a list of chars.
        for j in range(0, 2):
            input_strings[j] = input_strings[j]
            if len(input_strings[j]) < 16:
                input_strings[j] += ' ' * (16 - len(input_strings[j]))
            strings += [list(input_strings[j])]

        # Make sure insensities are 1 or less
        for i in range(0, 16):
            for j in range(0, 2):
                if intensities[j][i] > 1:
                    intensities[j][i] = 1

        commands = []
        char_on_time = []
        char_off_time = []

        # Initialize a 2x16 array for segments value
        segs = [[0] * 16 for _ in range(2)]

        # Loop through each character
        for i in range(0, 16):

            # Activate the character position (this goes to both displayas)
            commands += [self.platform.pinproc.aux_command_output_custom(i, 0, self.strobes[0], False, 0)]

            for j in range(0, 2):
                segs[j][i] = self.asciiSegments[ord(strings[j][i]) - 32]

                # Check for commas or periods.
                # If found, squeeze comma into previous character.
                # No point checking the last character (plus, this avoids an
                # indexing error by not checking i+1 on the 16th char.
                if i < 15:
                    comma_dot = strings[j][i + 1]
                    if comma_dot == "," or comma_dot == ".":
                        segs[j][i] |= self.asciiSegments[ord(comma_dot) - 32]
                        strings[j].remove(comma_dot)
                        # Append a space to ensure there are enough chars.
                        strings[j].append(' ')
                # character is 16 bits long, characters are loaded in 2 lots of 8 bits,
                # for each display (4 enable lines total)
                commands += [self.platform.pinproc.aux_command_output_custom(
                    segs[j][i] & 0xff, 0,
                    self.strobes[j * 2 + 1], False, 0)]     # first 8 bits of characater data
                commands += [self.platform.pinproc.aux_command_output_custom(
                    (segs[j][i] >> 8) & 0xff, 0,
                    self.strobes[j * 2 + 2], False, 0)]     # second 8 bits of characater data

                char_on_time += [intensities[j][i] * self.full_intensity_delay]
                char_off_time += [self.inter_char_delay + (self.full_intensity_delay - char_on_time[j])]

            if char_on_time[0] < char_on_time[1]:
                first = 0
                second = 1
            else:
                first = 1
                second = 0

            # Determine amount of time to leave the other char on after the
            # first is off.
            between_delay = char_on_time[second] - char_on_time[first]

            # Not sure if the hardware will like a delay of 0
            # Use 2 to be extra safe.  2 microseconds won't affect display.
            if between_delay == 0:
                between_delay = 2

            # Delay until it's time to turn off the character with the lowest intensity
            commands += [self.platform.pinproc.aux_command_delay(char_on_time[first])]
            commands += [self.platform.pinproc.aux_command_output_custom(0, 0, self.strobes[first * 2 + 1], False, 0)]
            commands += [self.platform.pinproc.aux_command_output_custom(0, 0, self.strobes[first * 2 + 2], False, 0)]

            # Delay until it's time to turn off the other character.
            commands += [self.platform.pinproc.aux_command_delay(between_delay)]
            commands += [self.platform.pinproc.aux_command_output_custom(0, 0, self.strobes[second * 2 + 1], False, 0)]
            commands += [self.platform.pinproc.aux_command_output_custom(0, 0, self.strobes[second * 2 + 2], False, 0)]

            # Delay for the inter-digit delay.
            commands += [self.platform.pinproc.aux_command_delay(char_off_time[second])]

        # Send the new list of commands to the Aux port controller.
        self.aux_controller.update(self.aux_index, commands)
