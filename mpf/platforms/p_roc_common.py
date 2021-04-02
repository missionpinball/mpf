# pylint: disable-msg=too-many-lines
"""Common code for P-Roc and P3-Roc."""
import abc
import asyncio
import logging
from logging import Logger

import sys
from threading import Thread

import time
from typing import List, Union, Tuple, Optional, Set

from mpf._version import log_url
from mpf.core.utility_functions import Util
from mpf.core.platform_batch_light_system import PlatformBatchLightSystem
from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface

from mpf.platforms.p_roc_devices import PROCSwitch, PROCMatrixLight, PDBLED, PDBLight, PDBCoil, PDBSwitch, PdLedServo, \
    PdLedStepper

from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.core.platform import SwitchPlatform, DriverPlatform, LightsPlatform, SwitchSettings, DriverSettings, \
    SwitchConfig, ServoPlatform, StepperPlatform, RepulseSettings

from mpf.exceptions.runtime_error import MpfRuntimeError


# pylint: disable-msg=ungrouped-imports
try:    # pragma: no cover
    import pinproc
    PINPROC_IMPORTED = True
    IMPORT_ERROR = None
except ImportError:     # pragma: no cover
    try:
        if sys.platform == 'darwin':
            from mpf.platforms.pinproc.osx import pinproc
        elif sys.platform == 'win32':
            from mpf.platforms.pinproc.windows import pinproc
        else:
            raise ImportError

        PINPROC_IMPORTED = True
        IMPORT_ERROR = None

    except ImportError as e:
        PINPROC_IMPORTED = False
        pinproc = None
        IMPORT_ERROR = e


class ProcProcess:

    """External pinproc process."""

    def __init__(self):
        """Initialise process."""
        self.proc = None
        self.dmd = None
        self.loop = None
        self.stop_future = None
        self.trace = None
        self.log = None

    def start_pinproc(self, machine_type, loop, trace, log):
        """Initialise libpinproc."""
        self.loop = loop
        asyncio.set_event_loop(loop)
        self.stop_future = asyncio.Future()
        self.trace = trace
        assert log is not None
        self.log = log  # type: Logger
        while not self.proc:
            try:
                self.proc = pinproc.PinPROC(machine_type)
            except IOError as e:     # pragma: no cover
                self.log.warning("Failed to instantiate pinproc.PinPROC(%s): %s. Is your P/P3-Roc connected "
                                 "and powered up?", machine_type, e)
                self.log.info("Will retry creating PinPROC in 1s.")
                time.sleep(1)
                continue

            try:
                self.proc.reset(1)
            except IOError as e:  # pragma: no cover
                self.log.warning("Failed to reset P/P3-Roc: %s. Is your P/P3-Roc connected and powered up?", e)
                self.log.info("Will retry creating PinPROC and resetting it in 1s.")
                time.sleep(1)
                continue

    def start_proc_process(self, machine_type, loop, trace, log):
        """Run the pinproc communication."""
        asyncio.set_event_loop(loop)
        self.start_pinproc(machine_type, loop, trace, log)

        loop.run_until_complete(self.stop_future)
        loop.close()

    def stop(self):
        """Stop thread."""
        self.stop_future.set_result(True)

    @staticmethod
    def _sync(num):
        return "sync", num

    def _write_data_batch(self, data):
        for cmd in data:
            self.proc.write_data(*cmd)
        self.proc.flush()
        if self.trace:
            self.log.debug("pinproc.PinPROC.write_data(%s)", data)
            self.log.debug("pinproc.PinPROC.flush()")

    async def run_command(self, cmd, *args):
        """Run command in proc thread."""
        try:
            if cmd.startswith("_"):
                return getattr(self, cmd)(*args)

            if self.trace:
                assert self.log is not None
                result = getattr(self.proc, cmd)(*args)
                self.log.debug("pinproc.PinPROC.%s%s -> %s", cmd, args, result)
                return result

            return getattr(self.proc, cmd)(*args)
        except IOError as error:  # pragma: no cover
            raise MpfRuntimeError("Communication with P/P3-Roc broke down. Check USB cable and power supply.", 2,
                                  self.log.name) from error

    def _dmd_send(self, data):
        if not self.dmd:
            # size is hardcoded here since 128x32 is all the P-ROC hw supports
            self.dmd = pinproc.DMDBuffer(128, 32)

        self.dmd.set_data(data)
        self.proc.dmd_draw(self.dmd)

    async def read_events_and_watchdog(self, poll_sleep):
        """Return all events and tickle watchdog."""
        try:
            while not self.stop_future.done():
                events = self.proc.get_events()
                self.proc.watchdog_tickle()
                self.proc.flush()
                if events:
                    return list(events)

                await asyncio.sleep(poll_sleep)

            return []
        except IOError as error:  # pragma: no cover
            raise MpfRuntimeError("Communication with P/P3-Roc broke down. Check USB cable and power supply.", 2,
                                  self.log.name) from error


# pylint does not understand that this class is abstract
# pylint: disable-msg=abstract-method
# pylint: disable-msg=too-many-instance-attributes
class PROCBasePlatform(LightsPlatform, SwitchPlatform, DriverPlatform, ServoPlatform, StepperPlatform,
                       metaclass=abc.ABCMeta):

    """Platform class for the P-Roc and P3-ROC hardware controller.

    Args:
    ----
        machine: The MachineController instance.
    """

    __slots__ = ["pdbconfig", "pinproc", "proc", "log", "hw_switch_rules", "version", "revision", "hardware_version",
                 "dipswitches", "machine_type", "event_task", "_late_init_futures",
                 "proc_thread", "proc_process", "proc_process_instance", "_commands_running", "config", "_light_system"]

    def __init__(self, machine):
        """Make sure pinproc was loaded."""
        super().__init__(machine)

        if not PINPROC_IMPORTED:
            raise MpfRuntimeError('Could not import "pinproc". Either the library is not installed or is missing '
                                  'some of its dependencies. Check the install instructions for your OS in '
                                  'Multimorphic section of the MPF docs. You can run mpf with "-X" to use virtual '
                                  'hardware in the meantime.', 3, 'P-Roc') from IMPORT_ERROR

        self.pdbconfig = None
        self.pinproc = pinproc
        self.log = None
        self.hw_switch_rules = {}
        self.version = None
        self.revision = None
        self.hardware_version = None
        self.dipswitches = None
        self.event_task = None
        self.proc_thread = None
        self.proc_process = None
        self.proc_process_instance = None
        self._commands_running = 0
        self.config = {}
        self._light_system = None
        self.machine_type = None
        self._late_init_futures = []

    def _decrement_running_commands(self, future):
        del future
        self._commands_running -= 1

    def run_proc_cmd(self, cmd, *args):
        """Run a command in the p-roc thread and return a future."""
        if self.debug:
            self.debug_log("Calling P-Roc cmd: %s (%s)", cmd, args)
        future = asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(self.proc_process.run_command(cmd, *args), self.proc_process_instance))
        future.add_done_callback(Util.raise_exceptions)
        return future

    def run_proc_cmd_no_wait(self, cmd, *args):
        """Run a command in the p-roc thread."""
        if self.debug:
            self.debug_log("Calling P-Roc cmd (no wait): %s (%s)", cmd, args)
        asyncio.run_coroutine_threadsafe(self.proc_process.run_command(cmd, *args), self.proc_process_instance)

    def run_proc_cmd_sync(self, cmd, *args):
        """Run a command in the p-roc thread and return the result."""
        return self.machine.clock.loop.run_until_complete(self.run_proc_cmd(cmd, *args))

    async def initialize(self):
        """Set machine vars."""
        await super().initialize()
        await self.connect()
        self.machine.variables.set_machine_var("p_roc_version", self.version)
        '''machine_var: p_roc_version

        desc: Holds the firmware version number of the P-ROC or P3-ROC controller that's
        attached to MPF.
        '''

        self.machine.variables.set_machine_var("p_roc_revision", self.revision)
        '''machine_var: p_roc_revision

        desc: Holds the firmware revision number of the P-ROC or P3-ROC controller
        that's attached to MPF.
        '''

        self.machine.variables.set_machine_var("p_roc_hardware_version", self.hardware_version)
        '''machine_var: p_roc_hardware_version

        desc: Holds the hardware version number of the P-ROC or P3-ROC controller
        that's attached to MPF.
        '''

        self._light_system = PlatformBatchLightSystem(self.machine.clock, self._send_multiple_light_update,
                                                      self.machine.config['mpf']['default_light_hw_update_hz'],
                                                      65535)

    async def _send_multiple_light_update(self, sequential_brightness_list: List[Tuple[PDBLED, float, int]]):
        """Update a list of light at once."""
        first_light, _, common_fade_ms = sequential_brightness_list[0]
        board = first_light.board
        command_buffer = []     # type: List[Tuple[int, int, int]]
        if common_fade_ms > 0:
            # set the fade time
            self._write_fade_time_buffered(board, int(common_fade_ms / 4), command_buffer)

        # set address of first board
        self._write_addr_buffered(board, first_light.address, command_buffer)

        if self.debug:
            self.debug_log("Fading %s lights with %s fade_ms ",
                           len(sequential_brightness_list), common_fade_ms)

        for light, brightness, fade_ms in sequential_brightness_list:
            if light.polarity:
                value = 255 - int(brightness * 255)
            else:
                value = int(brightness * 255)

            if self.debug:
                self.debug_log("Setting color %s with fade_ms %s to %s-%s",
                               value, fade_ms, light.board, light.address)
            if common_fade_ms > 0:
                self._write_fade_color_buffered(board, value, command_buffer)
            else:
                self._write_color_buffered(board, value, command_buffer)

        self.run_proc_cmd_no_wait("_write_data_batch", command_buffer)

    async def start(self):
        """Start listening for switches."""
        if self._late_init_futures:
            await asyncio.wait(self._late_init_futures)

        self.event_task = self.machine.clock.loop.create_task(self._poll_events())
        self.event_task.add_done_callback(Util.raise_exceptions)
        self._light_system.start()

    def process_events(self, events):
        """Process events from the P-Roc."""
        raise NotImplementedError()

    async def _poll_events(self):
        poll_sleep = 1 / self.machine.config['mpf']['default_platform_hz']
        while True:
            events = await asyncio.wrap_future(
                asyncio.run_coroutine_threadsafe(self.proc_process.read_events_and_watchdog(poll_sleep),
                                                 self.proc_process_instance))
            if events:
                self.process_events(events)

            await asyncio.sleep(poll_sleep)

    def stop(self):
        """Stop proc."""
        if self._light_system:
            self._light_system.stop()
        if self.proc_process and self.proc_process_instance:
            self.proc_process_instance.call_soon_threadsafe(self.proc_process.stop)
        if self.proc_thread:
            self.debug_log("Waiting for pinproc thread.")
            self.proc_thread.join()
            self.proc_thread = None
            self.debug_log("pinproc thread finished.")

    def _start_proc_process(self):
        self.proc_process = ProcProcess()
        if self.config["use_separate_thread"]:
            # Create a new loop
            self.proc_process_instance = asyncio.new_event_loop()
            # Assign the loop to another thread
            self.proc_thread = Thread(target=self.proc_process.start_proc_process,
                                      args=(self.machine_type, self.proc_process_instance,
                                            self.config['trace_bus'] and self.config['debug'],
                                            self.log))
            self.proc_thread.start()

        else:
            # use existing loop
            self.proc_process_instance = self.machine.clock.loop
            self.proc_process.start_pinproc(loop=self.machine.clock.loop, machine_type=self.machine_type,
                                            trace=self.config['trace_bus'] and self.config['debug'],
                                            log=self.log)

    async def connect(self):
        """Connect to the P-ROC.

        Keep trying if it doesn't work the first time.
        """
        self.log.info("Connecting to P-ROC")

        self._start_proc_process()

        version_revision = await self.run_proc_cmd("read_data", 0x00, 0x01)

        self.revision = version_revision & 0xFFFF
        self.version = (version_revision & 0xFFFF0000) >> 16
        dipswitches = await self.run_proc_cmd("read_data", 0x00, 0x03)
        self.hardware_version = (dipswitches & 0xF00) >> 8
        self.dipswitches = ~dipswitches & 0x3F

        self.log.info("Successfully connected to P-ROC/P3-ROC. Firmware Version: %s. Firmware Revision: %s. "
                      "Hardware Board ID: %s",
                      self.version, self.revision, self.hardware_version)

        if self.version < 2 or (self.version == 2 and self.revision < 14):
            self.log.warning("Consider upgrading the firmware of your P/P3-Roc to at least 2.14. "
                             "Your version contains known bugs. See: %s",
                             log_url.format("{}-{}-{}".format("RE", self.log.name, 1)))

        # for unknown reasons we have to postpone this a bit after init
        self.machine.delay.add(100, self._configure_pd_led)

    def _configure_pd_led(self):
        """Configure PD-LEDs."""
        for pd_number, config in self.config['pd_led_boards'].items():
            self._write_ws2811_ctrl(pd_number, config['ws281x_low_bit_time'], config['ws281x_high_bit_time'],
                                    config['ws281x_end_bit_time'], config['ws281x_reset_bit_time'])
            self._write_ws2811_range(pd_number, 0, config['ws281x_0_first_address'], config['ws281x_0_last_address'])
            self._write_ws2811_range(pd_number, 1, config['ws281x_1_first_address'], config['ws281x_1_last_address'])
            self._write_ws2811_range(pd_number, 2, config['ws281x_2_first_address'], config['ws281x_2_last_address'])
            self._write_lpd8806_range(pd_number, 0, config['lpd880x_0_first_address'], config['lpd880x_0_last_address'])
            self._write_lpd8806_range(pd_number, 1, config['lpd880x_1_first_address'], config['lpd880x_1_last_address'])
            self._write_lpd8806_range(pd_number, 2, config['lpd880x_2_first_address'], config['lpd880x_2_last_address'])
            self._write_pdled_serial_control(pd_number, (config['use_ws281x_0'] * 1 << 0) +
                                             (config['use_ws281x_1'] * 1 << 1) +
                                             (config['use_ws281x_2'] * 1 << 2) +
                                             (config['use_lpd880x_0'] * 1 << 3) +
                                             (config['use_lpd880x_1'] * 1 << 4) +
                                             (config['use_lpd880x_2'] * 1 << 5) +
                                             (config['use_stepper_0'] * 1 << 8) +
                                             (config['use_stepper_1'] * 1 << 9))

            # configure servos
            self.write_pdled_config_reg(pd_number, 20, (config['use_servo_0'] * 1 << 0) +
                                        (config['use_servo_1'] * 1 << 1) +
                                        (config['use_servo_2'] * 1 << 2) +
                                        (config['use_servo_3'] * 1 << 3) +
                                        (config['use_servo_4'] * 1 << 4) +
                                        (config['use_servo_5'] * 1 << 5) +
                                        (config['use_servo_6'] * 1 << 6) +
                                        (config['use_servo_7'] * 1 << 7) +
                                        (config['use_servo_8'] * 1 << 8) +
                                        (config['use_servo_9'] * 1 << 9) +
                                        (config['use_servo_10'] * 1 << 10) +
                                        (config['use_servo_11'] * 1 << 11))
            self.write_pdled_config_reg(pd_number, 21, config['max_servo_value'])

            # configure steppers
            if config['use_stepper_0'] or config['use_stepper_1']:
                self.write_pdled_config_reg(pd_number, 22, config['stepper_speed'])

    def write_pdled_config_reg(self, board_addr, addr, reg_data):
        """Write a pdled config register.

        Args:
        ----
            board_addr: Address of the board
            addr: Register address
            reg_data: Register data

        Write the 'regData' into the PD-LEDs address register because when writing a config register
        The data (16 bits) goes into the address field, and the address (8-bits) goes into the data field.
        """
        self._write_addr(board_addr, reg_data)
        self._write_reg_data(board_addr, addr)

    def write_pdled_color(self, board_addr, addr, color):
        """Set a color instantly.

        This command will internally increment the index on the PD-LED board.
        Therefore, it will be much more efficient if you set colors for addresses sequentially.
        """
        command_buffer = []
        self._write_addr_buffered(board_addr, addr, command_buffer)
        self._write_color_buffered(board_addr, color, command_buffer)
        self.run_proc_cmd_no_wait("_write_data_batch", command_buffer)

    def _write_addr(self, board_addr, addr):
        """Write an address to pdled."""
        base_reg_addr = 0x01000000 | (board_addr & 0x3F) << 16
        proc_output_module = 3
        proc_pdb_bus_addr = 0xC00

        # Write the low address bits into reg addr 0
        data = base_reg_addr | (addr & 0xFF)
        self.run_proc_cmd_no_wait("write_data", proc_output_module, proc_pdb_bus_addr, data)

        # Write the high address bits into reg addr 6
        data = base_reg_addr | (6 << 8) | ((addr >> 8) & 0xFF)
        self.run_proc_cmd_no_wait("write_data", proc_output_module, proc_pdb_bus_addr, data)

    def _write_reg_data(self, board_addr, data):
        """Write data to pdled."""
        base_reg_addr = 0x01000000 | (board_addr & 0x3F) << 16
        proc_output_module = 3
        proc_pdb_bus_addr = 0xC00

        # Write 0 into reg addr 7, which is the data word, which is actually the address when
        # writing a config write.  The config register is mapped to 0.
        word = base_reg_addr | (7 << 8) | data
        self.run_proc_cmd_no_wait("write_data", proc_output_module, proc_pdb_bus_addr, word)

    @staticmethod
    def _write_fade_time_buffered(board_addr, fade_time, buffer):
        """Set the fade time for a board."""
        proc_output_module = 3
        proc_pdb_bus_addr = 0xC00
        base_reg_addr = 0x01000000 | (board_addr & 0x3F) << 16
        data = base_reg_addr | (3 << 8) | (fade_time & 0xFF)
        buffer.append((proc_output_module, proc_pdb_bus_addr, data))
        data = base_reg_addr | (4 << 8) | ((fade_time >> 8) & 0xFF)
        buffer.append((proc_output_module, proc_pdb_bus_addr, data))

    @staticmethod
    def _write_addr_buffered(board_addr, addr, buffer):
        """Write an address to pdled."""
        base_reg_addr = 0x01000000 | (board_addr & 0x3F) << 16
        proc_output_module = 3
        proc_pdb_bus_addr = 0xC00

        # Write the low address bits into reg addr 0
        data = base_reg_addr | (addr & 0xFF)
        buffer.append((proc_output_module, proc_pdb_bus_addr, data))

        # Write the high address bits into reg addr 6
        data = base_reg_addr | (6 << 8) | ((addr >> 8) & 0xFF)
        buffer.append((proc_output_module, proc_pdb_bus_addr, data))

    @staticmethod
    def _write_color_buffered(board_addr, color, buffer):
        base_reg_addr = 0x01000000 | (board_addr & 0x3F) << 16
        proc_output_module = 3
        proc_pdb_bus_addr = 0xC00

        data = base_reg_addr | (1 << 8) | (color & 0xFF)
        buffer.append((proc_output_module, proc_pdb_bus_addr, data))

    @staticmethod
    def _write_fade_color_buffered(board_addr, fade_color, buffer):
        """Fade the LED at the current index for a board to a certain color."""
        proc_output_module = 3
        proc_pdb_bus_addr = 0xC00
        base_reg_addr = 0x01000000 | (board_addr & 0x3F) << 16
        data = base_reg_addr | (2 << 8) | (fade_color & 0xFF)
        buffer.append((proc_output_module, proc_pdb_bus_addr, data))

    # pylint: disable-msg=too-many-arguments
    def _write_ws2811_ctrl(self, board_addr, lbt, hbt, ebt, rbt):
        self.write_pdled_config_reg(board_addr, 4, lbt)
        self.write_pdled_config_reg(board_addr, 5, hbt)
        self.write_pdled_config_reg(board_addr, 6, ebt)
        self.write_pdled_config_reg(board_addr, 7, rbt)

    def _write_pdled_serial_control(self, board_addr, index_mask):
        self.write_pdled_config_reg(board_addr, 0, index_mask)

    def _write_ws2811_range(self, board_addr, index, first_addr, last_addr):
        self.write_pdled_config_reg(board_addr, 8 + index * 2, first_addr)
        self.write_pdled_config_reg(board_addr, 9 + index * 2, last_addr)

    def _write_lpd8806_range(self, board_addr, index, first_addr, last_addr):
        self.write_pdled_config_reg(board_addr, 16 + index * 2, first_addr)
        self.write_pdled_config_reg(board_addr, 17 + index * 2, last_addr)

    @classmethod
    def _get_event_type(cls, sw_activity, debounced):
        if sw_activity == 0 and debounced:
            return "open_debounced"
        if sw_activity == 0 and not debounced:
            return "open_nondebounced"
        if sw_activity == 1 and debounced:
            return "closed_debounced"
        # if sw_activity == 1 and not debounced:
        return "closed_nondebounced"

    def _add_hw_rule(self, switch: SwitchSettings, coil: DriverSettings, rule, invert=False):
        rule_type = self._get_event_type(switch.invert == invert, switch.debounce)

        if not switch.hw_switch.has_rules:
            raise AssertionError("Switch {} does not support hardware rules.".format(switch.hw_switch))

        if not coil.hw_driver.has_rules:
            raise AssertionError("Driver {} does not support hardware rules.".format(coil.hw_driver))

        # overwrite rules for the same switch and coil combination
        for rule_num, rule_obj in enumerate(switch.hw_switch.hw_rules[rule_type]):
            if rule_obj[0] == switch.hw_switch.number and rule_obj[1] == coil.hw_driver.number:
                del switch.hw_switch.hw_rules[rule_type][rule_num]

        switch.hw_switch.hw_rules[rule_type].append(
            (switch.hw_switch.number, coil.hw_driver.number, rule)
        )

    def _add_pulse_rule_to_switch(self, switch, coil):
        """Add a rule to pulse a coil on switch hit for a certain duration and optional with PWM."""
        # make sure we never set 0 (due to a bug elsewhere) as this would turn the driver on permanently
        assert coil.pulse_settings.duration != 0

        if coil.pulse_settings.power < 1.0:
            pwm_on, pwm_off = coil.hw_driver.get_pwm_on_off_ms(coil.pulse_settings)
            if self.version < 2 or (self.version == 2 and self.revision < 14):
                raise MpfRuntimeError("Your P/P3-Roc firmware contains a known bug with pulsed_patter hardware rules. "
                                      "Please upgrade the firmware to at least 2.14. "
                                      "As a workaround you might remove pulse_power from "
                                      "coil: {}.".format(coil.hw_driver.number),
                                      1, self.log.name)

            self._add_hw_rule(switch, coil,
                              self.pinproc.driver_state_pulsed_patter(coil.hw_driver.state(), pwm_on, pwm_off,
                                                                      coil.pulse_settings.duration, True))
        else:
            self._add_hw_rule(switch, coil,
                              self.pinproc.driver_state_pulse(coil.hw_driver.state(), coil.pulse_settings.duration))

    def _add_pulse_and_hold_rule_to_switch(self, switch: SwitchSettings, coil: DriverSettings):
        """Add a rule to pulse a coil on switch hit for a certain duration and enable the coil with optional PWM.

        The initial pulse will always be at full power and this method will error out if it is set differently.
        """
        # make sure we never set 0 (due to a bug elsewhere) as this would turn the driver on permanently
        assert coil.pulse_settings.duration != 0

        if coil.pulse_settings.power < 1.0:
            self.raise_config_error("Any rules with hold need to have pulse_power set to 1.0. This is a limitation "
                                    "with the P/P3-Roc.", 6)

        if coil.hold_settings.power < 1.0:
            pwm_on, pwm_off = coil.hw_driver.get_pwm_on_off_ms(coil.hold_settings)
            self._add_hw_rule(switch, coil,
                              self.pinproc.driver_state_patter(
                                  coil.hw_driver.state(), pwm_on, pwm_off, coil.pulse_settings.duration, True))
        else:
            # This method is called in the p-roc thread. we can call hw_driver.state()
            self._add_hw_rule(switch, coil, self.pinproc.driver_state_pulse(coil.hw_driver.state(), 0))

    def _add_release_disable_rule_to_switch(self, switch: SwitchSettings, coil: DriverSettings):
        self._add_hw_rule(switch, coil,
                          self.pinproc.driver_state_disable(coil.hw_driver.state()), invert=True)

    def _add_disable_rule_to_switch(self, switch: SwitchSettings, coil: DriverSettings):
        self._add_hw_rule(switch, coil,
                          self.pinproc.driver_state_disable(coil.hw_driver.state()))

    def _add_hold_rule_to_switch(self, switch: SwitchSettings, coil: DriverSettings):
        if coil.hold_settings.power < 1.0:
            pwm_on, pwm_off = coil.hw_driver.get_pwm_on_off_ms(coil.hold_settings)
            self._add_hw_rule(switch, coil,
                              self.pinproc.driver_state_patter(
                                  coil.hw_driver.state(), pwm_on, pwm_off, 0, True))

    def _write_rules_to_switch(self, switch, coil, drive_now):
        for event_type, driver_rules in switch.hw_switch.hw_rules.items():
            driver = []
            for x in driver_rules:
                driver.append(x[2])
            rule = {'notifyHost': bool(switch.hw_switch.notify_on_nondebounce) == event_type.endswith("nondebounced"),
                    'reloadActive': bool(coil.recycle)}
            if drive_now is None:
                self.run_proc_cmd_no_wait("switch_update_rule", switch.hw_switch.number, event_type, rule, driver)
            else:
                self.run_proc_cmd_no_wait("switch_update_rule", switch.hw_switch.number, event_type, rule, driver,
                                          drive_now)

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

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                      eos_switch: SwitchSettings, coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver."""
        self.debug_log("Setting Pulse on hit and release and disable HW Rule. Enable Switch: %s,"
                       "Disable Switch: %s, Driver: %s", enable_switch.hw_switch.number,
                       eos_switch.hw_switch.number, coil.hw_driver.number)
        self._add_pulse_rule_to_switch(enable_switch, coil)
        self._add_release_disable_rule_to_switch(enable_switch, coil)
        self._add_disable_rule_to_switch(eos_switch, coil)

        self._write_rules_to_switch(enable_switch, coil, False)
        self._write_rules_to_switch(eos_switch, coil, False)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver."""
        self.debug_log("Setting Pulse on hit and enable and release and disable HW Rule. Enable Switch: %s,"
                       "Disable Switch: %s, Driver: %s", enable_switch.hw_switch.number,
                       eos_switch.hw_switch.number, coil.hw_driver.number)
        self._add_pulse_and_hold_rule_to_switch(enable_switch, coil)
        self._add_release_disable_rule_to_switch(enable_switch, coil)
        self._add_hold_rule_to_switch(eos_switch, coil)

        self._write_rules_to_switch(enable_switch, coil, False)
        self._write_rules_to_switch(eos_switch, coil, False)

    def clear_hw_rule(self, switch, coil):
        """Clear a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        Args:
        ----
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
            self.run_proc_cmd_no_wait("driver_disable", coil_number)
            self._write_rules_to_switch(switch, coil, None)

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
        if subtype == "led":
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

        raise AssertionError("Unknown subtype {}".format(subtype))

    def configure_light(self, number, subtype, config, platform_settings) -> LightPlatformInterface:
        """Configure a light channel."""
        if not subtype:
            subtype = self._get_default_subtype()
        if subtype == "matrix":
            if self.machine_type == self.pinproc.MachineTypePDB:
                proc_num = self.pdbconfig.get_proc_light_number(str(number))
                if proc_num == -1:
                    raise AssertionError("Matrixlight {}/{} cannot be controlled by the P-ROC. ".format(
                        config.name, str(number)))

            else:
                proc_num = self.pinproc.decode(self.machine_type, str(number))

            return PROCMatrixLight(proc_num, self.machine, self)
        if subtype == "led":
            board, index = number.split("-")
            polarity = platform_settings and platform_settings.get("polarity", False)
            return PDBLED(int(board), int(index), polarity, self.config.get("debug", False), self, self._light_system)

        raise AssertionError("unknown subtype {}".format(subtype))

    def _configure_switch(self, config: SwitchConfig, proc_num) -> PROCSwitch:
        """Configure a P3-ROC switch.

        Args:
        ----
            config: Dictionary of settings for the switch.
            proc_num: decoded switch number

        Returns a reference to the switch object that was just created.
        """
        if proc_num == -1:
            raise AssertionError("Switch {}/{} cannot be controlled by the "
                                 "P-ROC/P3-ROC.".format(config.name, proc_num))

        switch = PROCSwitch(config, proc_num, config.debounce == "quick", self)
        # The P3-ROC needs to be configured to notify the host computers of
        # switch events. (That notification can be for open or closed,
        # debounced or nondebounced.)
        self.debug_log("Configuring switch's host notification settings. P3-ROC"
                       "number: %s, debounce: %s", proc_num,
                       config.debounce)
        if config.debounce == "quick":
            self.run_proc_cmd_no_wait("switch_update_rule", proc_num, 'closed_nondebounced',
                                      {'notifyHost': True, 'reloadActive': False}, [], False)
            self.run_proc_cmd_no_wait("switch_update_rule", proc_num, 'open_nondebounced',
                                      {'notifyHost': True, 'reloadActive': False}, [], False)
        else:
            self.run_proc_cmd_no_wait("switch_update_rule", proc_num, 'closed_debounced',
                                      {'notifyHost': True, 'reloadActive': False}, [], False)
            self.run_proc_cmd_no_wait("switch_update_rule", proc_num, 'open_debounced',
                                      {'notifyHost': True, 'reloadActive': False}, [], False)
        return switch

    async def configure_servo(self, number: str) -> ServoPlatformInterface:
        """Configure a servo on a PD-LED board.

        Args:
        ----
            number: Number of the servo
        """
        try:
            board, number = number.split("-")
        except ValueError:
            self.raise_config_error("Servo number should be board-number but is {}".format(number), 1)
        if 0 > int(number) >= 12:
            self.raise_config_error("PD-LED only supports 12 servos {}".format(number), 5)

        return PdLedServo(board, number, self, self.config.get("debug", False))

    async def configure_stepper(self, number: str, config: dict) -> PdLedStepper:
        """Configure a stepper (axis) device in platform.

        Args:
        ----
            number: Number of the stepper.
            config: Config for this stepper.
        """
        try:
            board, number = number.split("-")
        except ValueError:
            self.raise_config_error("Stepper number should be board-number but is {}".format(number), 3)
        if 0 > int(number) >= 2:
            self.raise_config_error("PD-LED only supports two steppers {}".format(number), 4)

        pd_led = self.config['pd_led_boards'].get(board, {})
        stepper_speed = pd_led.get("stepper_speed", 13524)

        return PdLedStepper(board, number, self, self.config.get("debug", False), stepper_speed)


class PDBConfig:

    """Handles PDB Config of the P/P3-Roc.

    This class is only used when using the P3-ROC or when the P-ROC is configured to use PDB
    driver boards such as the PD-16 or PD-8x8. i.e. not when it's operating in
    WPC or Stern mode.
    """

    __slots__ = ["log", "platform", "polarity", "lamp_matrix_strobe_time", "watchdog_time", "use_watchdog", "indexes"]

    # pylint: disable-msg=too-many-locals
    def __init__(self, proc_platform, config, driver_count):
        """Set up PDB config.

        Will configure driver groups for matrixes, lamps and normal drivers.
        We always use polarity True in this method because it is only used for PDB machines.
        """
        self.log = logging.getLogger('PDBConfig')
        self.log.debug("Processing PDB Driver Board configuration")

        self.platform = proc_platform

        # Set config defaults
        self.lamp_matrix_strobe_time = config['p_roc']['lamp_matrix_strobe_time']
        self.watchdog_time = config['p_roc']['watchdog_time']
        self.use_watchdog = config['p_roc']['use_watchdog']

        # Initialize some lists for data collecting
        coil_bank_list, unconfigured_coil_bank_list = self._load_coil_bank_list_from_config(config)
        lamp_source_bank_list, lamp_list, lamp_list_for_index = self._load_lamp_lists_from_config(config)

        # Create a list of indexes.  The PDB banks will be mapped into this
        # list. The index of the bank is used to calculate the P-ROC/P3-ROC driver
        # number for each driver.
        num_proc_banks = driver_count // 8
        self.indexes = [{}] * num_proc_banks    # type: List[Union[int, dict]]

        self._initialize_drivers()

        # Set up dedicated driver groups (groups 0-3).
        for group_ctr in range(0, 4):
            # PDB Banks 0-3 are interpreted as dedicated bank here. Therefore, we do not use them.
            enable = group_ctr in coil_bank_list
            self.log.debug("Driver group %02d (dedicated): Enable=%s",
                           group_ctr, enable)
            self.platform.run_proc_cmd_no_wait("driver_update_group_config",
                                               group_ctr,
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
        lamp_banks = set()
        for i, lamp_dict in enumerate(lamp_list):
            # If the bank is 16 or higher, the P-ROC/P3-ROC can't control it
            # directly. Software can't really control lamp matrixes either
            # (need microsecond resolution).  Instead of doing crazy logic here
            # for a case that probably won't happen, just ignore these banks.
            if group_ctr >= num_proc_banks or lamp_dict['sink_bank'] >= 16:
                raise AssertionError("Lamp matrix banks can't be mapped to index "
                                     "{} because that's outside of the banks the "
                                     "P-ROC/P3-ROC can control.".format(lamp_dict['sink_bank']))

            self.log.debug("Driver group %02d (lamp sink): slow_time=%d "
                           "enable_index=%d row_activate_index=%d "
                           "row_enable_index=%d matrix=%s", group_ctr,
                           self.lamp_matrix_strobe_time,
                           lamp_dict['sink_bank'],
                           lamp_dict['source_output'],
                           lamp_dict['source_index'], True)
            self.indexes[group_ctr] = lamp_list_for_index[i]
            lamp_banks.add(lamp_dict['sink_bank'])
            self.platform.run_proc_cmd_no_wait("driver_update_group_config",
                                               group_ctr,
                                               self.lamp_matrix_strobe_time,
                                               lamp_dict['sink_bank'],
                                               lamp_dict['source_output'],
                                               lamp_dict['source_index'],
                                               True,
                                               True,
                                               True,
                                               True)
            group_ctr += 1

        unconfigured_coil_bank_list -= lamp_banks
        unconfigured_coil_bank_list -= set(lamp_source_bank_list)

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
                self.platform.run_proc_cmd_no_wait("driver_update_group_config",
                                                   group_ctr,
                                                   0,
                                                   coil_bank,
                                                   0,
                                                   0,
                                                   False,
                                                   True,
                                                   True,
                                                   True)
                group_ctr += 1

        # configure all unconfigured coil banks but do not enable them
        for coil_bank in unconfigured_coil_bank_list:
            if group_ctr >= num_proc_banks or coil_bank >= 32:
                self.log.warning("Cannot configure %s. The polarity on those banks might be incorrect.", coil_bank)
                continue

            self.log.debug("Driver group %02d: slow_time=%d Enabled "
                           "Index=%d", group_ctr, 0, coil_bank)
            self.platform.run_proc_cmd_no_wait("driver_update_group_config",
                                               group_ctr,
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
            self.platform.run_proc_cmd_no_wait("driver_update_group_config",
                                               i,
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
        self._configure_lamp_banks(lamp_source_bank_list, False)
        self._configure_lamp_banks(lamp_source_bank_list, True)

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

        if '/' in addr:  # x/y/z form
            params = addr.rsplit('/')
            if len(params) != 3:
                raise ValueError('pdb address must have 3 components')
            board = int(params[0])
            bank = int(params[1])
            output = int(params[2])
            return board, bank, output

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
                    # p-roc numbers are requested.  The requester won't know
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

    def _load_coil_bank_list_from_config(self, config) -> Tuple[Set[int], Set[int]]:
        coil_bank_list = set()
        secondary_coil_bank_list = set()

        # Make a list of unique coil banks
        if 'coils' in config:
            for name in config['coils']:
                item_dict = config['coils'][name]
                coil = PDBCoil(self, str(item_dict['number']))
                bank = coil.bank()
                coil_bank_list.add(bank)

                secondary_bank = coil.bank_secondary()
                if secondary_bank is not None:
                    secondary_coil_bank_list.add(secondary_bank)

        secondary_coil_bank_list -= coil_bank_list

        return coil_bank_list, secondary_coil_bank_list

    def _initialize_drivers(self):
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

            self.platform.run_proc_cmd_no_wait("driver_update_state", state)

    def _configure_lamp_banks(self, lamp_source_bank_list, enable):
        self.platform.run_proc_cmd_no_wait("driver_update_global_config",
                                           enable,
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
        ----
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
        ----
            number_str (str): PDB string
        """
        lamp = PDBLight(self, number_str)
        if lamp.lamp_type == 'unknown':
            return -1
        if lamp.lamp_type == 'dedicated':
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
        ----
            number_str (str): PDB string
        """
        switch = PDBSwitch(self, number_str)
        num = switch.proc_num()
        return num
