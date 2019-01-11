import ruamel.yaml as yaml
import subprocess
import logging
import asyncio
from threading import Timer, Thread, Event

class TICError(Exception):
    pass

class PololuTICDevice(object):

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
        #this is my cheat to control threading, because self._commandrunning appears to
        #be shared memory between the threads, I can use it to prevent collisions with
        #ticcmd but potentially risk deadlock.  if someone knows a more proper way to do
        #this in python, feel free
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
            self.log.debug("Exception: " + str(e.output))
            raise TICError(e.output)

    def currentstatus(self, refresh=True):
        if refresh:
            self._getstatus()
        return self._status

    def _getstatus(self):
        cmd_return = self._ticcmd('-s', '--full')
        self._status = yaml.load(cmd_return)
        self.currentposition = self._status['Current position']

    def haltandhold(self):
        self._ticcmd('--halt-and-hold')

    def haltandsetposition(self, position):
        self._ticcmd('--halt-and-set-position', str(position))

    def rotate_to_position(self, position):
        self.targetposition = position
        self._ticcmd('--position', str(position))

    def rotate_by_velocity(self, velocity):
        self._ticcmd('--velocity', str(velocity))

    def reset_command_timeout(self):
        self._ticcmd('--reset-command-timeout')

    def exit_safe_start(self):
        self._ticcmd('--exit-safe-start')

    def set_step_mode(self, mode):
        self._ticcmd('--step-mode', str(mode))

    def set_max_speed(self, speed):
        self._ticcmd('--max-speed', str(speed))

    def set_starting_speed(self, speed):
        self._ticcmd('--starting-speed', str(speed))

    def set_max_acceleration(self, acceleration):
        self._ticcmd('--max-accel', str(acceleration))

    def set_max_deceleration(self, deceleration):
        self._ticcmd('--max-decel', str(deceleration))

    def set_current_limit(self, current):
        self._ticcmd('--current', str(current))

    def energize(self):
        self._ticcmd('--energize')
