"""Logic Blocks devices."""
from random import shuffle

from typing import Any, List, Optional

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.machine import MachineController
from mpf.core.mode import Mode, MODE_STARTING_EVENT_TEMPLATE
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.utility_functions import Util


class LogicBlockState:

    """Represents the state of a logic_block."""

    __slots__ = ["enabled", "completed", "value"]

    def __init__(self):
        """initialize state."""
        self.enabled = False
        self.completed = False
        self.value = None


@DeviceMonitor("value", "enabled", "completed")
class LogicBlock(SystemWideDevice, ModeDevice):

    """Parent class for each of the logic block classes."""

    __slots__ = ["delay", "_state", "_start_enabled", "player_state_variable"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialize logic block."""
        super().__init__(machine, name)
        self.delay = DelayManager(self.machine)
        self._state = None          # type: Optional[LogicBlockState]
        self._start_enabled = None  # type: Optional[bool]

        self.player_state_variable = "{}_state".format(self.name)
        '''player_var: (logic_block)_state
        config_section: counters, accruals, sequences

        desc: A dictionary that stores the internal state of the logic block
        with the name (logic_block). (In other words, a logic block called
        *mode1_hit_counter* will store its state in a player variable called
        ``mode1_hit_counter_state``).

        The state that's stored in this variable include whether the logic
        block is enabled and whether it's complete.
        '''

    async def _initialize(self):
        await super()._initialize()
        if self.config['start_enabled'] is not None:
            self._start_enabled = self.config['start_enabled']
        else:
            self._start_enabled = not self.config['enable_events']

    def add_control_events_in_mode(self, mode: Mode) -> None:
        """Do not auto enable this device in modes."""

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None) -> dict:
        """Validate logic block config."""
        del is_mode_config
        del debug_prefix
        if 'events_when_complete' not in config:
            config['events_when_complete'] = ['logicblock_' + self.name + '_complete']

        if 'events_when_hit' not in config:
            config['events_when_hit'] = ['logicblock_' + self.name + '_hit']

        self.machine.config_validator.validate_config(
            self.config_section, config, self.name, ("device", "logic_blocks_common"))

        self._configure_device_logging(config)
        return config

    @property
    def can_exist_outside_of_game(self) -> bool:
        """Return true if persist_state is not set."""
        return not bool(self.config['persist_state'])

    def get_start_value(self) -> Any:
        """Return the start value for this block."""
        raise NotImplementedError("implement")

    async def device_added_system_wide(self):
        """initialize internal state."""
        self._state = LogicBlockState()
        self.value = self.get_start_value()
        await super().device_added_system_wide()
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
                player[self.player_state_variable] = LogicBlockState()
                # enable device ONLY when we create a new entry in the player
                if self._start_enabled:
                    mode.add_mode_event_handler(MODE_STARTING_EVENT_TEMPLATE.format(mode.name),
                                                self.event_enable, priority=mode.priority + 1)

                self._state = player[self.player_state_variable]
                self.value = self.get_start_value()
            else:
                self._state = player[self.player_state_variable]
        else:
            self._state = LogicBlockState()
            self.value = self.get_start_value()
            if self._start_enabled:
                mode.add_mode_event_handler(MODE_STARTING_EVENT_TEMPLATE.format(mode.name),
                                            self.event_enable, priority=mode.priority + 1)

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

        return None

    @value.setter
    def value(self, value):
        """Set the value."""
        self._state.value = value

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
        config_section: counters, accruals, sequences

        desc: The logic block called "name" has changed.

        This might happen when the block advanced, it was resetted or restored.

        args:
        value: The current value of this block.
        enabled: Whatever this block is enabled or not.
        '''

    def enable(self):
        """Enable this logic block.

        Automatically called when one of the
        enable_event events is posted. Can also manually be called.
        """
        super().enable()
        self.debug_log("Enabling")
        self.enabled = True
        self.post_update_event()
        self._logic_block_timer_start()

    def _post_hit_events(self, **kwargs):
        self.post_update_event()
        for event in self.config['events_when_hit']:
            self.machine.events.post(event, **kwargs)
            '''event: logicblock_(name)_hit
            config_section: counters, accruals, sequences

            desc: The logic block "name" was just hit.

            Note that this is the default hit event for logic blocks,
            but this can be changed in a logic block's "events_when_hit:"
            setting, so this might not be the actual event that's posted for
            all logic blocks in your machine.

            args: depend on the type
            '''

    @event_handler(0)
    def event_disable(self, **kwargs):
        """Event handler for disable event."""
        del kwargs
        self.disable()

    def disable(self):
        """Disable this logic block.

        Automatically called when one of the
        disable_event events is posted. Can also manually be called.
        """
        self.debug_log("Disabling")
        self.enabled = False
        self.post_update_event()
        self.delay.remove("timeout")

    @event_handler(4)
    def event_reset(self, **kwargs):
        """Event handler for reset event."""
        del kwargs
        self.reset()

    def reset(self):
        """Reset the progress towards completion of this logic block.

        Automatically called when one of the reset_event events is called.
        Can also be manually called.
        """
        self.completed = False
        self.value = self.get_start_value()
        self.debug_log("Resetting")
        self.post_update_event()
        self._logic_block_timer_start()

    def _logic_block_timer_start(self):
        if self.config['logic_block_timeout']:
            self.debug_log("Setting up a logic block timer for %sms",
                           self.config['logic_block_timeout'])

            self.delay.reset(name="timeout",
                             ms=self.config['logic_block_timeout'],
                             callback=self._logic_block_timeout)

    def _logic_block_timeout(self):
        """Reset the progress towards completion of this logic block when timer expires.

        Automatically called when one of the logic_block_timer_complete
        events is called.
        """
        self.info_log("Logic Block timeouted")
        self.machine.events.post("{}_timeout".format(self.name))
        '''event: (name)_timeout
        config_section: counters, accruals, sequences

        desc: The logic block called "name" has just timeouted.

        Timeouts are disabled by default but you can set logic_block_timeout to
        enable them. They will run from start of your logic block until it is
        stopped.
        '''
        self.reset()

    @event_handler(5)
    def event_restart(self, **kwargs):
        """Event handler for restart event."""
        del kwargs
        self.restart()

    def restart(self):
        """Restart this logic block by calling reset() and enable().

        Automatically called when one of the restart_event events is called.
        Can also be manually called.
        """
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
        self.delay.remove("timeout")

        self.debug_log("Complete")
        if self.config['events_when_complete']:
            for event in self.config['events_when_complete']:
                self.machine.events.post(event)
        '''event: logicblock_(name)_complete
        config_section: counters, accruals, sequences

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

    __slots__ = ["delay", "ignore_hits", "hit_value"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """initialize counter."""
        super().__init__(machine, name)

        self.ignore_hits = False
        self.hit_value = -1

    async def _initialize(self):
        await super()._initialize()
        self.debug_log("Creating Counter LogicBlock")
        self.hit_value = self.config['count_interval']

        if (self.config['direction'] == 'down' and self.hit_value > 0) or \
                (self.config['direction'] == 'up' and self.hit_value < 0):
            self.hit_value *= -1

        # Add control events if included in the config
        if self.config['control_events']:
            self._setup_control_events(self.config['control_events'])

    def add_control_events_in_mode(self, mode: Mode) -> None:
        """Do not auto enable this device in modes."""

    def _setup_control_events(self, event_list):
        self.debug_log("Setting up control events")

        kwargs = {}
        for entry in event_list:
            if entry['action'] in ('add', 'subtract', 'jump'):
                handler = getattr(self, "event_{}".format(entry['action']))
                kwargs = {'value': entry['value']}
            else:
                raise AssertionError("Invalid control_event action {} in mode".
                                     format(entry['action']), self.name)
            self.machine.events.add_handler(entry['event'], handler, **kwargs)

    def check_complete(self, count_complete_value=None):
        """Check if counter is completed.

        Return true if the counter has reached or surpassed its specified
        completion value, return False if no completion criteria or is
        not complete.
        """
        # If count_complete_value was not passed, obtain it
        if count_complete_value is None and self.config.get("count_complete_value"):
            count_complete_value = self.config["count_complete_value"].evaluate([])

        if count_complete_value is not None:
            if self.config['direction'] == 'up':
                return self.value >= count_complete_value
            if self.config['direction'] == 'down':
                return self.value <= count_complete_value

        return False

    def event_add(self, value, **kwargs):
        """Add to the value of this counter.

        Args:
        ----
            value: Value to add to the counter.
            kwargs: Additional arguments.
        """
        evaluated_value = value.evaluate_or_none(kwargs)
        if evaluated_value is None:
            self.log.warning("Placeholder %s for counter add did not evaluate with args %s", value, kwargs)
            return
        # Add to the counter the specified value
        self.value += evaluated_value
        self.post_update_event()
        # Check if count is complete given the updated value
        if self.check_complete():
            self.complete()

    def event_subtract(self, value, **kwargs):
        """Subtract from the value of this counter.

        Args:
        ----
            value: Value to subtract from the counter.
            kwargs: Additional arguments.
        """
        evaluated_value = value.evaluate_or_none(kwargs)
        if evaluated_value is None:
            self.log.warning("Placeholder %s for counter substract did not evaluate with args %s", value, kwargs)
            return
        # Subtract from the counter the specified value
        self.value -= evaluated_value
        self.post_update_event()
        # Check if count is complete given the updated value
        if self.check_complete():
            self.complete()

    def event_jump(self, value, **kwargs):
        """Set the internal value of the counter.

        Args:
        ----
            value: Value to add to jump to.
            kwargs: Additional arguments.
        """
        evaluated_value = value.evaluate_or_none(kwargs)
        if evaluated_value is None:
            self.log.warning("Placeholder %s for counter jump did not evaluate with args %s", value, kwargs)
            return
        # Set the internal value of the counter to the specified value
        self.value = evaluated_value
        self.post_update_event()
        # Check if count is complete given the updated value
        if self.check_complete():
            self.complete()

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

    @event_handler(0)
    def event_count(self, **kwargs):
        """Event handler for count events."""
        del kwargs
        self.count()

    def count(self):
        """Increase the hit progress towards completion.

        This method is also automatically called when one of the
        ``count_events`` is posted.

        """
        if not self.enabled:
            return

        count_complete_value = self.config['count_complete_value'].evaluate([]) if self.config['count_complete_value']\
            is not None else None

        if not self.ignore_hits:
            self.value += self.hit_value
            self.debug_log("Processing Count change. Total: %s", self.value)

            args = {
                "count": self.value
            }
            if count_complete_value is not None:
                if self.config['direction'] == 'down':
                    args['hits'] = self.get_start_value() - self.value
                    args['remaining'] = self.value - count_complete_value
                else:
                    args['hits'] = self.value - self.get_start_value()
                    args['remaining'] = count_complete_value - self.value

            self._post_hit_events(**args)

            if self.check_complete(count_complete_value):
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

    __slots__ = []  # type: List[str]

    @property
    def config_section_name(self):
        """Return config section."""
        return "accrual"

    async def _initialize(self):
        await super()._initialize()
        self.debug_log("Creating Accrual LogicBlock")
        self.setup_event_handlers()

    def get_start_value(self) -> List[bool]:
        """Return start states."""
        return [False] * len(self.config['events'])

    def setup_event_handlers(self):
        """Add event handlers."""
        for step, events in enumerate(self.config['events']):
            for event in Util.string_to_event_list(events):
                self.machine.events.add_handler(event, self.hit, step=step)

    @event_handler(0)
    def event_advance_random(self, **kwargs):
        """Event handler for advance random events."""
        del kwargs
        if not self.enabled:
            return

        self.debug_log("Advancing random step in accrual.")
        randomized_values = list(enumerate(self.value))
        shuffle(randomized_values)
        step = None
        for step, state in randomized_values:
            if not state:
                break
        else:
            return

        if step is None:
            return

        # call existing path
        self.hit(step)

    def hit(self, step: int, **kwargs):
        """Increase the hit progress towards completion.

        Automatically called
        when one of the `count_events` is posted. Can also manually be
        called.

        Args:
        ----
            step: Integer of the step number (0 indexed) that was just hit.
        """
        del kwargs
        if not self.enabled:
            return

        self.debug_log("Processing hit for step: %s", step)
        if not self.value[step]:
            self.value[step] = True
            self.debug_log("Status: %s", self.value)
            self._post_hit_events(step=step)

        if self.value.count(True) == len(self.value):
            self.complete()


class Sequence(LogicBlock):

    """A type of LogicBlock which tracks many different events (steps) towards a goal.

    The steps have to happen in order.
    """

    config_section = 'sequences'
    collection = 'sequences'
    class_label = 'sequence'

    __slots__ = []  # type: List[str]

    @property
    def config_section_name(self):
        """Return config section."""
        return "sequence"

    async def _initialize(self):
        """initialize sequence."""
        await super()._initialize()
        self.debug_log("Creating Sequence LogicBlock")
        self.setup_event_handlers()

    def get_start_value(self) -> int:
        """Return start step."""
        return 0

    def setup_event_handlers(self):
        """Add the handlers for the current step."""
        for step, events in enumerate(self.config['events']):
            for event in Util.string_to_event_list(events):
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

        if step is not None and step != self.value:
            # got this for another state
            return

        self.debug_log("Processing Hit")

        self.value += 1
        self._post_hit_events(step=self.value)

        if self.value >= len(self.config['events']):
            self.complete()
