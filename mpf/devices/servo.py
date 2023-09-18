"""Implements a servo in MPF."""
from mpf.core.delays import DelayManager

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.platform import ServoPlatform
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor(_position="position")
class Servo(SystemWideDevice):

    """Represents a servo in a pinball machine.

    Args: Same as the Device parent class.
    """

    config_section = 'servos'
    collection = 'servos'
    class_label = 'servo'

    def __init__(self, machine, name):
        """initialize servo."""
        self.hw_servo = None
        self.platform = None        # type: ServoPlatform
        self._position = None
        self.speed_limit = None
        self.acceleration_limit = None
        self._ball_search_started = False
        self.delay = DelayManager(machine)
        super().__init__(machine, name)

    async def _initialize(self):
        await super()._initialize()
        self.platform = self.machine.get_platform_sections('servo_controllers', self.config['platform'])
        self.platform.assert_has_feature("servos")

        for position in self.config['positions']:
            self.machine.events.add_handler(self.config['positions'][position],
                                            self._position_event,
                                            position=position)

        if not self.platform.features['allow_empty_numbers'] and self.config['number'] is None:
            self.raise_config_error("Servo must have a number.", 1)

        self.hw_servo = await self.platform.configure_servo(self.config['number'], self.config)
        self._position = self.config['reset_position']
        self.speed_limit = self.config['speed_limit']
        self.acceleration_limit = self.config['acceleration_limit']

        if self.config['include_in_ball_search']:
            self.machine.events.add_handler("ball_search_started",
                                            self._ball_search_start)
            self.machine.events.add_handler("ball_search_stopped",
                                            self._ball_search_stop)

        self.set_speed_limit(self.speed_limit)
        self.set_acceleration_limit(self.acceleration_limit)

        self.machine.events.add_handler("shutdown", self.event_stop)

    @event_handler(1)
    def event_reset(self, **kwargs):
        """Event handler for reset event."""
        del kwargs
        self.reset()

    def reset(self):
        """Go to reset position."""
        self.go_to_position(self.config['reset_position'])

    @event_handler(10)
    def event_stop(self, **kwargs):
        """Event handler for stop event."""
        del kwargs
        self.stop()

    def stop(self):
        """Stop this servo.

        This should either home the servo or disable the output.
        """
        self.debug_log("Stopping servo")
        self.hw_servo.stop()

    @event_handler(5)
    def _position_event(self, position, **kwargs):
        del kwargs
        self.go_to_position(position)

    def go_to_position(self, position):
        """Move servo to position."""
        self._position = position
        if self._ball_search_started:
            return
        self._go_to_position(position)

    def _go_to_position(self, position):
        # linearly interpolate between servo limits
        corrected_position = self.config['servo_min'] + position * (
            self.config['servo_max'] - self.config['servo_min'])

        self.debug_log("Moving to position %s (corrected: %s)", position, corrected_position)

        # call platform with calculated position
        self.hw_servo.go_to_position(corrected_position)

        if self.config["stop_timeout_after_last_move"] is not None:
            self.delay.reset(self.config["stop_timeout_after_last_move"], self.stop, "movement_timeout")

    def set_speed_limit(self, speed_limit):
        """Set speed parameter."""
        self.hw_servo.set_speed_limit(speed_limit)

    def set_acceleration_limit(self, acceleration_limit):
        """Set acceleration parameter."""
        self.hw_servo.set_acceleration_limit(acceleration_limit)

    def _ball_search_start(self, **kwargs):
        del kwargs
        # we do not touch self._position during ball search so we can reset to
        # it later
        self._ball_search_started = True
        self._ball_search_go_to_min()

    def _ball_search_go_to_min(self):
        self._go_to_position(self.config['ball_search_min'])
        self.delay.add(name="ball_search", callback=self._ball_search_go_to_max, ms=self.config['ball_search_wait'])

    def _ball_search_go_to_max(self):
        self._go_to_position(self.config['ball_search_max'])
        self.delay.add(name="ball_search", callback=self._ball_search_go_to_min, ms=self.config['ball_search_wait'])

    def _ball_search_stop(self, **kwargs):
        del kwargs
        # stop delay
        self.delay.remove("ball_search")
        self._ball_search_started = False

        # move to last position set
        self._go_to_position(self._position)
