"""MPF plugin which implements Logic Blocks."""
import abc
import copy
import logging

from mpf.core.delays import DelayManager
from mpf.core.machine import MachineController
from mpf.core.mode import Mode
from mpf.core.player import Player
from mpf.core.utility_functions import Util


class LogicBlocks(object):

    """LogicBlock Manager."""

    def __init__(self, machine: MachineController):
        """Initialise LogicBlock manager."""
        self.log = logging.getLogger('Logic Blocks Manager')

        self.machine = machine

        # Tell the mode controller that it should look for LogicBlock items in
        # modes.
        self.machine.mode_controller.register_start_method(
            self._process_config,
            'logic_blocks')

        # Process game-wide (i.e. not in modes) logic blocks
        self.machine.events.add_handler('player_add_success',
                                        self._create_player_logic_blocks)
        self.machine.events.add_handler('player_turn_start',
                                        self.player_turn_start)
        self.machine.events.add_handler('player_turn_stop',
                                        self.player_turn_stop)

    def _create_player_logic_blocks(self, player: Player, **kwargs):
        """Create the game-wide logic blocks for this player.

        Args:
            player: The player object.
            **kwargs: Does nothing. Just here to allow this method to be called
                via an event handler.

        Note that this method is automatically added as a handler to the
        'player_add_success' event.
        """
        del kwargs
        player.logic_blocks = set()

        if 'logic_blocks' in self.machine.config:
            self._create_logic_blocks(
                config=self.machine.config['logic_blocks'],
                player=player)

    def player_turn_start(self, player, **kwargs):
        """Create blocks for current player.

        Args:
            player: Player object
        """
        del kwargs

        self.log.debug("Processing player_turn_start")

        for block in player.logic_blocks:
            block.create_control_events()

    def player_turn_stop(self, player: Player, **kwargs):
        """Remove blocks from current player.

        Args:
            player: Player pnkect
        """
        del kwargs

        self.log.debug("Player logic blocks: %s", player.logic_blocks)

        for block in player.logic_blocks.copy():
            # copy since each logic block will remove itself from the list
            # we're iterating over
            block.player_turn_stop()

    def _process_config(self, config: dict, priority: int=0, mode: Mode=None):
        del priority
        self.log.debug("Processing LogicBlock configuration.")

        blocks_added = self._create_logic_blocks(config=config,
                                                 player=self.machine.game.player)

        if mode:
            for block in blocks_added:
                block.create_control_events()

        return self._unload_logic_blocks, blocks_added

    def _create_logic_blocks(self, config: dict, player: Player):
        # config is localized for LogicBlock

        blocks_added = set()

        if 'counters' in config:
            for item in config['counters']:
                counter_block = Counter(self.machine, item, player,
                                        config['counters'][item])
                blocks_added.add(counter_block)

        if 'accruals' in config:
            for item in config['accruals']:
                accrual_block = Accrual(self.machine, item, player,
                                        config['accruals'][item])
                blocks_added.add(accrual_block)

        if 'sequences' in config:
            for item in config['sequences']:
                sequence_block = Sequence(self.machine, item, player,
                                          config['sequences'][item])
                blocks_added.add(sequence_block)

        # Enable any logic blocks that do not have specific enable events
        for block in blocks_added:
            if not block.config['enable_events']:
                block.log.debug("Enabling")
                block.enabled = True

        player.logic_blocks |= blocks_added

        return blocks_added

    def _unload_logic_blocks(self, block_list):
        self.log.debug("Unloading Logic Blocks")

        for block in block_list:
            block.unload()


class LogicBlock(object):

    """Parent class for each of the logic block classes."""

    def __init__(self, machine: MachineController, name: str, player: Player, config: dict):
        """Initialise logic block."""
        self.machine = machine
        self.name = name
        self.player = player
        self.handler_keys = set()
        self.log = None

        self.enabled = False
        self.completed = False

        # LogicBlocks are loaded multiple times and config_validator changes the config
        # therefore we have to copy the config
        config = copy.deepcopy(config)

        self.config = self.machine.config_validator.validate_config(
            'logic_blocks:{}'.format(self.config_section_name), config,
            base_spec='logic_blocks:common')

        if not self.config['events_when_complete']:
            self.config['events_when_complete'] = ['logicblock_' + self.name + '_complete']

        if not self.config['events_when_hit']:
            self.config['events_when_hit'] = ['logicblock_' + self.name + '_hit']

    @property
    @abc.abstractmethod
    def config_section_name(self):
        """Return config section name."""
        raise NotImplementedError("Please implement")

    def __repr__(self):
        """Return str representation of class."""
        return '<LogicBlock.{}>'.format(self.name)

    def create_control_events(self):
        """Create control events."""
        if self.enabled:
            # register all event handler if already enabled
            self.add_event_handlers()

        # Register for the events to enable, disable, and reset this LogicBlock
        for event in self.config['enable_events']:
            self.handler_keys.add(
                self.machine.events.add_handler(event, self.enable))

        for event in self.config['disable_events']:
            self.handler_keys.add(
                self.machine.events.add_handler(event, self.disable))

        for event in self.config['reset_events']:
            self.handler_keys.add(
                self.machine.events.add_handler(event, self.reset))

        for event in self.config['restart_events']:
            self.handler_keys.add(
                self.machine.events.add_handler(event, self.restart))

    def _remove_all_event_handlers(self):
        for key in self.handler_keys:
            self.machine.events.remove_handler_by_key(key)

        self.handler_keys = set()

    def player_turn_stop(self):
        """Remove block on player stop."""
        self._remove_all_event_handlers()

    def unload(self):
        """Unload block."""
        self.disable()
        self._remove_all_event_handlers()
        try:
            self.machine.game.player.logic_blocks.remove(self)
        except AttributeError:
            pass

    def enable(self, **kwargs):
        """Enable this logic block.

        Automatically called when one of the
        enable_event events is posted. Can also manually be called.
        """
        del kwargs
        self.log.debug("Enabling")
        self.enabled = True
        self.add_event_handlers()

    @abc.abstractmethod
    def add_event_handlers(self):
        """Add handler to advance block."""
        raise NotImplementedError("Not implemented")

    @abc.abstractmethod
    def hit(self, **kwargs):
        """Hit block."""
        raise NotImplementedError("Not implemented")

    def _post_hit_events(self, **kwargs):
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
        self.log.debug("Disabling")
        self.enabled = False
        self.machine.events.remove_handler(self.hit)

    def reset(self, **kwargs):
        """Reset the progress towards completion of this logic block.

        Automatically called when one of the reset_event events is called.
        Can also be manually called.
        """
        del kwargs
        self.completed = False
        self.log.debug("Resetting")

    def restart(self, **kwargs):
        """Restart this logic block by calling reset() and enable().

        Automatically called when one of the restart_event events is called.
        Can also be manually called.
        """
        del kwargs
        self.log.debug("Restarting (resetting then enabling)")
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

        self.log.debug("Complete")
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

    @property
    def config_section_name(self):
        """Return config section."""
        return 'counter'

    def __init__(self, machine: MachineController, name: str, player: Player, config: dict):
        """Initialise counter."""
        if 'events_when_hit' not in config:
            # for compatibility post the same default as previously for
            # counters. This one is deprecated.
            config['events_when_hit'] = ['counter_' + name + '_hit']

            # this is the one moving forward
            config['events_when_hit'].append('logicblock_' + name + '_hit')

        super().__init__(machine, name, player, config)

        self.log = logging.getLogger('Counter.' + name)
        self.log.debug("Creating Counter LogicBlock")

        self.delay = DelayManager(self.machine.delayRegistry)

        self.ignore_hits = False
        self.hit_value = -1

        if not self.config['player_variable']:
            self.config['player_variable'] = self.name + '_count'

        self.hit_value = self.config['count_interval']

        if self.config['direction'] == 'down' and self.hit_value > 0:
            self.hit_value *= -1
        elif self.config['direction'] == 'up' and self.hit_value < 0:
            self.hit_value *= -1

        if not self.config['persist_state'] or not self.player.is_player_var(self.config['player_variable']):
            self.player[self.config['player_variable']] = self.config['starting_count']

    def add_event_handlers(self):
        """Add handlers."""
        self.machine.events.remove_handler(self.hit)  # prevents multiples

        for event in self.config['count_events']:
            self.handler_keys.add(
                self.machine.events.add_handler(event, self.hit))

    def reset(self, **kwargs):
        """Reset the hit progress towards completion."""
        super().reset(**kwargs)
        self.player[self.config['player_variable']] = (
            self.config['starting_count'])

    def hit(self, **kwargs):
        """Increase the hit progress towards completion.

        Automatically called
        when one of the `count_events`s is posted. Can also manually be
        called.
        """
        del kwargs
        if not self.ignore_hits:
            self.player[self.config['player_variable']] += self.hit_value
            self.log.debug("Processing Count change. Total: %s",
                           self.player[self.config['player_variable']])

            self._post_hit_events(count=self.player[self.config['player_variable']])

            if self.config['count_complete_value'] is not None:

                if (self.config['direction'] == 'up' and
                        self.player[self.config['player_variable']] >= self.config['count_complete_value']):
                    self.complete()

                elif (self.config['direction'] == 'down' and
                        self.player[self.config['player_variable']] <= self.config['count_complete_value']):
                    self.complete()

            if self.config['multiple_hit_window']:
                self.log.debug("Beginning Ignore Hits")
                self.ignore_hits = True
                self.delay.add(name='ignore_hits_within_window',
                               ms=self.config['multiple_hit_window'],
                               callback=self.stop_ignoring_hits)

    def stop_ignoring_hits(self, **kwargs):
        """Cause the Counter to stop ignoring subsequent hits that occur within the 'multiple_hit_window'.

        Automatically called when the window time expires. Can safely be manually called.
        """
        del kwargs
        self.log.debug("Ending Ignore hits")
        self.ignore_hits = False


class Accrual(LogicBlock):

    """A type of LogicBlock which tracks many different events (steps) towards a goal.

    The steps are able to happen in any order.
    """

    @property
    def config_section_name(self):
        """Return config section."""
        return "accrual"

    def __init__(self, machine, name, player, config):
        """Initialise Accrual."""
        super().__init__(machine, name, player, config)

        self.log = logging.getLogger('Accrual.' + name)
        self.log.debug("Creating Accrual LogicBlock")

        # split events for each step
        self.config['events'][:] = [Util.string_to_list(x) for x in self.config['events']]

        if not self.config['player_variable']:
            self.config['player_variable'] = self.name + '_status'

        if not self.config['persist_state'] or not self.player[self.config['player_variable']]:
            self.player[self.config['player_variable']] = (
                [False] * len(self.config['events']))

    def add_event_handlers(self):
        """Add event handlers."""
        self.machine.events.remove_handler(self.hit)  # prevents multiples

        for entry_num in range(len(self.config['events'])):
            for event in self.config['events'][entry_num]:
                self.handler_keys.add(
                    self.machine.events.add_handler(event, self.hit,
                                                    step=entry_num))

    def reset(self, **kwargs):
        """Reset the hit progress towards completion."""
        super().reset(**kwargs)

        self.player[self.config['player_variable']] = (
            [False] * len(self.config['events']))
        self.log.debug("Status: %s",
                       self.player[self.config['player_variable']])

    def hit(self, step: int, **kwargs):
        """Increase the hit progress towards completion.

        Automatically called
        when one of the `count_events` is posted. Can also manually be
        called.

        Args:
            step: Integer of the step number (0 indexed) that was just hit.
        """
        del kwargs
        self.log.debug("Processing hit for step: %s", step)
        if not self.player[self.config['player_variable']][step]:
            self.player[self.config['player_variable']][step] = True
            self.log.debug("Status: %s",
                           self.player[self.config['player_variable']])
            self._post_hit_events(step=step)

        if (self.player[self.config['player_variable']].count(True) ==
                len(self.player[self.config['player_variable']])):
            self.complete()


class Sequence(LogicBlock):

    """A type of LogicBlock which tracks many different events (steps) towards a goal.

    The steps have to happen in order.
    """

    @property
    def config_section_name(self):
        """Return config section."""
        return "sequence"

    def __init__(self, machine: MachineController, name: str, player: Player, config: dict):
        """Initialise sequence."""
        super().__init__(machine, name, player, config)

        self.log = logging.getLogger('Sequence.' + name)
        self.log.debug("Creating Sequence LogicBlock")

        # split events for each step
        self.config['events'][:] = [Util.string_to_list(x) for x in self.config['events']]

        if not self.config['player_variable']:
            self.config['player_variable'] = self.name + '_step'

        if not self.config['persist_state']:
            self.player[self.config['player_variable']] = 0

    def add_event_handlers(self):
        """Add the handlers for the current step."""
        for event in (self.config['events']
                      [self.player[self.config['player_variable']]]):
            self.handler_keys.add(
                self.machine.events.add_handler(event, self.hit))

    def hit(self, **kwargs):
        """Increase the hit progress towards completion.

        Automatically called
        when one of the `count_events` is posted. Can also manually be
        called.
        """
        del kwargs
        self.log.debug("Processing Hit")
        # remove the event handlers for this step
        self.machine.events.remove_handler(self.hit)

        self.player[self.config['player_variable']] += 1
        self._post_hit_events(step=self.player[self.config['player_variable']])

        if self.player[self.config['player_variable']] >= (
                len(self.config['events'])):
            self.complete()
        else:
            # add the handlers for the new current step
            for event in (self.config['events']
                          [self.player[self.config['player_variable']]]):
                self.handler_keys.add(
                    self.machine.events.add_handler(event, self.hit))

    def reset(self, **kwargs):
        """Reset the sequence back to the first step."""
        super().reset(**kwargs)
        self.player[self.config['player_variable']] = 0

        # make sure we register the right handler
        if self.enabled:
            self.disable()
            self.enable()
