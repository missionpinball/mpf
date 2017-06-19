
import mpf.platforms.trinamics.TMCL

"""Trinamics StepRocker controller platform."""
import asyncio
import logging
import serial
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

    def __repr__(self):
        """Return string representation."""
        return '<Platform.TrinamicsStepRocker>'

    @asyncio.coroutine
    def initialize(self):
        """Method is called after all hardware platforms were instantiated."""
        yield from super().initialize()

        # validate our config (has to be in intialize since config_processor
        # is not read in __init__)
        self.config = self.machine.config_validator.validate_config("trinamics_steprocker", self.config)
        self.TMCL = TMCLDevice(self.config['port'], False)


    def stop(self):
        """Close serial."""
        self.TMCL.stop()

    def configure_stepper(self, config):
        """Configure a smart stepper device in platform.

        Args:
            config (dict): Configuration of device
        """
        return TrinamicsTMCLStepper( config, self.TMCL )


class TrinamicsTMCLStepper(StepperPlatformInterface):

    """A stepper on a TMCL based controller such as Trinamics StepRocker"""

    def __init__(self, config, TMCLDevice ):
        """Initialise stepper."""
        self.config = config
        self.log = logging.getLogger('TMCL Stepper')
        self._mn = int(self.config['number'])
        self.TMCL = TMCLDevice
        self._move_current = int(2.55 * self.config['move_current']) #percent to 0...255(100%)
        self._hold_current = int(2.55 * self.config['hold_current']) #percent to 0...255(100%)
        self._microstep_per_fullstep = self.config['microstep_per_fullstep']
        self._microstepsPerUserUnit = self.config['microstep_per_userunit']
        self._velocity_limit = self._ToVelocityCmd(self.config['velocity_limit'])
        self._acceleration_limit = self._ToVelocityCmd(self.config['acceleration_limit'])
        self._home_direction = self.config['home_direction']
        self._set_important_parameters(self._velocity_limit, self._acceleration_limit,
                                             self._move_current, self._hold_current, 
                                             self.TMCL.getMicroStepMode(self._microstep_per_fullstep), False)
        

    # Public Stepper Platform Interface
    def home(self):
        """Home an axis, resetting 0 position"""
        raise NotImplementedError()

    def move_abs_pos(self, position):
        """Move axis to a certain absolute position"""
        raise NotImplementedError()

    def move_rel_pos(self, position):
        """Move axis to a relative position"""
        raise NotImplementedError()

    def move_vel_mode(self, velocity):
        """Move at a specific velocity and direction (pos = clockwise, neg = counterclockwise)"""
        self._rotate(self._ToVelocityCmd(velocity))

    def currentPosition(self):
        raise NotImplementedError()

    # Private utility functions
    # def _set_motor_steps(self, N0=None, N1=None, N2=None):
    #     if not (N0 is None):
    #         self._N0 = int(N0)
    #     if not (N1 is None):
    #         self._N1 = int(N1)
    #     if not (N2 is None):
    #         self._N2 = int(N2)


    def _ToMsteps(self, userUnits : float) -> int:
        return int(userUnits * self._microstepsPerUserUnit)

    def _ToUU(self, mSteps : int) -> float:
        return ((mSteps * 1.0) / self._microstepsPerUserUnit)

    def _ToVelocityCmd(self, velocity) -> int:
        return int((64.0 * self._ToMsteps(velocity)) / 15625.0) * self._microstepsPerUserUnit

    def _get_globals(self):
        ret = {}
        for key, value in TMCL.GLOBAL_PARAMETER.iteritems():
            #print "GGP:",key+value
            bank, par, name, _, _ = key+value
            ret[name] = self.TMCL.ggp(bank, par)
        return ret

    def _get_parameters(self):
        retmotor = [{}, {}, {}]
        retsingle = {}
        for mn in range(3):
            for key, value in TMCL.AXIS_PARAMETER.iteritems():
                par, name, _, _ = (key,)+value
                #print "GAP:", mn, (key,)+value
                if par not in TMCL.SINGLE_AXIS_PARAMETERS:
                    retmotor[mn][name] = self.TMCL.gap(mn, par)
                elif mn == 0:
                    retsingle[name] = self.TMCL.gap(mn, par)
        return retmotor, retsingle

    def _set_important_parameters(self, maxspeed=2000, maxaccel=2000,
                                maxcurrent=72, standbycurrent=32, 
                                microstep_resolution=1,store=False):
        self.TMCL.sap(self._mn, 140, int(microstep_resolution))
        self.TMCL.sap(self._mn, 4, int(maxspeed))
        self.TMCL.sap(self._mn, 5, int(maxaccel))
        self.TMCL.sap(self._mn, 6, int(maxcurrent))
        self.TMCL.sap(self._mn, 7, int(standbycurrent))
        if not bool(store):
            return
        self.TMCL.stap(self._mn, 140)
        self.TMCL.stap(self._mn, 4)
        self.TMCL.stap(self._mn, 5)
        self.TMCL.stap(self._mn, 6)
        self.TMCL.stap(self._mn, 7)

    def _rotate(self, velocity):
        if velocity == 0:
            self.TMCL.mst(self._mn) #motor stop
        if velocity > 0:
            self.TMCL.ror(self._mn, velocity)
        else:
            self.TMCL.rol(self._mn, abs(velocity))        
        return velocity

    def _stop():
        self.TMCL.mst(self.number)



#if __name__ == "__main__":
#    
#    import time
#    time.sleep(100)
#
#    rocker = StepRocker(24, port='/dev/ttyACM0')
#    rocker.set_important_parameters(maxspeed=1000,
#                                    maxaccel=10,
#                                    maxcurrent=50,
#                                    standbycurrent=10,
#                                    microstep_resolution=4)
#    rocker.rotate(10.)
#    time.sleep(10)
#    rocker.stop()

