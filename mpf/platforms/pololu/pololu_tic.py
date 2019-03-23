"""Pololu TIC controller platform."""
import asyncio
import logging

from mpf.exceptions.ConfigFileError import ConfigFileError
from mpf.platforms.pololu.pololu_ticcmd_wrapper import PololuTiccmdWrapper
from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface
from mpf.core.platform import StepperPlatform


class PololuTICHardwarePlatform(StepperPlatform):

    """Supports the Pololu TIC stepper drivers via ticcmd command line."""

    def __init__(self, machine):
        """Initialise TIC platform."""
        super().__init__(machine)
        self.log = logging.getLogger("Pololu TIC")
        self.log.debug("Configuring template hardware interface.")
        self.config = self.machine.config.get('pololu_tic', {})
        self.features['tickless'] = True
        self._steppers = []

    def __repr__(self):
        """Return string representation."""
        return '<Platform.PololuTICHardwarePlatform>'

    @asyncio.coroutine
    def initialize(self):
        """Initialise TIC platform."""
        yield from super().initialize()

        # validate our config (has to be in initialize since config_processor
        # is not read in __init__)
        self.config = self.machine.config_validator.validate_config("pololu_tic", self.config)

    def stop(self):
        """De-energize the stepper and stop sending the command timeout refresh."""
        for stepper in self._steppers:
            stepper.shutdown()
        self._steppers = []

    @asyncio.coroutine
    def configure_stepper(self, number: str, config: dict) -> "PololuTICStepper":
        """Configure a smart stepper device in platform.

        Args:
            config (dict): Configuration of device
        """
        stepper = PololuTICStepper(number, config, self.machine)
        self._steppers.append(stepper)
        yield from stepper.initialize()
        return stepper

    @classmethod
    def get_stepper_config_section(cls):
        """Return config validator name."""
        return "tic_stepper_settings"


class PololuTICStepper(StepperPlatformInterface):

    """A stepper on a pololu TIC."""

    def __init__(self, number, config, machine):
        """Initialise stepper."""
        self.config = config
        self.log = logging.getLogger('TIC Stepper')
        self.log.debug("Configuring Stepper Parameters.")
        self.serial_number = number
        self.tic = PololuTiccmdWrapper(self.serial_number, machine, False)
        self.machine = machine
        self._position = None
        self._watchdog_task = None

        if self.config['step_mode'] not in [1, 2, 4, 8, 16, 32]:
            raise ConfigFileError("step_mode must be one of (1, 2, 4, 8, 16, or 32)", 1, self.log.name)

        if self.config['max_speed'] <= 0:
            raise ConfigFileError("max_speed must be greater than 0", 2, self.log.name)

        if self.config['max_speed'] > 500000000:
            raise ConfigFileError("max_speed must be less than or equal to 500,000,000", 3, self.log.name)

    @asyncio.coroutine
    def initialize(self):
        """Configure the stepper."""
        self.log.debug("Looking for TIC Device with serial number %s.", self.serial_number)
        status = yield from self.tic.get_status()

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

        self._watchdog_task = self.machine.clock.schedule_interval(self._reset_command_timeout, .5)

    def _reset_command_timeout(self):
        """Reset the command timeout."""
        self.tic.reset_command_timeout()

    def home(self, direction):
        """Home an axis, resetting 0 position."""
        self.tic.halt_and_hold()    # stop the stepper in case its moving
        self._position = 0
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
        self.tic.rotate_to_position(self._position)

    def move_rel_pos(self, position):
        """Move axis to a relative position."""
        self._position += position
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
            position (number): The position to set
        """
        self.log.debug("Setting Position To %s", position)
        self._position = position
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
        self.tic.halt_and_hold()
        self.tic.stop()

    @asyncio.coroutine
    def wait_for_move_completed(self):
        """Wait until move completed."""
        while not (yield from self.is_move_complete()):
            yield from asyncio.sleep(1 / self.config['poll_ms'], loop=self.machine.clock.loop)

    @asyncio.coroutine
    def is_move_complete(self) -> bool:
        """Return true if move is complete."""
        status = yield from self.tic.get_status()
        current_position = status['Current position']
        self.log.debug("Target Position: %s Current Position: %s", self._position, current_position)
        return bool(self._position == current_position)
