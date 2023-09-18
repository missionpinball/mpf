"""Pololu TIC controller platform."""
import asyncio
import logging
from typing import Dict, List

from mpf.core.utility_functions import Util
from mpf.core.machine import MachineController
from mpf.core.platform import SwitchConfig
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.platforms.pololu.pololu_ticcmd_wrapper import PololuTiccmdWrapper
from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface
from mpf.core.platform import StepperPlatform, SwitchPlatform
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface


class PololuTICHardwarePlatform(StepperPlatform, SwitchPlatform):

    """Supports the Pololu TIC stepper drivers via ticcmd command line."""

    def __init__(self, machine):
        """initialize TIC platform."""
        super().__init__(machine)
        self.config = self.machine.config_validator.validate_config("pololu_tic",
                                                                    self.machine.config.get('pololu_tic', {}))
        self._configure_device_logging_and_debug("Pololu TIC", self.config)
        self.features['tickless'] = True
        self._steppers = []                 # type: List[PololuTICStepper]

    def __repr__(self):
        """Return string representation."""
        return '<Platform.PololuTICHardwarePlatform>'

    def stop(self):
        """De-energize the stepper and stop sending the command timeout refresh."""
        for stepper in self._steppers:
            stepper.shutdown()
        self._steppers = []

    async def configure_stepper(self, number: str, config: dict) -> "PololuTICStepper":
        """Configure a smart stepper device in platform.

        Args:
        ----
            number: Number of this stepper.
            config (dict): Configuration of device
        """
        stepper = PololuTICStepper(number, config, self)
        self._steppers.append(stepper)
        await stepper.initialize()
        return stepper

    @classmethod
    def get_stepper_config_section(cls):
        """Return config validator name."""
        return "tic_stepper_settings"

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> "PololuTicSwitch":
        """Configure switch on controller."""
        return PololuTicSwitch(config, number, self)

    async def get_hw_switch_states(self) -> Dict[str, bool]:
        """Return initial switch state."""
        switches = {}
        for stepper in self._steppers:
            status = await stepper.tic.get_status()
            switches.update(stepper.get_switch_state(status))

        return switches


class PololuTicSwitch(SwitchPlatformInterface):

    """A switch on a Pololu TIC."""

    def __init__(self, config, name, platform):
        """Configure switch."""
        super().__init__(config, name, platform)
        self.board, self.pin = name.split("-", 2)

    def get_board_name(self):
        """Return board name."""
        return self.board


class PololuTICStepper(StepperPlatformInterface):

    """A stepper on a Pololu TIC."""

    def __init__(self, number, config, platform):
        """initialize stepper."""
        self.config = config
        self.log = logging.getLogger('TIC Stepper')
        self.log.debug("Configuring Stepper Parameters.")
        self.serial_number = number
        self.tic = PololuTiccmdWrapper(self.serial_number, platform.machine, False)
        self.machine = platform.machine          # type: MachineController
        self.platform = platform
        self._position = None
        self._watchdog_task = None
        self._poll_task = None
        self._move_complete = asyncio.Event()
        self._switch_state = {}

        if self.config['step_mode'] not in [1, 2, 4, 8, 16, 32]:
            raise ConfigFileError("step_mode must be one of (1, 2, 4, 8, 16, or 32)", 1, self.log.name)

        if self.config['max_speed'] <= 0:
            raise ConfigFileError("max_speed must be greater than 0", 2, self.log.name)

        if self.config['max_speed'] > 500000000:
            raise ConfigFileError("max_speed must be less than or equal to 500,000,000", 3, self.log.name)

    async def initialize(self):
        """Configure the stepper."""
        self.log.debug("Looking for TIC Device with serial number %s.", self.serial_number)
        status = await self.tic.get_status()

        if "Low VIN" in status['Errors currently stopping the motor']:
            self.log.debug("WARNING: Reporting Low VIN")

        self._position = status['Current position']

        self.log.debug("TIC Status: ")
        self.log.debug(status)

        self.tic.set_step_mode(self.config['step_mode'])
        self.tic.set_max_speed(self.config['max_speed'])
        self.tic.set_starting_speed(self.config['starting_speed'])
        self.tic.set_max_acceleration(self.config['max_acceleration'])
        self.tic.set_max_deceleration(self.config['max_deceleration'])
        self.tic.set_current_limit(self.config['current_limit'])

        self.tic.exit_safe_start()
        self.tic.energize()

        self._switch_state = self.get_switch_state(status)

        self._watchdog_task = self.machine.clock.schedule_interval(self._reset_command_timeout, .5)
        self._poll_task = asyncio.create_task(self._poll_status(1 / self.config['poll_ms']))
        self._poll_task.add_done_callback(Util.raise_exceptions)

    async def _poll_status(self, wait_time):
        while True:
            await asyncio.sleep(wait_time)
            status = await self.tic.get_status()
            current_position = status['Current position']
            if self._position != current_position:
                self.log.debug("Target Position: %s Current Position: %s", self._position, current_position)
            elif not self._move_complete.is_set():
                self._move_complete.set()

            switch_state = self.get_switch_state(status)
            if switch_state != self._switch_state:
                for switch, state in switch_state.items():
                    if state != self._switch_state[switch]:
                        self.machine.switch_controller.process_switch_by_num(num=switch, state=state,
                                                                             platform=self.platform)
                self._switch_state = switch_state

    def get_switch_state(self, status):
        """Return switch status based on status info."""
        switches = {"{}-SCL".format(self.serial_number): not bool(status['SCL pin']['Digital reading']),
                    "{}-SDA".format(self.serial_number): not bool(status['SDA pin']['Digital reading']),
                    "{}-TX".format(self.serial_number): not bool(status['TX pin']['Digital reading']),
                    "{}-RX".format(self.serial_number): not bool(status['RX pin']['Digital reading']),
                    "{}-RC".format(self.serial_number): not bool(status['RC pin']['Digital reading'])}
        return switches

    def _reset_command_timeout(self):
        """Reset the command timeout."""
        self.tic.reset_command_timeout()

    def home(self, direction):
        """Home an axis, resetting 0 position."""
        self.tic.halt_and_hold()    # stop the stepper in case its moving
        self._position = 0
        self._move_complete.clear()
        if direction == 'clockwise':
            self.log.debug("Homing clockwise")
            self.tic.go_home(True)
        elif direction == 'counterclockwise':
            self.log.debug("Homing counterclockwise")
            self.tic.go_home(False)

    def move_abs_pos(self, position):
        """Move axis to a certain absolute position."""
        self.log.debug("Moving To Absolute Position: %s", position)
        self._position = position
        self._move_complete.clear()
        self.tic.rotate_to_position(self._position)

    def move_rel_pos(self, position):
        """Move axis to a relative position."""
        self._position += position
        self._move_complete.clear()
        self.log.debug("Moving To Relative Position: %s (Absolute: %s)", position, self._position)
        self.tic.rotate_to_position(self._position)

    def move_vel_mode(self, velocity):
        """Move at a specific velocity and direction (pos = clockwise, neg = counterclockwise)."""
        if velocity == 0:
            self.log.debug("Stopping Due To Velocity Set To 0")
            self.tic.halt_and_hold()     # motor stop
        else:
            calculated_velocity = velocity * self.config['max_speed']
            self.log.debug("Rotating By Velocity (velocity * max_speed): %s", calculated_velocity)
            self.tic.rotate_by_velocity(calculated_velocity)

    def set_home_position(self):
        """Set position to home."""
        self.set_position(0)

    def set_position(self, position):
        """Set the current position of the stepper.

        Args:
        ----
            position (number): The position to set
        """
        self.log.debug("Setting Position To %s", position)
        self._position = position
        self._move_complete.set()
        self.tic.halt_and_set_position(position)

    def stop(self) -> None:
        """Stop stepper."""
        self.log.debug("Commanded To Stop")
        self.tic.halt_and_hold()

    def shutdown(self):
        """Shutdown stepper."""
        if self._watchdog_task:
            self._watchdog_task.cancel()
            self._watchdog_task = None
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None
        self.tic.halt_and_hold()
        self.tic.deengerize()
        self.tic.stop()

    async def wait_for_move_completed(self):
        """Wait until move completed."""
        return await self._move_complete.wait()
