"""MPF plugin which implements Logic Blocks"""

# logic_blocks.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging

from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing


def preload_check(machine):
    return True


class LogicBlocks(object):
    """LogicBlock Manager."""

    def __init__(self, machine):

        self.log = logging.getLogger('LogicBlocks Manager')

        self.machine = machine

        # Tell the mode controller that it should look for LogicBlock items in
        # modes.
        self.machine.modes.register_start_method(self.process_config,
                                                 'LogicBlocks')

        # If there's a base-level logic block config, process them when the game
        # starts
        self.machine.events.add_handler('player_add_success',
                                        self.create_player_logic_blocks)
        self.machine.events.add_handler('player_turn_start',
                                        self.player_turn_start)
        self.machine.events.add_handler('player_turn_stop',
                                        self.player_turn_stop)

    def create_player_logic_blocks(self, player, **kwargs):

        player.logic_blocks = set()

        if 'LogicBlocks' in self.machine.config:
            self.create_logic_blocks(config=self.machine.config['LogicBlocks'],
                                     player=player,
                                     enable=False)

    def player_turn_start(self, player):

        self.log.debug("Processing player_turn_start")

        for block in player.logic_blocks:
            block.player_turn_start()

    def player_turn_stop(self, player):

        self.log.debug("Processing player_turn_stop")
        self.log.debug("Player logic blocks: %s", player.logic_blocks)

        for block in player.logic_blocks.copy():
            # copy since each logic block will remove itself from the list
            # we're iterating over
            block.player_turn_stop()

    def process_config(self, config, priority=0, mode=None, enable=True):
        self.log.debug("Processing LogicBlock configuration.")

        blocks_added = self.create_logic_blocks(config=config,
                                                player=self.machine.game.player,
                                                enable=enable)

        return self.unload_logic_blocks, blocks_added

    def create_logic_blocks(self, config, player, enable=True):
        # config is localized for LogicBlock

        blocks_added = set()

        if 'Counters' in config:
            for item in config['Counters']:
                block = Counter(self.machine, item, player,
                                   config['Counters'][item])
                blocks_added.add(block)

        if 'Accruals' in config:
            for item in config['Accruals']:
                block = Accrual(self.machine, item, player,
                                config['Accruals'][item])
                blocks_added.add(block)

        if 'Sequences' in config:
            for item in config['Sequences']:
                block = Sequence(self.machine, item, player,
                                 config['Accruals'][item])
                blocks_added.add(block)

        # Enable any logic blocks that do not have specific enable events
        if enable:
            for block in blocks_added:
                if not block.config['enable_events']:
                    block.enable()

        player.logic_blocks |= blocks_added

        return blocks_added

    def unload_logic_blocks(self, block_list):

        self.log.debug("Unloading Logic Blocks")

        for block in block_list:
            block.unload()


class LogicBlock(object):
    """Parent class for each of the logic block classes."""

    def __init__(self, machine, name, player, config):

        self.machine = machine
        self.name = name
        self.player = player
        self.config = config
        self.handler_keys = set()

        self.enabled = False

        if 'enable_events' not in self.config:
            self.config['enable_events'] = list()
        else:
            self.config['enable_events'] = self.machine.string_to_list(
                self.config['enable_events'])

        if 'disable_events' not in self.config:
            self.config['disable_events'] = list()
        else:
            self.config['disable_events'] = self.machine.string_to_list(
                self.config['disable_events'])

        if 'reset_events' not in self.config:
            self.config['reset_events'] = list()
        else:
            self.config['reset_events'] = self.machine.string_to_list(
                self.config['reset_events'])

        if 'events_when_complete' not in self.config:
            self.config['events_when_complete'] = ([
                'logicblock_' + self.name + '_complete'])
        else:
            self.config['events_when_complete'] = self.machine.string_to_list(
                self.config['events_when_complete'])

        if 'restart_on_complete' not in self.config:
            self.config['restart_on_complete'] = False

        if 'disable_on_complete' not in self.config:
            self.config['disable_on_complete'] = True

        if 'reset_each_ball' in self.config and self.config['reset_each_ball']:
            if 'ball_starting' not in self.config['reset_events']:
                self.config['reset_events'].append('ball_starting')

    def __str__(self):
        return self.name

    def player_turn_start(self):

        self.log.debug("in player_turn_start")

        # If this logic block is enabled, keep it enabled
        # If it's not enabled, enable it if there are no other enable events
        if not self.enabled and not self.config['enable_events']:
            self.enable()

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

    def remove_all_event_handlers(self):
        for key in self.handler_keys:
            self.machine.events.remove_handler_by_key(key)

        self.handler_keys = set()

    def player_turn_stop(self):
        self.remove_all_event_handlers()

    def unload(self):
        self.disable()
        self.remove_all_event_handlers()
        self.machine.game.player.logic_blocks.remove(self)

    def enable(self, **kwargs):
        """Enables this logic block. Automatically called when one of the
        enable_event events is posted. Can also manually be called.
        """
        self.log.debug("Enabling")
        self.enabled = True

    def disable(self, **kwargs):
        """Disables this logic block. Automatically called when one of the
        disable_event events is posted. Can also manually be called.
        """
        self.log.debug("Disabling")
        self.enabled = False
        self.machine.events.remove_handler(self.hit)

    def reset(self, **kwargs):
        """Resets the progress towards completion of this logic block.
        Automatically called when one of the reset_event events is called.
        Can also be manually called.
        """
        self.log.debug("Resetting")

    def complete(self):
        self.log.debug("Complete")
        if self.config['events_when_complete']:
            for event in self.config['events_when_complete']:
                self.machine.events.post(event)

        if self.config['restart_on_complete']:
            self.reset()
            self.enable()

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

    # todo settle time

    def __init__(self, machine, name, player, config):
        self.log = logging.getLogger('Counter.' + name)
        self.log.debug("Creating Counter LogicBlock")

        super(Counter, self).__init__(machine, name, player, config)

        self.delay = DelayManager()

        #self.num_hits = 0
        self.ignore_hits = False
        self.hit_value = -1

        if 'count_events' not in self.config:
            self.log.critical("No count_events found for this logic block")
            raise Exception()
        else:
            self.config['count_events'] = self.machine.string_to_list(
                self.config['count_events'])

        if 'event_when_hit' not in self.config:
            self.config['event_when_hit'] = ('counter_' + self.name +
                                             '_hit')

        if 'count_complete_value' not in self.config:
            self.config['count_complete_value'] = None

        if 'multiple_hit_window' not in self.config:
            self.config['multiple_hit_window'] = None
        else:
            self.config['multiple_hit_window'] = Timing.string_to_ms(
                self.config['multiple_hit_window'])

        if 'player_variable' not in self.config:
            self.config['player_variable'] = self.name + '_count'

        if 'count_interval' not in self.config:
            self.config['count_interval'] = 1

        self.hit_value = self.config['count_interval']

        if 'direction' not in self.config:
            self.config['direction'] = 'up'

        if self.config['direction'] == 'down' and self.hit_value > 0:
            self.hit_value *= -1
        elif self.config['direction'] == 'up' and self.hit_value < 0:
            self.hit_value *= -1

        if 'starting_count' not in self.config:
            self.config['starting_count'] = 0

        self.player[self.config['player_variable']] = (
            self.config['starting_count'])

    def enable(self, **kwargs):
        """Enables this counter. Automatically called when one of the
        'enable_event's is posted. Can also manually be called.
        """

        super(Counter, self).enable(**kwargs)
        self.machine.events.remove_handler(self.hit)  # prevents multiples

        self.enabled = True

        for event in self.config['count_events']:
            self.machine.events.add_handler(event, self.hit)

    def reset(self, **kwargs):
        """Resets the hit progress towards completion"""
        super(Counter, self).reset(**kwargs)
        self.player[self.config['player_variable']] = (
            self.config['starting_count'])

    def hit(self, **kwargs):
        """Increases the hit progress towards completion. Automatically called
        when one of the `count_events`s is posted. Can also manually be
        called.
        """
        if not self.ignore_hits:
            self.player[self.config['player_variable']] += self.hit_value
            self.log.debug("Processing Count change. Total: %s",
                           self.player[self.config['player_variable']])

            if self.config['count_complete_value'] is not None:

                if (self.config['direction'] == 'up' and
                        self.player[self.config['player_variable']] >=
                        self.config['count_complete_value']):
                    self.complete()

                elif (self.config['direction'] == 'down' and
                        self.player[self.config['player_variable']] <=
                        self.config['count_complete_value']):
                    self.complete()

            if self.config['event_when_hit']:
                self.machine.events.post(self.config['event_when_hit'],
                    count=self.player[self.config['player_variable']])

            if self.config['multiple_hit_window']:
                self.log.debug("Beginning Ignore Hits")
                self.ignore_hits = True
                self.delay.add('ignore_hits_within_window',
                               self.config['multiple_hit_window'],
                               self.stop_ignoring_hits)

    def stop_ignoring_hits(self, **kwargs):
        """Causes the Counter to stop ignoring subsequent hits that occur
        within the 'multiple_hit_window'. Automatically called when the window
        time expires. Can safely be manually called.
        """
        self.log.debug("Ending Ignore hits")
        self.ignore_hits = False


class Accrual(LogicBlock):
    """A type of LogicBlock which tracks many different events (steps) towards
    a goal, with the steps being able to happen in any order.
    """

    def __init__(self, machine, name, player, config):
        self.log = logging.getLogger('Accrual.' + name)
        self.log.debug("Creating Accrual LogicBlock")

        super(Accrual, self).__init__(machine, name, player, config)

        #self.status = list()

        # make sure the events entry is a list of lists
        if 'events' in self.config and type(self.config['events']) is list:
            for entry_num in range(len(self.config['events'])):
                self.config['events'][entry_num] = (
                    self.machine.string_to_list(self.config['events']
                                                [entry_num]))
        elif 'events' in self.config and type(self.config['events']) is str:
            temp_list = self.machine.string_to_list(self.config['events'])
            self.config['events'] = list()
            for entry_num in temp_list:
                self.config['events'].append([entry_num])

        if 'player_variable' not in self.config:
            self.config['player_variable'] = self.name + '_status'

        # populate status list
        self.player[self.config['player_variable']] = [False] * len(self.config['events'])

    def enable(self, **kwargs):
        """Enables this accrual. Automatically called when one of the
        'enable_events' is posted. Can also manually be called.
        """
        super(Accrual, self).enable(**kwargs)
        self.machine.events.remove_handler(self.hit)  # prevents multiples

        for entry_num in range(len(self.config['events'])):
            for event in self.config['events'][entry_num]:
                self.machine.events.add_handler(event, self.hit,
                                                step=entry_num)

    def reset(self, **kwargs):
        """Resets the hit progress towards completion"""
        super(Accrual, self).reset(**kwargs)

        self.player[self.config['player_variable']] = [False] * len(self.config['events'])
        self.log.debug("Status: %s", self.player[self.config['player_variable']])

    def hit(self, step, **kwargs):
        """Increases the hit progress towards completion. Automatically called
        when one of the `count_events` is posted. Can also manually be
        called.
        """
        self.log.debug("Processing hit for step: %s", step)
        self.player[self.config['player_variable']][step] = True
        self.log.debug("Status: %s", self.player[self.config['player_variable']])

        if self.player[self.config['player_variable']].count(True) == len(self.player[self.config['player_variable']]):
            self.complete()


class Sequence(LogicBlock):
    """A type of LogicBlock which tracks many different events (steps) towards
    a goal, with the steps having to happen in order.
    """

    def __init__(self, machine, name, player, config):
        self.log = logging.getLogger('Sequence.' + name)
        self.log.debug("Creating Sequence LogicBlock")

        super(Sequence, self).__init__(machine, name, player, config)

        #self.current_step = 1

        # make sure the events entry is a list of lists
        if 'events' in self.config and type(self.config['events']) is list:
            for entry_num in range(len(self.config['events'])):
                self.config['events'][entry_num] = (
                    self.machine.string_to_list(self.config['events']
                                                [entry_num]))

        if 'player_variable' not in self.config:
                self.config['player_variable'] = self.name + '_step'

        self.player[self.config['player_variable']] = 1

    def enable(self, step=0, **kwargs):
        """Enables this Sequence. Automatically called when one of the
        'enable_events' is posted. Can also manually be called.
        """
        self.log.debug("Enabling")
        if step:
            self.player[self.config['player_variable']] = step

        if self.player[self.config['player_variable']] >= len(self.config['events']):
            # hmm.. we're enabling, but we're done. So now what?
            self.log.warning("Received request to enable at step %s, but this "
                             " Sequence only has %s step(s). Marking complete",
                             step, len(self.config['events']))
            self.complete()  # I guess we just complete?
            return

        self.enabled = True
        # add the handlers for the current step
        for event in self.config['events'][self.player[self.config['player_variable']]]:
            self.machine.events.add_handler(event, self.hit)

    def hit(self, **kwargs):
        """Increases the hit progress towards completion. Automatically called
        when one of the `count_events` is posted. Can also manually be
        called.
        """
        self.log.debug("Processing Hit")
        # remove the event handlers for this step
        self.machine.events.remove_handler(self.hit)

        self.player[self.config['player_variable']] += 1

        if self.player[self.config['player_variable']] >= len(self.config['events']):
            self.complete()
        else:
            # add the handlers for the new current step
            for event in self.config['events'][self.player[self.config['player_variable']]]:
                self.machine.events.add_handler(event, self.hit)


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
