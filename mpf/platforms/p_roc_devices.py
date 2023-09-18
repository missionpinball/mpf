"""P-Roc hardware platform devices."""
from typing import Tuple, Optional

import asyncio
import logging

from mpf.core.platform_batch_light_system import PlatformBatchLight
from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface

from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.core.utility_functions import Util

MYPY = False
if MYPY:    # pragma: no cover
    from mpf.platforms.p_roc_common import PROCBasePlatform     # pylint: disable-msg=cyclic-import,unused-import


class PROCSwitch(SwitchPlatformInterface):

    """P-ROC switch object which is use to store the configure rules and config."""

    __slots__ = ["string_number", "log", "notify_on_nondebounce", "hw_rules", "pdbconfig"]

    def __init__(self, config, number, notify_on_nondebounce, platform):
        """initialize P-ROC switch."""
        super().__init__(config, number, platform)
        self.string_number = number
        self.log = logging.getLogger('PROCSwitch {}'.format(self.string_number))
        self.notify_on_nondebounce = notify_on_nondebounce
        self.hw_rules = {"closed_debounced": [],
                         "closed_nondebounced": [],
                         "open_debounced": [],
                         "open_nondebounced": []}
        self.pdbconfig = getattr(platform, "pdbconfig", None)

    def get_board_name(self):
        """Return board of the switch."""
        if not self.pdbconfig:
            return "P-Roc"

        board, bank, _ = self.pdbconfig.decode_pdb_address(self.string_number)

        return "SW-16 Board {} Bank {}".format(board, bank)

    @property
    def has_rules(self):
        """Return true as we support hardware rules."""
        return True


class PROCDriver(DriverPlatformInterface):

    """A P-ROC driver/coil.

    Base class for drivers connected to a P3-ROC. This class is used for all
    drivers, regardless of whether they're connected to a P-ROC driver board
    (such as the PD-16 or PD-8x8) or an OEM driver board.

    """

    __slots__ = ["log", "proc", "string_number", "pdbconfig", "polarity", "__dict__"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, number, config, platform, string_number, polarity):
        """initialize driver."""
        self.log = logging.getLogger('PROCDriver {}'.format(number))
        super().__init__(config, number)
        self.platform = platform            # type: PROCBasePlatform
        self.polarity = polarity
        self.string_number = string_number
        self.pdbconfig = getattr(platform, "pdbconfig", None)

    async def initialize(self):
        """Initialize driver."""
        if self.polarity is None:
            self.log.debug("Getting polarity for driver %s", self.number)
            state = await self.platform.run_proc_cmd("driver_get_state", self.number)
            self.polarity = state["polarity"]
            self.log.debug("Got Polarity %s for driver %s", self.polarity, self.number)

        self.log.debug("Driver Settings for %s", self.number)
        self.platform.run_proc_cmd_no_wait("driver_update_state", self.state())

    def get_board_name(self):
        """Return board of the driver."""
        if not self.pdbconfig:
            return "P-Roc"

        board, bank, _ = self.pdbconfig.decode_pdb_address(self.string_number)

        return "PD-16 Board {} Bank {}".format(board, bank)

    @classmethod
    def get_pwm_on_off_ms(cls, coil: HoldSettings):
        """Find out the pwm_on_ms and pwm_off_ms for this driver."""
        return Util.power_to_on_off(coil.power)

    def disable(self):
        """Disable (turn off) this driver."""
        self.log.debug('Disabling Driver')
        self.platform.run_proc_cmd_no_wait("driver_disable", self.number)

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable (turn on) this driver."""
        if pulse_settings.power != 1:
            raise AssertionError("pulse_power != 1.0 with hold/enable is not supported in P/P3-Roc.")

        if hold_settings.power < 1.0:
            pwm_on, pwm_off = self.get_pwm_on_off_ms(hold_settings)
            self.log.debug('Enabling. Initial pulse_ms:%s, pwm_on_ms: %s'
                           'pwm_off_ms: %s', pwm_on, pwm_off, pulse_settings.duration)

            self.platform.run_proc_cmd_no_wait("driver_patter", self.number, pwm_on, pwm_off,
                                               pulse_settings.duration, True)
        else:
            self.log.debug('Enabling at 100%')

            self.platform.run_proc_cmd_no_wait("driver_schedule", self.number, 0xffffffff, 0, True)

    def pulse(self, pulse_settings: PulseSettings):
        """Enable this driver for `milliseconds`.

        ``ValueError`` will be raised if `milliseconds` is outside of the range
        0-255.
        """
        # make sure we never set 0 (due to a bug elsewhere) as this would turn the driver on permanently
        assert pulse_settings.duration != 0

        self.log.debug('Pulsing for %sms at %s pulse power.', pulse_settings.duration, pulse_settings.power)
        if pulse_settings.power != 1:
            on_time, off_time = Util.power_to_on_off(pulse_settings.power)
            self.platform.run_proc_cmd_no_wait("driver_pulsed_patter", self.number, on_time, off_time,
                                               pulse_settings.duration, True)
        else:
            self.platform.run_proc_cmd_no_wait("driver_pulse", self.number, pulse_settings.duration)

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and enable the coil for an explicit duration."""
        raise NotImplementedError

    def state(self):
        """Return a dictionary representing this driver's current configuration state."""
        return {
            'driverNum': self.number,
            'outputDriveTime': 0,
            'polarity': self.polarity,
            'state': False,
            'waitForFirstTimeSlot': False,
            'timeslots': 0,
            'patterOnTime': 0,
            'patterOffTime': 0,
            'patterEnable': False,
            'futureEnable': False
        }

    @property
    def has_rules(self):
        """Return true as we support hardware rules."""
        return True


class PROCMatrixLight(LightPlatformSoftwareFade):

    """A P-ROC matrix light device."""

    __slots__ = ["log", "proc", "platform"]

    def __init__(self, number, machine, platform):
        """initialize matrix light device."""
        super().__init__(number, machine.clock.loop,
                         int(1 / machine.config['mpf']['default_light_hw_update_hz'] * 1000))
        self.log = logging.getLogger('PROCMatrixLight {}'.format(number))
        self.platform = platform

    def set_brightness(self, brightness: float):
        """Enable (turns on) this driver."""
        if brightness >= 1:
            self.platform.run_proc_cmd_no_wait("driver_schedule", self.number, 0xffffffff, 0, True)
        elif brightness > 0:
            pwm_on_ms, pwm_off_ms = Util.power_to_on_off(brightness)
            self.platform.run_proc_cmd_no_wait("driver_patter", self.number, pwm_on_ms, pwm_off_ms, 0, True)
        else:
            self.platform.run_proc_cmd_no_wait("driver_disable", self.number)

    def get_board_name(self):
        """Return board of the light."""
        return "P-Roc Matrix"

    def is_successor_of(self, other):
        """Return true if the other light has the previous number."""
        return self.number == other.number + 1

    def get_successor_number(self):
        """Return next number."""
        return self.number + 1

    def __lt__(self, other):
        """Order lights by hardware number."""
        return self.number < other.number


class PDBSwitch:

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


class PDBCoil:

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
        if self.coil_type == 'pdb':
            return self.boardnum * 2 + self.banknum

        return -1

    def bank_secondary(self) -> Optional[int]:
        """Return the other bank if this is a PDB board."""
        if self.coil_type == 'pdb':
            if self.banknum == 0:
                return self.boardnum * 2 + 1

            return self.boardnum * 2

        return None

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


class PDBLight:

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
    def split_matrix_addr_parts(cls, string) -> Tuple[str, str]:
        """Split the string of a matrix lamp address.

        Input is of form C-Ax-By-z:R-Ax-By-z  or  C-x/y/z:R-x/y/z  or
        aliasX:aliasY.  We want to return only the address part: Ax-By-z,
        x/y/z, or aliasX.  That is, remove the two character prefix if present.
        """
        addrs = string.rsplit(':')
        if len(addrs) != 2:
            raise AssertionError("Cannot split address {}. "
                                 "Expected form C-Ax-By-z:R-Ax-By-z or C-x/y/z:R-x/y/z".format(string))
        addrs_out = []
        for addr in addrs:
            bits = addr.split('-')
            if len(bits) == 1:
                addrs_out.append(addr)  # Append unchanged.
            else:  # Generally this will be len(bits) 2 or 4.
                # Remove the first bit and rejoin.
                addrs_out.append('-'.join(bits[1:]))
        assert len(addrs_out) == 2
        return addrs_out[0], addrs_out[1]

    def is_pdb_lamp(self, string):
        """Return true if it looks like a pdb lamp string."""
        params = self.split_matrix_addr_parts(string)
        if len(params) != 2:
            return False
        for addr in params:
            if not self.pdb.is_pdb_address(addr):
                return False
        return True


class PDBLED(PlatformBatchLight):

    """Represents an RGB LED connected to a PD-LED board."""

    __slots__ = ["board", "address", "debug", "log", "polarity", "platform"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, board, address, polarity, debug, driver_platform, light_system):
        """initialize PDB LED."""
        self.board = board
        self.address = address
        self.debug = debug
        self.platform = driver_platform     # type: PROCBasePlatform
        super().__init__("{}-{}".format(self.board, self.address), light_system)
        self.log = logging.getLogger('PDBLED')
        self.polarity = polarity

        self.log.debug("Creating PD-LED item: board: %s, "
                       "RGB output: %s", self.board, self.address)

    def _normalise_color(self, value: int) -> int:
        if self.polarity:
            return 255 - value

        return value

    def get_max_fade_ms(self):
        """Return max fade ms."""
        return 4294967296

    def get_board_name(self):
        """Return board of the light."""
        return "PD-LED Board {}".format(self.board)

    def is_successor_of(self, other):
        """Return true if the other light has the previous address and is on the same board."""
        return self.board == other.board and self.address == other.address + 1

    def get_successor_number(self):
        """Return address on the same board."""
        return "{}-{}".format(self.board, self.address + 1)

    def __lt__(self, other):
        """Order lights by their position on the hardware."""
        return (self.board, self.address) < (other.board, other.address)


class PdLedServo(ServoPlatformInterface):

    """A servo on a PD-LED board."""

    __slots__ = ["board", "number", "debug", "log", "platform", "min_servo_value"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, board, number, platform, debug, min_servo_value):
        """initialize PDB LED."""
        self.board = int(board)
        self.number = int(number)
        self.debug = debug
        self.log = logging.getLogger('PD-LED.Servo.{}-{}'.format(board, number))
        self.platform = platform    # type: PROCBasePlatform
        self.min_servo_value = min_servo_value

    def go_to_position(self, position):
        """Move servo to a certain position."""
        value = int(position * (255 - self.min_servo_value)) + self.min_servo_value
        if self.debug:
            self.log.debug("Setting servo to position: %s value: %s", position, value)

        self.platform.write_pdled_color(self.board, 72 + self.number, value)

    def stop(self):
        """Disable output."""
        self.platform.write_pdled_color(self.board, 72 + self.number, 0)


class PdLedStepper(StepperPlatformInterface):

    """A stepper on a PD-LED board."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, board, number, platform, debug, stepper_ticks_per_half_period):
        """initialize PDB LED."""
        self.board = int(board)
        self.number = int(number)
        self.debug = debug
        self.log = logging.getLogger('PD-LED.Stepper.{}-{}'.format(board, number))
        self.platform = platform
        self._move_complete = asyncio.Event()
        self._move_complete.set()
        self._move_timer = None
        self.stepper_ticks_per_half_period = stepper_ticks_per_half_period

    def move_vel_mode(self, velocity):
        """Turn stepper on at a certain speed."""
        if velocity == 0:
            self.stop()
        elif velocity > 0:
            self.move_rel_pos(16384)
        else:
            self.move_rel_pos(-16384)

    def move_rel_pos(self, position):
        """Move stepper by x steps."""
        if abs(position) > 16384:
            raise ValueError("Cannot move more than 16384 steps but tried {}".format(position))

        if position > 0:
            value = int(position)
        else:
            value = int(abs(position)) + (1 << 15)
        self.platform.write_pdled_config_reg(self.board, self.number + 23, value)

        self._move_complete.clear()
        # we need to time the steps and add 30ms for usb latency/jitter
        wait_time = ((int(abs(position)) * 2 * self.stepper_ticks_per_half_period) / 32000000) + 0.03
        self._move_timer = asyncio.sleep(wait_time)
        if self.debug:
            self.log.debug("Moving %s ticks. This will take %s", position, wait_time)
        self._move_timer = asyncio.ensure_future(self._move_timer)
        self._move_timer.add_done_callback(self._move_done)

    def _move_done(self, future):
        if self.debug:
            self.log.debug("Move done")
        try:
            future.result()
        except asyncio.CancelledError:
            return

        self._move_complete.set()

    def home(self, direction):
        """Not implemented."""
        del direction
        self.platform.raise_config_error("Use homing_mode switch for steppers on PD-LED.", 2)

    def stop(self):
        """Stop stepper."""
        self.platform.write_pdled_config_reg(self.board, self.number + 23, 0)
        self._move_complete.set()
        if self._move_timer:
            self._move_timer.cancel()

    async def wait_for_move_completed(self):
        """Wait for move complete."""
        return await self._move_complete.wait()
