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
        """Initialise smart stepper."""
        self.hw_stepper = None
        self.platform = None        # type: ServoPlatform
        self._position = None
        self._ball_search_started = False
        self.delay = DelayManager(machine.delayRegistry)
        super().__init__(machine, name)

    def _initialize(self):
        self.platform = self.machine.get_platform_sections('stepper_controllers', self.config['platform'])

        for position in self.config['positions']:
            self.machine.events.add_handler(self.config['positions'][position],
                                            self._position_event,
                                            position=position)

        self.hw_stepper = self.platform.configure_stepper(self.config['number'])
        self._position = self.config['reset_position']

        if self.config['include_in_ball_search']:
            self.machine.events.add_handler("ball_search_started",
                                            self._ball_search_start)
            self.machine.events.add_handler("ball_search_stopped",
                                            self._ball_search_stop)

    @event_handler(1)
    def reset(self, **kwargs):
        """Go to reset position."""
        del kwargs
        self.move_abs_pos(self.config['reset_position'])

    @event_handler(5)
    def _position_event(self, position, **kwargs):
        del kwargs
        self.move_abs_pos(position)

    def move_abs_pos(self, position):
        """Move servo to position."""
        self._position = position
        if self._ball_search_started:
            return
        self._move_abs_pos(position)

    def _move_abs_pos(self, position):
        # linearly interpolate between servo limits
        #position = self.config['servo_min'] + position * (
        #    self.config['servo_max'] - self.config['servo_min'])

        # call platform with calculated position
        self.hw_stepper.move_abs_pos(position)

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

        # move to last position set
        self._move_abs_pos(self._position)
