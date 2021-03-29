"""Trinamics StepRocker controller platform."""
import asyncio
import logging

from mpf.platforms.trinamics import TMCL

from mpf.platforms.trinamics.TMCL import TMCLDevice
from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface

from mpf.core.platform import StepperPlatform


class TrinamicsStepRocker(StepperPlatform):

    """Supports the Trinamics Step Rocker via PySerial.

    Works with Trinamics Step Rocker.  TBD other 'TMCL' based steppers eval boards
    """

    def __init__(self, machine):
        """Initialise Trinamics Step Rocker platform."""
        super().__init__(machine)
        self.log = logging.getLogger("Trinamics StepRocker")
        self.log.debug("Configuring template hardware interface.")
        self.config = self.machine.config['trinamics_steprocker']
        self.platform = None
        self.features['tickless'] = True
        self.tmcl = None

    def __repr__(self):
        """Return string representation."""
        return '<Platform.TrinamicsStepRocker>'

    async def initialize(self):
        """Initialise trinamics steprocker platform."""
        await super().initialize()

        # validate our config (has to be in intialize since config_processor
        # is not read in __init__)
        self.config = self.machine.config_validator.validate_config("trinamics_steprocker", self.config)
        self.tmcl = TMCLDevice(self.config['port'], False)

    def stop(self):
        """Close serial."""
        if self.tmcl:
            self.tmcl.stop()
            self.tmcl = None

    async def configure_stepper(self, number: str, config: dict) -> "TrinamicsTMCLStepper":
        """Configure a smart stepper device in platform.

        Args:
        ----
            number: Number of the stepper.
            config (dict): Configuration of device
        """
        return TrinamicsTMCLStepper(number, config, self.tmcl, self.machine)

    @classmethod
    def get_stepper_config_section(cls):
        """Return config validator name."""
        return "steprocker_stepper_settings"


# pylint: disable-msg=too-many-instance-attributes
class TrinamicsTMCLStepper(StepperPlatformInterface):

    """A stepper on a TMCL based controller such as Trinamics StepRocker."""

    def __init__(self, number, config, tmcl_device, machine):
        """Initialise stepper."""
        self._pulse_div = 5     # tbd add to config
        self._ramp_div = 9      # tbd add to config
        self._clock_freq = 16000000.0
        self.config = config
        self.log = logging.getLogger('TMCL Stepper')
        self._mn = int(number)
        self.tmcl = tmcl_device
        self._move_current = int(2.55 * self.config['move_current'])    # percent to 0...255(100%)
        self._hold_current = int(2.55 * self.config['hold_current'])    # percent to 0...255(100%)
        self._microstep_per_fullstep = self.config['microstep_per_fullstep']
        self._fullstep_per_userunit = self.config['fullstep_per_userunit']
        self._velocity_limit = self._uu_to_velocity_cmd(self.config['velocity_limit'])
        self._acceleration_limit = self._uu_to_accel_cmd(self.config['acceleration_limit'])
        self.machine = machine
        self._homing_speed = self._uu_to_velocity_cmd(self.config['homing_speed'])

        self._set_important_parameters(self._velocity_limit, self._acceleration_limit,
                                       self._move_current, self._hold_current,
                                       self._get_micro_step_mode(self._microstep_per_fullstep), False)
        # apply pulse and ramp divisors as well
        self.tmcl.sap(self._mn, 154, self._pulse_div)
        self.tmcl.sap(self._mn, 153, self._ramp_div)
        self._homing_active = False

    # Public Stepper Platform Interface
    def home(self, direction):
        """Home an axis, resetting 0 position."""
        self.tmcl.rfs(self._mn, 'STOP')  # in case in progress
        self._set_home_parameters(direction)
        self.tmcl.rfs(self._mn, 'START')
        self._homing_active = True

    def set_home_position(self):
        """Tell the stepper that we are at the home position."""
        self.tmcl.sap(self._mn, 1, 0)

    def move_abs_pos(self, position):
        """Move axis to a certain absolute position."""
        microstep_pos = self._uu_to_microsteps(position)
        self.tmcl.mvp(self._mn, "ABS", microstep_pos)

    def move_rel_pos(self, position):
        """Move axis to a relative position."""
        microstep_rel = self._uu_to_microsteps(position)
        self.tmcl.mvp(self._mn, "REL", microstep_rel)

    def move_vel_mode(self, velocity):
        """Move at a specific velocity and direction (pos = clockwise, neg = counterclockwise)."""
        self._rotate(velocity)

    def current_position(self):
        """Return current position."""
        microsteps = self.tmcl.gap(self._mn, 1)
        return self._microsteps_to_uu(microsteps)

    def stop(self) -> None:
        """Stop stepper."""
        self.tmcl.mst(self._mn)

    async def wait_for_move_completed(self):
        """Wait until move completed."""
        while not self.is_move_complete():
            await asyncio.sleep(1 / self.config['poll_ms'])

    def is_move_complete(self) -> bool:
        """Return true if move is complete."""
        if self._homing_active:
            ret = self.tmcl.rfs(self._mn, 'STATUS')
            if ret != 0:  # This is reversed from manual but is how it works
                return False

            self._homing_active = False
            return True

        # check normal move status
        ret = self.tmcl.gap(self._mn, 8)
        if ret == 1:
            return True

        return False

    # Private Utility Functions
    @staticmethod
    def _get_micro_step_mode(microsteps_per_fullstep: int) -> int:
        return int({
            1: 0,
            2: 1,
            4: 2,
            8: 3,
            16: 4,
            32: 5,
            64: 6,
            128: 7,
            256: 8
        }.get(microsteps_per_fullstep, 0))

    def _uu_to_microsteps(self, userunits) -> float:
        return userunits * self._fullstep_per_userunit * self._microstep_per_fullstep

    def _microsteps_to_uu(self, microsteps) -> float:
        return microsteps / (self._fullstep_per_userunit * self._microstep_per_fullstep)

    def _to_velocity_cmd(self, microsteps_per_sec) -> int:
        ret = (microsteps_per_sec * 2 ** self._pulse_div * 2048.0 * 32.0) / self._clock_freq
        if abs(ret) > 2047:
            raise ValueError("Scaled Velocity too high, lower pulse_div")
        if ret < 1:
            raise ValueError("Scaled Velocity too low, raise pulse_div")
        return int(ret)

    def _to_acceleration_cmd(self, microsteps_per_ss) -> int:
        ret = (2 ** (self._pulse_div + self._ramp_div + 29) * microsteps_per_ss) / self._clock_freq ** 2
        if ret > 2047:
            raise ValueError("Acceleration too high, lower ramps_div")
        if ret < 1:
            raise ValueError("Acceleration too low, raise ramps_div")
        return int(ret)

    def _uu_to_velocity_cmd(self, user_unit):
        microsteps_per_sec = user_unit * self._fullstep_per_userunit * self._microstep_per_fullstep
        return self._to_velocity_cmd(microsteps_per_sec)

    def _uu_to_accel_cmd(self, user_unit):
        microsteps_per_sec = user_unit * self._fullstep_per_userunit * self._microstep_per_fullstep
        return self._to_acceleration_cmd(microsteps_per_sec)

    def _get_globals(self):
        ret = {}
        for key, value in TMCL.GLOBAL_PARAMETER.iteritems():
            bank, par, name, _, _ = key + value
            ret[name] = self.tmcl.ggp(bank, par)
        return ret

    def _get_parameters(self):
        retmotor = [{}, {}, {}]
        retsingle = {}
        for mn in range(3):
            for key, value in TMCL.AXIS_PARAMETER.iteritems():
                par, name, _, _ = (key,) + value
                if par not in TMCL.SINGLE_AXIS_PARAMETERS:
                    retmotor[mn][name] = self.tmcl.gap(mn, par)
                elif mn == 0:
                    retsingle[name] = self.tmcl.gap(mn, par)
        return retmotor, retsingle

    # pylint: disable-msg=too-many-arguments
    def _set_important_parameters(self, maxspeed=2000, maxaccel=2000,
                                  maxcurrent=72, standbycurrent=32,
                                  microstep_resolution=1, store=False):
        self.tmcl.sap(self._mn, 140, int(microstep_resolution))
        self.tmcl.sap(self._mn, 4, int(maxspeed))
        self.tmcl.sap(self._mn, 5, int(maxaccel))
        self.tmcl.sap(self._mn, 6, int(maxcurrent))
        self.tmcl.sap(self._mn, 7, int(standbycurrent))
        if not bool(store):
            return
        self.tmcl.stap(self._mn, 140)
        self.tmcl.stap(self._mn, 4)
        self.tmcl.stap(self._mn, 5)
        self.tmcl.stap(self._mn, 6)
        self.tmcl.stap(self._mn, 7)

    def _set_home_parameters(self, direction):
        # self.TMCL.sap(self._mn, 9,  ) #ref. switch status
        # self.TMCL.sap(self._mn, 10, ) #right limit switch status
        # self.TMCL.sap(self._mn, 11, ) #left limit switch status
        # self.TMCL.sap(self._mn, 12, ) #right limit switch disable
        # self.TMCL.sap(self._mn, 13, ) #left limit switch disable
        # self.TMCL.sap(self._mn, 141, ) #ref. switch tolerance
        # self.TMCL.sap(self._mn, 149, ) #soft stop flag
        self.tmcl.sap(self._mn, 194, self._homing_speed)    # referencing search speed
        if direction == 'clockwise':
            self.tmcl.sap(self._mn, 193, 8)     # ref. search mode
        elif direction == 'counterclockwise':
            self.tmcl.sap(self._mn, 193, 7)
        # self.TMCL.sap(self._mn, 195, ) #referencing switch speed
        # self.TMCL.sap(self._mn, 196, ) # distance end switches

    def _rotate(self, velocity):
        if velocity == 0:
            self.tmcl.mst(self._mn)     # motor stop
        if velocity > 0:
            self.tmcl.ror(self._mn, self._uu_to_velocity_cmd(velocity))
        else:
            self.tmcl.rol(self._mn, self._uu_to_velocity_cmd(abs(velocity)))
        return velocity
