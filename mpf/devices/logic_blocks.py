"""Logic Blocks devices."""
from typing import Any, List

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.machine import MachineController
from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.utility_functions import Util


class LogicBlockState(object):

    """Represents the state of a logic_block."""

    def __init__(self, start_value):
        """Initialise state."""
        self.enabled = False
        self.completed = False
        self.value = start_value


@DeviceMonitor("value", "enabled", "completed")
class LogicBlock(SystemWideDevice, ModeDevice):

    """Parent class for each of the logic block classes."""

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialize logic block."""
        super().__init__(machine, name)
        self._state = None          # type: LogicBlockState
        self._start_enabled = None  # type: bool

        self.player_state_variable = "{}_state".format(self.name)
        '''player_var: (logic_block)_state

        desc: A dictionary that stores the internal state of the logic block
        with the name (logic_block). (In other words, a logic block called
        *mode1_hit_counter* will store its state in a player variable called
        ``mode1_hit_counter_state``).

        The state that's stored in this variable include whether the logic
        block is enabled and whether it's complete.
        '''

    def _initialize(self):
        if self.config['start_enabled'] is not None:
            self._start_enabled = self.config['start_enabled']
        else:
            self._start_enabled = not self.config['enable_events']

    def add_control_events_in_mode(self, mode: Mode) -> None:
        """Do not auto enable this device in modes."""
        pass

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None) -> dict:
        """Validate logic block config."""
        del is_mode_config
        del debug_prefix
        if 'events_when_complete' not in config:
            config['events_when_complete'] = ['logicblock_' + self.name + '_complete']

        if 'events_when_hit' not in config:
            config['events_when_hit'] = ['logicblock_' + self.name + '_hit']

        self.machine.config_validator.validate_config(
            self.config_section, config, self.name, ["device", "logic_blocks_common"])

        self._configure_device_logging(config)
        return config

    def can_exist_outside_of_game(self) -> bool:
        """Return true if persist_state is not set."""
        return not bool(self.config['persist_state'])

    def get_start_value(self) -> Any:
        """Return the start value for this block."""
        raise NotImplementedError("implement")

    def device_added_system_wide(self):
        """Initialise internal state."""
        self._state = LogicBlockState(self.get_start_value())
        super().device_added_system_wide()
        if not self.config['enable_events']:
            self.enable()

        if self.config['persist_state']:
            self.raise_config_error("Cannot set persist_state for system-wide logic_blocks", 1)

        self.post_update_event()

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Restore internal state from player if persist_state is set or create new state."""
        super().device_loaded_in_mode(mode, player)
        if self.config['persist_state']:
            if not player.is_player_var(self.player_state_variable):
                player[self.player_state_variable] = LogicBlockState(self.get_start_value())
                # enable device ONLY when we create a new entry in the player
                if self._start_enabled:
                    mode.add_mode_event_handler("mode_{}_starting".format(mode.name),
                                                self.enable, priority=mode.priority + 1)

            self._state = player[self.player_state_variable]
        else:
            self._state = LogicBlockState(self.get_start_value())
            if self._start_enabled:
                mode.add_mode_event_handler("mode_{}_starting".format(mode.name),
                                            self.enable, priority=mode.priority + 1)

        mode.add_mode_event_handler("mode_{}_starting".format(mode.name), self.post_update_event)

    def device_removed_from_mode(self, mode: Mode):
        """Unset internal state to prevent leakage."""
        super().device_removed_from_mode(mode)
        self._state = None

    @property
    def value(self):
        """Return value or None if that is currently not possible."""
        if self._state:
            return self._state.value
        else:
            return None

    @property
    def enabled(self):
        """Return if enabled."""
        return self._state and self._state.enabled

    @enabled.setter
    def enabled(self, value):
        """Set enable."""
        self._state.enabled = value

    @property
    def completed(self):
        """Return if completed."""
        return self._state and self._state.completed

    @completed.setter
    def completed(self, value):
        """Set if completed."""
        self._state.completed = value

    def post_update_event(self, **kwargs):
        """Post an event to notify about changes."""
        del kwargs
        value = self._state.value
        enabled = self._state.enabled
        self.machine.events.post("logicblock_{}_updated".format(self.name), value=value, enabled=enabled)
        '''event: logicblock_(name)_updated

        desc: The logic block called "name" has changed.

        This might happen when the block advanced, it was resetted or restored.

        args:
        value: The current value of this block.
        enabled: Whatever this block is enabled or not.
        '''

    def enable(self, **kwargs):
        """Enable this logic block.

        Automatically called when one of the
        enable_event events is posted. Can also manually be called.
        """
        del kwargs
        self.debug_log("Enabling")
        self.enabled = True
        self.post_update_event()

    def _post_hit_events(self, **kwargs):
        self.post_update_event()
        for event in self.config['events_when_hit']:
            self.machine.events.post(event, **kwargs)
            '''event: logicblock_(name)_hit

            desc: The logic block "name" was just hit.

            Note that this is the default hit event for logic blocks,
            but this can be changed in a logic block's "events_when_hit:"
            setting, so this might not be the actual event that's posted for
            all logic blocks in your machine.

            args: depend on the type
            '''

    def disable(self, **kwargs):
        """Disable this logic block.

        Automatically called when one of the
        disable_event events is posted. Can also manually be called.
        """
        del kwargs
        self.debug_log("Disabling")
        self.enabled = False

    def reset(self, **kwargs):
        """Reset the progress towards completion of this logic block.

        Automatically called when one of the reset_event events is called.
        Can also be manually called.
        """
        del kwargs
        self.completed = False
        self._state.value = self.get_start_value()
        self.debug_log("Resetting")
        self.post_update_event()

    def restart(self, **kwargs):
        """Restart this logic block by calling reset() and enable().

        Automatically called when one of the restart_event events is called.
        Can also be manually called.
        """
        del kwargs
        self.debug_log("Restarting (resetting then enabling)")
        self.reset()
        self.enable()

    def complete(self):
        """Mark this logic block as complete.

        Posts the 'events_when_complete'
        events and optionally restarts this logic block or disables it,
        depending on this block's configuration settings.
        """
        # if already completed do not complete again
        if self.completed:
            return

        # otherwise mark as completed
        self.completed = True

        self.debug_log("Complete")
        if self.config['events_when_complete']:
            for event in self.config['events_when_complete']:
                self.machine.events.post(event)
        '''event: logicblock_(name)_complete

        desc: The logic block called "name" has just been completed.

        Note that this is the default completion event for logic blocks, but
        this can be changed in a logic block's "events_when_complete:" setting,
        so this might not be the actual event that's posted for all logic
        blocks in your machine.
        '''

        # call reset to reset completion
        if self.config['reset_on_complete']:
            self.reset()

        # disable block
        if self.config['disable_on_complete']:
            self.disable()


class Counter(LogicBlock):

    """A type of LogicBlock that tracks multiple hits of a single event.

    This counter can be configured to track hits towards a specific end-goal
    (like number of tilt hits to tilt), or it can be an open-ended count (like
    total number of ramp shots).

    It can also be configured to count up or to count down, and can have a
    configurable counting interval.
    """

    config_section = 'counters'
    collection = 'counters'
    class_label = 'counter'

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialise counter."""
        super().__init__(machine, name)
        self.debug_log("Creating Counter LogicBlock")

        self.delay = DelayManager(self.machine.delayRegistry)

        self.ignore_hits = False
        self.hit_value = -1

    def _initialize(self):
        super()._initialize()
        self.hit_value = self.config['count_interval']

        if self.config['direction'] == 'down' and self.hit_value > 0:
            self.hit_value *= -1
        elif self.config['direction'] == 'up' and self.hit_value < 0:
            self.hit_value *= -1

    def get_start_value(self) -> int:
        """Return start count."""
        return self.config['starting_count'].evaluate([])

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None) -> dict:
        """Validate logic block config."""
        if 'events_when_hit' not in config:
            # for compatibility post the same default as previously for
            # counters. This one is deprecated.
            config['events_when_hit'] = ['counter_' + self.name + '_hit']

            # this is the one moving forward
            config['events_when_hit'].append('logicblock_' + self.name + '_hit')

        return super().validate_and_parse_config(config, is_mode_config, debug_prefix)

    def count(self, **kwargs):
        """Increase the hit progress towards completion.

        This method is also automatically called when one of the
        ``count_events`` is posted.

        """
        del kwargs
        if not self.enabled:
            return

        count_complete_value = self.config['count_complete_value'].evaluate([]) if self.config['count_complete_value']\
            is not None else None

        if not self.ignore_hits:
            self._state.value += self.hit_value
            self.debug_log("Processing Count change. Total: %s", self._state.value)

            args = {
                "count": self._state.value
            }
            if count_complete_value is not None:
                args['remaining'] = count_complete_value - self._state.value

            self._post_hit_events(**args)

            if count_complete_value is not None:

                if self.config['direction'] == 'up' and self._state.value >= count_complete_value:
                    self.complete()

                elif self.config['direction'] == 'down' and self._state.value <= count_complete_value:
                    self.complete()

            if self.config['multiple_hit_window']:
                self.debug_log("Beginning Ignore Hits")
                self.ignore_hits = True
                self.delay.add(name='ignore_hits_within_window',
                               ms=self.config['multiple_hit_window'],
                               callback=self.stop_ignoring_hits)

    def stop_ignoring_hits(self, **kwargs):
        """Cause the Counter to stop ignoring subsequent hits that occur within the 'multiple_hit_window'.

        Automatically called when the window time expires. Can safely be manually called.
        """
        del kwargs
        self.debug_log("Ending Ignore hits")
        self.ignore_hits = False


class Accrual(LogicBlock):

    """A type of LogicBlock which tracks many different events (steps) towards a goal.

    The steps are able to happen in any order.
    """

    config_section = 'accruals'
    collection = 'accruals'
    class_label = 'accrual'

    @property
    def config_section_name(self):
        """Return config section."""
        return "accrual"

    def __init__(self, machine, name):
        """Initialise Accrual."""
        super().__init__(machine, name)
        self.debug_log("Creating Accrual LogicBlock")

    def _initialize(self):
        super()._initialize()
        self.setup_event_handlers()

    def get_start_value(self) -> List[bool]:
        """Return start states."""
        return [False] * len(self.config['events'])

    def setup_event_handlers(self):
        """Add event handlers."""
        for step, events in enumerate(self.config['events']):
            for event in Util.string_to_list(events):
                self.machine.events.add_handler(event, self.hit, step=step)

    def hit(self, step: int, **kwargs):
        """Increase the hit progress towards completion.

        Automatically called
        when one of the `count_events` is posted. Can also manually be
        called.

        Args:
            step: Integer of the step number (0 indexed) that was just hit.
        """
        del kwargs
        if not self.enabled:
            return

        self.debug_log("Processing hit for step: %s", step)
        if not self._state.value[step]:
            self._state.value[step] = True
            self.debug_log("Status: %s", self._state.value)
            self._post_hit_events(step=step)

        if self._state.value.count(True) == len(self._state.value):
            self.complete()


class Sequence(LogicBlock):

    """A type of LogicBlock which tracks many different events (steps) towards a goal.

    The steps have to happen in order.
    """

    config_section = 'sequences'
    collection = 'sequences'
    class_label = 'sequence'

    @property
    def config_section_name(self):
        """Return config section."""
        return "sequence"

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialise sequence."""
        super().__init__(machine, name)
        self.debug_log("Creating Sequence LogicBlock")

    def _initialize(self):
        """Initialise sequence."""
        super()._initialize()
        self.setup_event_handlers()

    def get_start_value(self) -> int:
        """Return start step."""
        return 0

    def setup_event_handlers(self):
        """Add the handlers for the current step."""
        for step, events in enumerate(self.config['events']):
            for event in Util.string_to_list(events):
                # increase priority with steps to prevent advancing multiple steps at once
                self.machine.events.add_handler(event, self.hit, step=step, priority=step)

    def hit(self, step: int = None, **kwargs):
        """Increase the hit progress towards completion.

        Automatically called
        when one of the `count_events` is posted. Can also manually be
        called.
        """
        del kwargs
        if not self.enabled:
            return

        if step is not None and step != self._state.value:
            # got this for another state
            return

        self.debug_log("Processing Hit")

        self._state.value += 1
        self._post_hit_events(step=self._state.value)

        if self._state.value >= len(self.config['events']):
            self.complete()
