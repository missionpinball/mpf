"""Pololu TIC Device."""
import subprocess
import logging
import asyncio
from threading import Thread
import ruamel.yaml


class TicError(Exception):

    """A Pololu TIC Error."""

    pass


class PololuTiccmdWrapper:

    """A Pololu TIC Device."""

    def __init__(self, serial_number, machine, debug=True):
        """Return the current status of the TIC device.

        Args:
            serial_number (number): The serial number of the TIC to control
            machine (object): The machine object
            debug (boolean): Turn on debugging or not
        """
        self._debug = debug
        self.log = logging.getLogger('TIC Stepper')
        self._serial_number = serial_number
        self._machine = machine
        self.loop = None

        self._start_thread()

    def _start_thread(self):
        # Create a new loop
        self.loop = asyncio.new_event_loop()
        self.stop_future = asyncio.Future(loop=self.loop)
        # Assign the loop to another thread
        self.thread = Thread(target=self._run_loop)
        self.thread.start()

    def _run_loop(self):
        """Run the asyncio loop in this thread."""
        self.loop.run_until_complete(self.stop_future)
        self.loop.close()

    @asyncio.coroutine
    def stop_async(self):
        """Stop loop."""
        self.stop_future.set_result(True)

    def stop(self):
        """Stop loop and join thread."""
        asyncio.run_coroutine_threadsafe(self.stop_async(), self.loop)
        self._stop_thread()

    def _stop_thread(self):
        self.thread.join()

    def _ticcmd(self, *args):
        """Run ticcmd in another thread."""
        future = asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(self._ticcmd_async(*args), self.loop),
            loop=self._machine.clock.loop)
        future.add_done_callback(self._done)
        return future

    @staticmethod
    def _done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    @asyncio.coroutine
    def _ticcmd_async(self, *args):
        """Run ticcmd.

        This will block the asyncio loop in the thread so only one command can run at a time.
        However, it will not block MPF because we will call this via run_coroutine_threadsafe from another thread.
        """
        args = list(args)
        args.append('-d')
        args.append(str(self._serial_number))
        try:
            output = subprocess.check_output(['ticcmd'] + args, stderr=subprocess.STDOUT)
            return output
        except subprocess.CalledProcessError as e:
            self.log.debug("Exception: %s", str(e.output))
            raise TicError(e.output)

    @asyncio.coroutine
    def get_status(self):
        """Return the current status of the TIC device."""
        cmd_return = yield from self._ticcmd('-s', '--full')
        status = ruamel.yaml.safe_load(cmd_return)
        return status

    def halt_and_hold(self):
        """Stop the motor abruptly without respecting the deceleration limit."""
        self._ticcmd('--halt-and-hold')

    def halt_and_set_position(self, position):
        """Stop the motor abruptly without respecting the deceleration limit and sets the current position."""
        self._ticcmd('--halt-and-set-position', str(int(position)))

    def rotate_to_position(self, position):
        """Tells the TIC to move the stepper to the target position.

        Args:
            position (number): The desired position in microsteps
        """
        self._ticcmd('--position', str(int(position)))

    def rotate_by_velocity(self, velocity):
        """Tells the TIC to move the stepper continuously at the specified velocity.

        Args:
            velocity (number): The desired speed in microsteps per 10,000 s
        """
        self._ticcmd('--velocity', str(int(velocity)))

    def reset_command_timeout(self):
        """Tells the TIC to reset the internal command timeout."""
        self._ticcmd('--reset-command-timeout')

    def exit_safe_start(self):
        """Tells the TIC to exit the safe start mode."""
        self._ticcmd('--exit-safe-start')

    def set_step_mode(self, mode):
        """Set the Step Mode of the stepper.

        Args:
            mode (number): One of 1, 2, 4, 8, 16, 32, the number of microsteps per step
        """
        self._ticcmd('--step-mode', str(int(mode)))

    def set_max_speed(self, speed):
        """Set the max speed of the stepper.

        Args:
            speed (number): The maximum speed of the stepper in microsteps per 10,000s
        """
        self._ticcmd('--max-speed', str(int(speed)))

    def set_starting_speed(self, speed):
        """Set the starting speed of the stepper.

        Args:
            speed (number): The starting speed of the stepper in microsteps per 10,000s
        """
        self._ticcmd('--starting-speed', str(int(speed)))

    def set_max_acceleration(self, acceleration):
        """Set the max acceleration of the stepper.

        Args:
            acceleration (number): The maximum acceleration of the stepper in microsteps per 100 s^2
        """
        self._ticcmd('--max-accel', str(int(acceleration)))

    def set_max_deceleration(self, deceleration):
        """Set the max deceleration of the stepper.

        Args:
            deceleration (number): The maximum deceleration of the stepper in microsteps per 100 s^2
        """
        self._ticcmd('--max-decel', str(int(deceleration)))

    def set_current_limit(self, current):
        """Set the max current of the stepper driver.

        Args:
            current (number): The maximum current of the stepper in milliamps
        """
        self._ticcmd('--current', str(int(current)))

    def energize(self):
        """Energize the Stepper."""
        self._ticcmd('--energize')

    def go_home(self, forward):
        """Energize the Stepper."""
        if forward:
            direction = "fwd"
        else:
            direction = "rev"
        self._ticcmd('--home {}'.format(direction))
