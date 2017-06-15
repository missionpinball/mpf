
import trinamics.TMCL

"""Pololu Maestro servo controller platform."""
#import asyncio
import logging
import serial
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
        self.TMCL = TMCL.TMCLDevice(pself.config['port'], debug)

    def stop(self):
        """Close serial."""
        self.TMCL.stop()

    def configure_stepper(self, number: str):
        """Configure a smart stepper device in platform.

        Args:
            config (dict): Configuration of device
        """
        return TrinamicsTMCLStepper(int(number), self.config, self.serial)


class TrinamicsTMCLStepper(StepperPlatformInterface):

    """A servo on the pololu servo controller."""

    def __init__(self, number, config ):
        """Initialise Pololu servo."""
        self.log = logging.getLogger('PololuServo')
        self.number = int(motor)
        self.config = config

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
        """Move at a specific velocity indefinitely"""
        raise NotImplementedError()

    def set_motor_steps(self, N0=None, N1=None, N2=None):
        if not (N0 is None):
            self._N0 = int(N0)
        if not (N1 is None):
            self._N1 = int(N1)
        if not (N2 is None):
            self._N2 = int(N2)

    def get_globals(self):
        ret = {}
        for key, value in TMCL.GLOBAL_PARAMETER.iteritems():
            #print "GGP:",key+value
            bank, par, name, _, _ = key+value
            ret[name] = self.TMCL.ggp(bank, par)
        return ret

    def get_parameters(self):
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

    def set_important_parameters(self, maxspeed=2000, maxaccel=2000,
                                maxcurrent=72, standbycurrent=32, 
                                microstep_resolution=1,store=False):
        self.TMCL.sap(0, 140, int(microstep_resolution))
        for mn in range(3):
            self.TMCL.sap(mn, 4, int(maxspeed))
            self.TMCL.sap(mn, 5, int(maxaccel))
            self.TMCL.sap(mn, 6, int(maxcurrent))
            self.TMCL.sap(mn, 7, int(standbycurrent))
        if not bool(store):
            return
        self.TMCL.stap(0, 140)
        for mn in range(3):
            self.TMCL.stap(mn, 4)
            self.TMCL.stap(mn, 5)
            self.TMCL.stap(mn, 6)
            self.TMCL.stap(mn, 7)

    def rotate(self, frequency, motor=0, direction='cw'):
        microstep_resolution = self.TMCL.gap(0, 140)
        vel = int(frequency * self.N0 * microstep_resolution)
        mn = int(motor)
        if str(direction) == 'cw':
            self.TMCL.ror(mn, vel)
        elif str(direction) == 'ccw':
            self.TMCL.rol(mn, vel)
        else:
            raise ValueError('direction needs to be either "cw" or "ccw"')
        return vel / float( self.N0 * microstep_resolution )

    def stop():
        self.TMCL.mst(self.number)



#if __name__ == "__main__":
#    
#    import time
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

