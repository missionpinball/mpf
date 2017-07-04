
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
        self.TMCL = None

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
        self._pulse_div = 5 #tbd add to config
        self._ramp_div =  9 #tbd add to config
        self._clockFreq = 16000000.0
        self.config = config
        self.log = logging.getLogger('TMCL Stepper')
        self._mn = int(self.config['number'])
        self.TMCL = TMCLDevice
        self._move_current = int(2.55 * self.config['move_current']) #percent to 0...255(100%)
        self._hold_current = int(2.55 * self.config['hold_current']) #percent to 0...255(100%)
        self._microstep_per_fullstep = self.config['microstep_per_fullstep']
        self._fullstep_per_userunit = self.config['fullstep_per_userunit']
        self._velocity_limit = self.UU_To_VelocityCmd(self.config['velocity_limit'])
        self._acceleration_limit = self.UU_To_AccelCmd(self.config['acceleration_limit'])
        mode = self.config['mode']
        if mode == 'position':
            self._home_direction = self.config['homing_direction']
            self._homing_speed = self.UU_To_VelocityCmd(self.config['homing_speed'])

        self._set_important_parameters(self._velocity_limit, self._acceleration_limit,
                                             self._move_current, self._hold_current, 
                                             self._getMicroStepMode(self._microstep_per_fullstep), False)
        # apply pulse and ramp divisors as well                                             
        self.TMCL.sap(self._mn, 154, self._pulse_div)
        self.TMCL.sap(self._mn, 153, self._ramp_div)
        self._homingActive = False


    # Public Stepper Platform Interface
    def home(self):
        """Home an axis, resetting 0 position"""
        self.TMCL.rfs(self._mn,'STOP') # in case in progress
        self._set_home_parameters()
        self.TMCL.rfs(self._mn,'START')
        self._homingActive = True

    def move_abs_pos(self, position):
        """Move axis to a certain absolute position"""
        microStepPos = self._UU_To_Microsteps(position)
        self.TMCL.mvp(self._mn,"ABS",microStepPos)

    def move_rel_pos(self, position):
        """Move axis to a relative position"""
        microStepRel = self._UU_To_Microsteps(position)
        self.TMCL.mvp(self._mn,"REL",microStepPos)

    def move_vel_mode(self, velocity):
        """Move at a specific velocity and direction (pos = clockwise, neg = counterclockwise)"""
        self._rotate(velocity)

    def currentPosition(self):
        microSteps = self.TMCL.gap(self._mn, 1)
        return self._MicroSteps_To_UU(microSteps)

    def stop(self):
        self.TMCL.mst(self._mn)        

    def is_move_complete(self):
        if self._homingActive == True:
            ret = self.TMCL.rfs(self._mn,'STATUS') 
            if ret != 0:  # This is reversed from manual but is how it works
                 return False
            else:
                self._homingActive = False
                return True  
        else: # check normal move status
            ret = self.TMCL.gap(self._mn, 8)
            if ret == 1:
                return True
            else:
                return False

    #Private Utility Functions
    def _getMicroStepMode(self, microsteps_per_fullstep : int) -> int:
        retVal = int({
            1: 0,
            2: 1,
            4: 2,
            8: 3,
            16: 4,
            32: 5,
            64: 6,
            128: 7,
            256: 8
        }.get(microsteps_per_fullstep,0))
        return retVal
    
    def _UU_To_Microsteps(self , userunits ):
        return userunits * self._fullstep_per_userunit * self._microstep_per_fullstep
    def _MicroSteps_To_UU(self, microsteps):
        return microsteps / (self._fullstep_per_userunit * self._microstep_per_fullstep)

    def _ToVelocityCmd( self, microStepsPerSec ):
        ret =  (microStepsPerSec * 2**self._pulse_div * 2048.0 * 32.0) / self._clockFreq
        if abs(ret) > 2047:
            raise ValueError("Scaled Velocity too high, lower pulse_div")
        if ret < 1:
            raise ValueError("Scaled Velocity too low, raise pulse_div")
        return int(ret)

    def _ToAccelerationCmd( self, microStepsPerSS ):
        ret = (2 ** (self._pulse_div + self._ramp_div + 29) * microStepsPerSS) /  self._clockFreq ** 2
        if ret > 2047:
            raise ValueError("Acceleration too high, lower ramps_div")
        if ret < 1:
            raise ValueError("Acceleration too low, raise ramps_div")
        return int(ret)
    
    def UU_To_VelocityCmd( self, userUnit ) :
        microStepsPerSec = userUnit * self._fullstep_per_userunit * self._microstep_per_fullstep
        return self._ToVelocityCmd(microStepsPerSec)

    def UU_To_AccelCmd( self, userUnit ) :
        microStepsPerSec = userUnit * self._fullstep_per_userunit * self._microstep_per_fullstep
        return self._ToAccelerationCmd(microStepsPerSec)

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

    def _set_home_parameters(self):
        #self.TMCL.sap(self._mn, 9,  ) #ref. switch status
        #self.TMCL.sap(self._mn, 10, ) #right limit switch status
        #self.TMCL.sap(self._mn, 11, ) #left limit switch status
        #self.TMCL.sap(self._mn, 12, ) #right limit switch disable
        #self.TMCL.sap(self._mn, 13, ) #left limit switch disable
        #self.TMCL.sap(self._mn, 141, ) #ref. switch tolerance
        #self.TMCL.sap(self._mn, 149, ) #soft stop flag
        self.TMCL.sap(self._mn, 194, self._homing_speed) #referencing search speed
        if self._home_direction == 'clockwise':
            self.TMCL.sap(self._mn, 193, 8) #ref. search mode
        elif self._home_direction == 'counterclockwise':
            self.TMCL.sap(self._mn, 193, 7)
        #self.TMCL.sap(self._mn, 195, ) #referencing switch speed
        #self.TMCL.sap(self._mn, 196, ) # distance end switches 

    def _rotate(self, velocity):
        if velocity == 0:
            self.TMCL.mst(self._mn) #motor stop
        if velocity > 0:
            self.TMCL.ror(self._mn, self.UU_To_VelocityCmd(velocity))
        else:
            self.TMCL.rol(self._mn, self.UU_To_VelocityCmd(abs(velocity))) 
        return velocity

     

