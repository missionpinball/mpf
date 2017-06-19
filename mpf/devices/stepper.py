"""Implements a servo in MPF."""
from mpf.core.delays import DelayManager

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.platform import StepperPlatform
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor(_position="position")
class Stepper(SystemWideDevice):

    """Represents an stepper motor based axis in a pinball machine.

    Args: Same as the Device parent class.
    """

    config_section = 'steppers'
    collection = 'steppers'
    class_label = 'stepper'

    def __init__(self, machine, name):
        """Initialise stepper."""
        self.hw_stepper = None
        self.platform = None        # type: Stepper
        self._cachedPosition = 0 # in user units
        self._ball_search_started = False
        self._min_pos = 0
        self._max_pos = 1
        self.positionMode = False
        self._cachedVelocity = 0
        self._isHomed = False
    
        self.delay = DelayManager(machine.delayRegistry)
        super().__init__(machine, name)

    def _initialize(self):
        self.platform = self.machine.get_platform_sections('stepper_controllers', self.config['platform'])

        for position in self.config['named_positions']:
            self.machine.events.add_handler(self.config['named_positions'][position],
                                            self._position_event,
                                            position=position)

        self.hw_stepper = self.platform.configure_stepper(self.config)
        self._position = self.config['reset_position']
        self._max_pos = self.config['pos_max']
        self._min_pos = self.config['pos_min']
        self._max_velocity = self.config['velocity_limit']

        mode = self.config['mode']
        if mode == 'position':
             self.positionMode = True
        elif mode == 'velocity':
             self.positionMode = False
        else:
             raise AssertionError("Operating Mode not defined")

        if self.config['include_in_ball_search']:
            self.machine.events.add_handler("ball_search_started",
                                            self._ball_search_start)
            self.machine.events.add_handler("ball_search_stopped",
                                            self._ball_search_stop)
    def currentPosition(self):
        """ return position in user units (vs microsteps) """
        return self.hw_stepper.currentPosition()

    def move_abs_pos(self, position):
        """Move servo to position."""
        if self._ball_search_started:
            return
        if not self.positionMode:
            raise RuntimeError("Cannot do a position move in velocity mode")
        if position >= self._min_pos and position <= self._max_pos:
            self.hw_stepper.move_abs_pos(position)
            self._cachedPosition = position # TODO: this needs to move to move complete handler
        else:
            raise ValueError("move_abs: position argument beyond limits")

    def home(self):
        """Home an axis, resetting 0 position"""
        if self.positionMode:
            self.hw_stepper.home()
            self._isHomed = True # TODO: this needs to move to move complete handler
            self._cachedPosition = 0 # TODO: this needs to move to move complete handler
        else:
            raise RuntimeError("Cannot home in velocity mode")

    def move_rel_pos(self, delta):
        """Move axis to a relative position"""
        start = self._cachedPosition
        self.move_abs_pos( start + delta )

    def move_vel_mode(self, velocity):
        """Move at a specific velocity indefinitely"""
        if self.positionMode:
            raise RuntimeError("Cannot do a velocity move in position mode")
        if velocity <= self._max_velocity:
            self.hw_stepper.move_vel_mode(velocity)
            self._cachedVelocity = velocity # TODO: this needs to move to move complete handler
        else:
            raise ValueError("move_vel_mode: velocity argument is above limit")

    @event_handler(1)
    def reset(self, **kwargs):
        """Go to reset position."""
        del kwargs
        if self.positionMode:
            if self._isHomed:
                self.move_abs_pos(0)
            else:
                self.home()
        else:
            self.move_vel_mode(0)

    @event_handler(5)
    def _position_event(self, position, **kwargs):
        del kwargs
        self.move_abs_pos(position)

    def _ball_search_start(self, **kwargs):
        del kwargs
        # we do not touch self._position during ball search so we can reset to
        # it later
        self._ball_search_started = True
        self._ball_search_go_to_min()

    def _ball_search_go_to_min(self):
        self._move_abs_pos(self.config['ball_search_min'])
        self.delay.add(name="ball_search", callback=self._ball_search_go_to_max, ms=self.config['ball_search_wait'])

    def _ball_search_go_to_max(self):
        self._move_abs_pos(self.config['ball_search_max'])
        self.delay.add(name="ball_search", callback=self._ball_search_go_to_min, ms=self.config['ball_search_wait'])

    def _ball_search_stop(self, **kwargs):
        del kwargs
        # stop delay
        self.delay.remove("ball_search")
        self._ball_search_started = False

        # move to last commanded
        if self.positionMode:
            self.move_abs_pos(self._cachedPosition)
        else:
            self.move_vel_mode(self._cachedVelocity)
    