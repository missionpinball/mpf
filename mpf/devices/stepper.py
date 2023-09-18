"""Implements a servo in MPF."""
import asyncio

from typing import Optional

from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface

from mpf.core.delays import DelayManager

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.utility_functions import Util


@DeviceMonitor(_current_position="position", _target_position="target_position", _is_homed="is_homed")
class Stepper(SystemWideDevice):

    """Represents an stepper motor based axis in a pinball machine.

    Args: Same as the Device parent class.
    """

    config_section = 'steppers'
    collection = 'steppers'
    class_label = 'stepper'

    __slots__ = ["hw_stepper", "platform", "_target_position", "_current_position", "_ball_search_started",
                 "_ball_search_old_target", "_is_homed", "_is_moving", "_move_task", "delay"]

    def __init__(self, machine, name):
        """initialize stepper."""
        self.hw_stepper = None          # type: Optional[StepperPlatformInterface]
        self.platform = None            # type: Optional[Stepper]
        self._target_position = 0       # in user units
        self._current_position = 0      # in user units
        self._ball_search_started = False
        self._ball_search_old_target = 0
        self._is_homed = False
        self._is_moving = asyncio.Event()
        self._move_task = None          # type: Optional[asyncio.Task]
        self.delay = DelayManager(machine)
        super().__init__(machine, name)

    async def _initialize(self):
        await super()._initialize()
        self.platform = self.machine.get_platform_sections('stepper_controllers', self.config['platform'])
        self.platform.assert_has_feature("steppers")

        # first target is the reset position but we might get an early target during startup via events
        self._target_position = self.config['reset_position']

        for position in self.config['named_positions']:
            self.machine.events.add_handler(self.config['named_positions'][position],
                                            self.event_move_to_position,
                                            position=position)

        if not self.platform.features['allow_empty_numbers'] and self.config['number'] is None:
            self.raise_config_error("Stepper must have a number.", 2)

        self.hw_stepper = await self.platform.configure_stepper(self.config['number'],
                                                                self.config['platform_settings'])

        if self.config['include_in_ball_search']:
            self.machine.events.add_handler("ball_search_started",
                                            self._ball_search_start)
            self.machine.events.add_handler("ball_search_stopped",
                                            self._ball_search_stop)

        if self.config['homing_mode'] == "switch" and not self.config['homing_switch']:
            self.raise_config_error("Cannot use homing_mode switch without a homing_switch. Please add homing_switch or"
                                    " use homing_mode hardware.", 1)

        self._move_task = asyncio.create_task(self._run())
        self._move_task.add_done_callback(Util.raise_exceptions)

    def validate_and_parse_config(self, config, is_mode_config, debug_prefix: str = None):
        """Validate stepper config."""
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)
        platform = self.machine.get_platform_sections(
            'stepper_controllers', getattr(config, "platform", None))
        config['platform_settings'] = platform.validate_stepper_section(
            self, config.get('platform_settings', None))
        self._configure_device_logging(config)
        return config

    async def _run(self):
        # wait for switches to be initialized
        await self.machine.events.wait_for_event("init_phase_3")

        # first home the stepper
        self.debug_log("Homing stepper")
        await self._home()

        # run the loop at least once
        self._is_moving.set()

        while True:
            # wait until we should be moving
            await self._is_moving.wait()
            self._is_moving.clear()
            # store target position in local variable since it may change in the meantime
            target_position = self._target_position
            delta = target_position - self._current_position
            if delta != 0:
                self.debug_log("Got move command. Current position: %s Target position: %s Delta: %s",
                               self._current_position, target_position, delta)
                # move stepper
                self.hw_stepper.move_rel_pos(delta)
                # wait for the move to complete
                await self.hw_stepper.wait_for_move_completed()
            else:
                self.debug_log("Got move command. Stepper already at target. Not moving.")
            # set current position
            self._current_position = target_position
            # post ready event
            self._post_ready_event()
            self.debug_log("Move completed")

    def _move_to_absolute_position(self, position):
        """Move servo to position."""
        self.debug_log("Moving to position %s", position)
        if self.config['pos_min'] <= position <= self.config['pos_max']:
            self._target_position = position
            self._is_moving.set()
        else:
            raise ValueError("_move_to_absolute_position: position argument beyond limits")

    async def _home(self):
        """Home an axis, resetting 0 position."""
        self._is_homed = False
        self._is_moving.set()
        if self.config['homing_mode'] == "hardware":
            self.info_log("Homing stepper using hardware homing.")
            self.hw_stepper.home(self.config['homing_direction'])
            await self.hw_stepper.wait_for_move_completed()
        else:
            self.info_log("Homing stepper using switch homing with switch %s.", self.config["homing_switch"])
            # move the stepper manually
            if self.config['homing_direction'] == "clockwise":
                self.hw_stepper.move_vel_mode(1)
            else:
                self.hw_stepper.move_vel_mode(-1)

            # wait until home switch becomes active
            await self.machine.switch_controller.wait_for_switch(self.config['homing_switch'],
                                                                 only_on_change=False)
            self.hw_stepper.stop()
            self.hw_stepper.set_home_position()

        self.info_log("Stepper reached home.")

        self._is_homed = True
        self._is_moving.clear()
        # home position is 0
        self._current_position = 0

    def _post_ready_event(self):
        if not self._ball_search_started:
            self.machine.events.post('stepper_' + self.name + "_ready", position=self._current_position)
            '''event: stepper_(name)_ready'''

    def stop_device(self):
        """Stop motor."""
        self.hw_stepper.stop()
        self._is_moving.clear()
        if self._move_task:
            self._move_task.cancel()
            self._move_task = None

    @event_handler(1)
    def event_reset(self, **kwargs):
        """Event handler for reset event."""
        del kwargs
        self.reset()

    def reset(self):
        """Move to reset position."""
        self._move_to_absolute_position(self.config['reset_position'])

    @event_handler(5)
    def event_move_to_position(self, position=None, **kwargs):
        """Event handler for move_to_position event."""
        del kwargs
        if position is None:
            raise AssertionError("move_to_position event is missing a position.")

        self.move_to_position(position)

    def move_to_position(self, position):
        """Move stepper to a position."""
        self._target_position = position
        if self._ball_search_started:
            return
        self._move_to_absolute_position(position)

    def _ball_search_start(self, **kwargs):
        del kwargs
        # we do not touch self._position during ball search so we can reset to
        # it later
        self._ball_search_old_target = self._target_position
        self._ball_search_started = True
        self._ball_search_go_to_min()

    def _ball_search_go_to_min(self):
        self._move_to_absolute_position(self.config['ball_search_min'])
        self.delay.add(name="ball_search", callback=self._ball_search_go_to_max, ms=self.config['ball_search_wait'])

    def _ball_search_go_to_max(self):
        self._move_to_absolute_position(self.config['ball_search_max'])
        self.delay.add(name="ball_search", callback=self._ball_search_go_to_min, ms=self.config['ball_search_wait'])

    def _ball_search_stop(self, **kwargs):
        del kwargs
        # stop delay
        self.delay.remove("ball_search")
        self._ball_search_started = False

        # move to last position
        self._target_position = self._ball_search_old_target
        self._move_to_absolute_position(self._target_position)
