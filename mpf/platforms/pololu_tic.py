"""Pololu TIC controller platform."""
import asyncio
import logging
import subprocess

from threading import Timer, Thread, Event

from mpf.platforms.pololu import PololuTIC

from mpf.platforms.pololu.PololuTIC import PololuTICDevice

from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface

from mpf.core.platform import StepperPlatform

from mpf.exceptions.ConfigFileError import ConfigFileError

class PololuTICHardwarePlatform(StepperPlatform):

    """Supports the Pololu TIC stepper drivers via ticcmd command line."""

    def __init__(self, machine):
        """Initialise TIC platform."""
        super().__init__(machine)
        self.log = logging.getLogger("Pololu TIC")
        self.log.debug("Configuring template hardware interface.")
        self.config = self.machine.config['pololu_tic']
        self.platform = None
        self.features['tickless'] = True
        self.TIC = None

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
        #self.TMCL.stop()
    
    def configure_stepper(self, number: str, config: dict) -> "PololuTICStepper":
        """Configure a smart stepper device in platform.

        Args:
            config (dict): Configuration of device
        """
        return PololuTICStepper(number, config, self.TIC, self.machine)

    @classmethod
    def get_stepper_config_section(cls):
        """Return config validator name."""
        return "tic_stepper_settings"


# pylint: disable-msg=too-many-instance-attributes
class PololuTICStepper(StepperPlatformInterface):

    """A stepper on a pololu TIC."""

    def __init__(self, number, config, tic_device, machine):
        """Initialise stepper."""
        self.config = config
        self.log = logging.getLogger('TIC Stepper')
        self.log.debug("Configuring Stepper Parameters.")
        self.serial_number = number
        self.TIC = PololuTICDevice(self.serial_number, machine, False)
        self.max_speed = self.config['max_speed']
        self.starting_speed = self.config['starting_speed']
        self.max_acceleration = self.config['max_acceleration']
        self.max_deceleration = self.config['max_deceleration']
        self.current_limit = self.config['current_limit']
        self.step_mode = self.config['step_mode']
        self.machine = machine
        self.commandTimer = None
        
        if self.config['step_mode'] not in [1, 2, 4, 8, 16, 32]:
            raise ConfigFileError("step_mode must be one of (1, 2, 4, 8, 16, or 32)", 1, self.log.name)

        if self.config['max_speed'] <= 0:
            raise ConfigFileError("max_speed must be greater than 0", 2, self.log.name)

        if self.config['max_speed'] > 500000000:
            raise ConfigFileError("max_speed must be less than or equal to 500,000,000", 3, self.log.name)

        self.log.debug("Looking for TIC Device with serial number " + str(self.serial_number) + ".")
        self.TIC = PololuTICDevice(self.serial_number, False)

        if "Low VIN" in self.TIC.currentstatus(False)['Errors currently stopping the motor']:
            self.log.debug("WARNING: Reporting Low VIN")
        
        self.log.debug("TIC Status: ")
        self.log.debug(self.TIC.currentstatus(True))
        
        #start the thread that continuously resets the command timeout
        self.commandTimer = pololuCommandTimer(0.5, self.resetCommandTimeout)
        self.commandTimer.start()
        
        self.TIC.set_step_mode(self.step_mode)
        self.TIC.set_max_speed(self.max_speed)
        self.TIC.set_starting_speed(self.starting_speed)
        self.TIC.set_max_acceleration(self.max_acceleration)
        self.TIC.set_max_deceleration(self.max_deceleration)
        self.TIC.set_current_limit(self.current_limit)
        
        self.TIC.exit_safe_start()
        self.TIC.energize()

    # Public Stepper Platform Interface
    def resetCommandTimeout(self):
        #self.log.debug("Requested command timeout reset")
        self.TIC.reset_command_timeout()
    
    def home(self, direction):
        """Home an axis, resetting 0 position."""
        self.TIC.haltandhold() #stop the stepper in case its moving
        if direction == 'clockwise':
            self.log.debug("Homing clockwise")
            self.TIC.rotate_to_position(2147483647)
        elif direction == 'counterclockwise':
            self.log.debug("Homing counterclockwise")
            self.TIC.rotate_to_position(-2147483647)

    def move_abs_pos(self, position):
        """Move axis to a certain absolute position."""
        self.log.debug("Moving To Absolute Position: " + str(position))
        self.TIC.rotate_to_position(position)

    def move_rel_pos(self, position):
        """Move axis to a relative position."""
        self.log.debug("Moving To Relative Position: " + str(position))
        _newposition = int(position) - int(self.TIC.currentstatus(True)['Current position'])
        self.TIC.rotate_to_position(_newposition)

    def move_vel_mode(self, velocity):
        """Move at a specific velocity and direction (pos = clockwise, neg = counterclockwise)."""
        if velocity == 0:
            self.log.debug("Stopping Due To Velocity Set To 0")
            self.TIC.haltandhold()     # motor stop
        else:
            calculatedvelocity = velocity * self.config['max_speed']
            self.log.debug("Rotating By Velocity (velocity * max_speed): " + str(calculatedvelocity))
            self.TIC.rotate_by_velocity(calculatedvelocity)

    def set_position(self, position):
        self.log.debug("Setting Position To " + str(position))
        self.TIC.haltandsetposition(position)

    def current_position(self):
        """Return current position."""
        return int(self.log.debug(self.TIC.currentstatus(True)['Current position']))

    def stop(self) -> None:
        """Stop stepper."""
        self.log.debug("Commanded To Stop")
        self.TIC.haltandhold()

    @asyncio.coroutine
    def wait_for_move_completed(self):
        """Wait until move completed."""
        while not self.is_move_complete():
            yield from asyncio.sleep(1 / self.config['poll_ms'], loop=self.machine.clock.loop)

    def is_move_complete(self) -> bool:
        """Return true if move is complete."""
        _currentstatus = self.TIC.currentstatus(True)
        self.log.debug("Target Position: " + str(self.TIC.targetposition) + \
            " Current Position: " + str(self.TIC.currentposition))
        if self.TIC.targetposition == self.TIC.currentposition:
            return True
        else:
            return False

class pololuCommandTimer():

    def __init__(self, t, hFunction):
        self.t = t
        self.hFunction = hFunction
        self.thread = Timer(self.t, self.handle_function)

    def handle_function(self):
        self.hFunction()
        self.thread = Timer(self.t, self.handle_function)
        self.thread.start()

    def start(self):
        self.thread.start()

    def cancel(self):
        self.thread.cancel()

    def is_alive(self):
        return self.is_alive()
