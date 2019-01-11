import subprocess
import logging
import asyncio
from threading import Timer, Thread, Event
import ruamel.yaml as yaml


class TICError(Exception):
    pass


class PololuTICDevice(object):
        """A Pololu TIC Device"""

    def __init__(self, serial_number, machine, debug=True):
        self._debug = debug
        self.log = logging.getLogger('TIC Stepper')
        self._serial_number = serial_number
        self._machine = machine
        self._status = None
        self._commandrunning = False
        self.currentposition = None
        self.targetposition = None
        self._getstatus()

    def _ticcmd(self, *args):
        # this is my cheat to control threading, because self._commandrunning appears to
        # be shared memory between the threads, I can use it to prevent collisions with
        # ticcmd but potentially risk deadlock.  if someone knows a more proper way to do
        # this in python, feel free
        while self._commandrunning:
            asyncio.sleep(0.005)
        self._commandrunning = True
        args = list(args)
        args.append('-d')
        args.append(str(self._serial_number))
        try:
            output = subprocess.check_output(['ticcmd'] + args, stderr=subprocess.STDOUT)
            self._commandrunning = False
            return output
        except subprocess.CalledProcessError as e:
            self.log.debug("Exception: {}".format(str(e.output)))
            raise TICError(e.output)

    def currentstatus(self, refresh=True):
        """Returns the current status of the TIC device.

        Args:
            refresh (boolean): Refresh the cached status by asking the TIC
        """
        if refresh:
            self._getstatus()
        return self._status

    def _getstatus(self):
        cmd_return = self._ticcmd('-s', '--full')
        self._status = yaml.load(cmd_return)
        self.currentposition = self._status['Current position']

    def haltandhold(self):
        """Stops the motor abruptly without respecting the deceleration limit."""
        self._ticcmd('--halt-and-hold')

    def haltandsetposition(self, position):
        """Stops the motor abruptly without respecting the deceleration limit and sets the current position."""
        self._ticcmd('--halt-and-set-position', str(position))

    def rotate_to_position(self, position):
        """Tells the TIC to move the stepper to the target position

        Args:
            position (number): The desired position in microsteps
        """
        self.targetposition = position
        self._ticcmd('--position', str(position))

    def rotate_by_velocity(self, velocity):
        """Tells the TIC to move the stepper continuously at the specified velocity

        Args:
            velocity (number): The desired speed in microsteps per 10,000 s
        """
        self._ticcmd('--velocity', str(velocity))

    def reset_command_timeout(self):
        """Tells the TIC to reset the internal command timeout."""
        self._ticcmd('--reset-command-timeout')

    def exit_safe_start(self):
        """Tells the TIC to exit the safe start mode."""
        self._ticcmd('--exit-safe-start')

    def set_step_mode(self, mode):
        """Sets the Step Mode of the stepper

        Args:
            mode (number): One of 1, 2, 4, 8, 16, 32, the number of microsteps per step
        """
        self._ticcmd('--step-mode', str(mode))

    def set_max_speed(self, speed):
        """Sets the max speed of the stepper

        Args:
            speed (number): The maximum speed of the stepper in microsteps per 10,000s
        """
        self._ticcmd('--max-speed', str(speed))

    def set_starting_speed(self, speed):
        """Sets the starting speed of the stepper

        Args:
            speed (number): The starting speed of the stepper in microsteps per 10,000s
        """
        self._ticcmd('--starting-speed', str(speed))

    def set_max_acceleration(self, acceleration):
        """Sets the max acceleration of the stepper

        Args:
            acceleration (number): The maximum acceleration of the stepper in microsteps per 100 s^2
        """
        self._ticcmd('--max-accel', str(acceleration))

    def set_max_deceleration(self, deceleration):
        """Sets the max deceleration of the stepper

        Args:
            deceleration (number): The maximum deceleration of the stepper in microsteps per 100 s^2
        """
        self._ticcmd('--max-decel', str(deceleration))

    def set_current_limit(self, current):
        """Sets the max current of the stepper driver

        Args:
            current (number): The maximum current of the stepper in milliamps
        """
        self._ticcmd('--current', str(current))

    def energize(self):
        """Energizes the Stepper"""
        self._ticcmd('--energize')
