"""Contains the SwitchController class which is responsible for reading switch
states and posting events to the framework.

"""
# switch_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from collections import defaultdict
import time

from mpf.system.config import Config


class SwitchController(object):
    """Base class for the switch controller, which is responsible for receiving
    all switch activity in the machine and converting them into events.

    More info:
    http://missionpinball.com/docs/system-components/switch-controller/

    """

    log = logging.getLogger('SwitchController')

    def __init__(self, machine):
        self.machine = machine
        self.registered_switches = defaultdict(list)
        # Dictionary of switches and states that have been registered for
        # callbacks.

        self.active_timed_switches = defaultdict(list)
        # Dictionary of switches that are currently in a state counting ms
        # waiting to notify their handlers. In other words, this is the dict that
        # tracks current switches for things like "do foo() if switch bar is
        # active for 100ms."

        self.switches = {}
        # Dictionary which holds the master list of switches as well as their
        # current states. State here does factor in whether a switch is NO or NC,
        # so 1 = active and 0 = inactive.

        # register for events
        self.machine.events.add_handler('timer_tick', self._tick, 1000)
        self.machine.events.add_handler('machine_init_phase_2',
                                        self.initialize_hw_states,
                                        1000)
                                        # priority 1000 so this fires first

        self.machine.events.add_handler('machine_reset_phase_3',
                                        self.log_active_switches)

    def initialize_hw_states(self):
        """Reads and processes the hardware states of the physical switches.

        We can't do this in __init__() because we need the switch controller to
        be setup first before we set up the hw switches. This method is
        called via an event handler which listens for `machine_init_phase_2`.
        """

        start_active = list()

        if not self.machine.physical_hw:

            try:
                start_active = Config.string_to_list(self.machine.config
                    ['virtual platform start active switches'])
            except KeyError:
                pass

        self.log.debug("Syncing the logical and physical switch states.")
        for switch in self.machine.switches:

            if switch.name in start_active:
                switch.state = 1

            self.set_state(switch.name, switch.state, reset_time=True)

    def is_state(self, switch_name, state, ms=0):
        """Queries whether a switch is in a given state and (optionally)
        whether it has been in that state for the specified number of ms.

        Returns True if the switch_name has been in the state for the given
        number of ms. If ms is not specified, returns True if the switch
        is in the state regardless of how long it's been in that state.

        """

        if self.switches[switch_name]['state'] == state:
            if ms <= self.ms_since_change(switch_name):
                return True
            else:
                return False
        else:
            return False

    def is_active(self, switch_name, ms=None):
        """Queries whether a switch is active.

        Returns True if the current switch is active. If optional arg ms
        is passed, will only return true if switch has been active for that
        many ms.

        Note this method does consider whether a switch is NO or NC. So an NC
        switch will show as active if it is open, rather than closed.
        """

        return self.is_state(switch_name=switch_name,
                             state=1,
                             ms=ms)

    def is_inactive(self, switch_name, ms=None):
        """Queries whether a switch is inactive.

        Returns True if the current switch is inactive. If optional arg
        `ms` is passed, will only return true if switch has been inactive
        for that many ms.

        Note this method does consider whether a switch is NO or NC. So an NC
        switch will show as active if it is closed, rather than open.
        """

        return self.is_state(switch_name=switch_name,
                             state=0,
                             ms=ms)

    def ms_since_change(self, switch_name):
        """Returns the number of ms that have elapsed since this switch
        last changed state.
        """

        return (time.time() - self.switches[switch_name]['time']) * 1000.0

    def secs_since_change(self, switch_name):
        """Returns the number of ms that have elapsed since this switch
        last changed state.
        """

        return time.time() - self.switches[switch_name]['time']

    def set_state(self, switch_name, state=1, reset_time=False):
        """Sets the state of a switch."""

        if reset_time:
            timestamp = 1
        else:
            timestamp = time.time()

        self.switches.update({switch_name: {'state': state,
                                            'time': timestamp
                                            }
                              })

        # todo this method does not set the switch device's state. Either get
        # rid of it, or move the switch device settings from process_switch()
        # to here.

    def process_switch(self, name=None, state=1, logical=False, num=None,
                       obj=None):
        """Processes a new switch state change.

        This is the method that is called by the platform driver whenever a
        switch changes state. It's also used by the "other" modules that
        activate switches, including the keyboard and OSC interfaces.

        State 0 means the switch changed from active to inactive, and 1 means
        it changed from inactive to active. (The hardware & platform code
        handles NC versus NO switches and translates them to 'active' versus
        'inactive'.)

        Args:
            name: The string name of the switch. This is optional if you specify
                the switch via the 'num' or 'obj' parameters.
            state: The state of the switch you're processing, 1 is active, 0 is
                inactive.
            logical: Boolean which specifies whether the 'state' argument
                represents the "physical" or "logical" state of the switch. If
                True, a 1 means this switch is active and a 0 means it's
                inactive, regardless of the NC/NO configuration of the switch.
                If False, then the state paramenter passed will be inverted if
                the switch is configured to be an 'NC' type. Typically the
                hardware will send switch states in their raw (logical=False)
                states, but other interfaces like the keyboard and OSC will use
                logical=True.
            num: The hardware number of the switch.
            obj: The switch object.

        Note that there are three different paramter options to specify the
        switch: 'name', 'num', and 'obj'. You only need to pass one of them.

        """

        # Find the switch name
        # todo find a better way to do this ...
        if num is not None:
            for switch in self.machine.switches:
                if switch.number == num:
                    name = switch.name
                    break

        elif obj:
            name = obj.name

        if name and not self.machine.switches[name]:
            self.log.warning("Received process_switch command but can't find "
                              "the switch. Name: %s, Num: %s, Obj: %s", name,
                              num, obj)
            # Removed the Exception below since it's kind of annoying to have
            # MPF halt every time a non-configured switch is hit.
            #raise Exception("Received process_switch command but can't find the"
            #                " switch. Name: %s, Num: %s, Obj: %s", name, num,
            #                obj)

        # flip the logical & physical states for NC switches
        hw_state = state
        if self.machine.switches[name].type == 'NC':
            if logical:  # NC + logical means hw_state is opposite of state
                hw_state = hw_state ^ 1
            else:
                # NC w/o logical (i.e. hardware state was sent) means logical
                # state is the opposite
                state = state ^ 1

        # update the switch device
        self.machine.switches[name].state = state
        self.machine.switches[name].hw_state = hw_state

        # if the switch is already in this state, then abort
        if self.switches[name]['state'] == state:
            # todo log this as potential hw error??
            self.log.warning("Received duplicate switch state. Switch: %s, "
                             "State: %s", name, state)
            return

        self.log.info("<<<<< switch: %s, State:%s >>>>>", name, state)

        # Update the switch controller's logical state for this switch
        self.set_state(name, state)

        # Combine name & state so we can look it up
        switch_key = str(name) + '-' + str(state)

        # Do we have any registered handlers for this switch/state combo?
        if switch_key in self.registered_switches:
            for entry in self.registered_switches[switch_key]:  # generator?
                # Found an entry.

                if entry['ms']:
                    # This entry is for a timed switch, so add it to our
                    # active timed switch list
                    key = time.time() + (entry['ms'] / 1000.0)
                    value = {'switch_action': str(name) + '-' + str(state),
                             'callback': entry['callback'],
                             'switch_name': name,
                             'state': state,
                             'ms': entry['ms'],
                             'return_info': entry['return_info']}
                    self.active_timed_switches[key].append(value)
                    self.log.debug("Found timed switch handler for k/v %s / %s",
                                   key, value)
                else:
                    # This entry doesn't have a timed delay, so do the action
                    # now
                    if entry['return_info']:

                        entry['callback'](switch_name=name, state=state, ms=0)
                    else:
                        entry['callback']()

                # todo need to add args and kwargs support to callback

        # now check if the opposite state is in the active timed switches list
        # if so, remove it
        for k, v, in self.active_timed_switches.items():
            # using items() instead of iteritems() since we might want to
            # delete while iterating

            for item in v:
                if item['switch_action'] == str(name) + '-' + str(state ^ 1):
                    # ^1 in above line invertes the state
                    del self.active_timed_switches[k]

        self._post_switch_events(name, state)

    def add_switch_handler(self, switch_name, callback, state=1, ms=0,
                           return_info=False):
        """Register a handler to take action on some switch event.

        Args:

            switch_name: String name of the switch you're adding this handler
                for.

            callback: The method you want called when this switch handler fires.

            state: Integer of the state transition you want to callback to be
                triggered on. Default is 1 which means it's called when the
                switch goes from inactive to active, but you can also use 0
                which means your callback will be called when the switch becomes
                inactive

            ms: Integer. If you specify a 'ms' parameter, the handler won't be
                called until the witch is in that state for that many
                milliseconds (rounded up to the nearst machine timer tick).

            return_info: If True, the switch controller will pass the
                parameters of the switch handler as arguments to the callback,
                including switch_name, state, and ms. If False (default), it
                just calls the callback with no parameters.


        You can mix & match entries for the same switch here.
        """
        # todo add support for other parameters to the callback?

        self.log.debug("Registering switch handler: %s, %s, state: %s, ms: %s"
                       ", info: %s", switch_name, callback, state, ms,
                       return_info)

        entry_val = {'ms': ms, 'callback': callback,
                     'return_info': return_info}
        entry_key = str(switch_name) + '-' + str(state)

        self.registered_switches[entry_key].append(entry_val)

        # If the switch handler that was just registered has a delay (i.e. ms>0,
        # then let's see if the switch is currently in the state that the
        # handler was registered for. If so, and if the switch has been in this
        # state for less time than the ms registered, then we need to add this
        # switch to our active_timed_switches list so this handler is called
        # when this switch's active time expires. (in other words, we're
        # catching delayed switches that were in progress when this handler was
        # registered.

        if ms:  # only do this for handlers that have delays
            if state == 1:
                if self.is_active(switch_name, 0) and (
                        self.ms_since_change(switch_name) < ms):
                    # figure out when this handler should fire based on the
                    # switch's original activation time.
                    key = (time.time() + ((ms - self.ms_since_change(switch_name))
                                                                   / 1000.0))
                    value = {'switch_action': entry_key,
                             'callback': callback,
                             'switch_name': switch_name,
                             'state': state,
                             'ms': ms,
                             'return_info': return_info}
                    self.active_timed_switches[key].append(value)
            elif state == 0:
                if self.is_inactive(switch_name, 0) and (
                        self.ms_since_change(switch_name) < ms):

                    key = (time.time() + ((ms - self.ms_since_change(switch_name))
                                                                   / 1000.0))
                    value = {'switch_action': entry_key,
                             'callback': callback,
                             'switch_name': switch_name,
                             'state': state,
                             'ms': ms,
                             'return_info': return_info}
                    self.active_timed_switches[key].append(value)

        # Return the args we used to setup this handler for easy removal later
        return {'switch_name': switch_name,
                'callback': callback,
                'state': state,
                'ms': ms}

    def remove_switch_handler(self, switch_name, callback, state=1, ms=0):
        """Removes a registered switch handler.

        Currently this only works if you specify everything exactly as you set
        it up. (Except for return_info, which doesn't matter if true or false, it
        will remove either / both."""

        self.log.debug("Removing switch handler. Switch: %s, State: %s, ms: %s",
                      switch_name, state, ms)

        # Try first with return_info: False
        entry_val = {'ms': ms, 'callback': callback, 'return_info': False}
        entry_key = str(switch_name) + '-' + str(state)

        if entry_val in self.registered_switches[entry_key]:
            self.registered_switches[entry_key].remove(entry_val)

        # And try again with return_info: True
        entry_val = {'ms': ms, 'callback': callback, 'return_info': True}
        if entry_val in self.registered_switches[entry_key]:
            self.registered_switches[entry_key].remove(entry_val)

    def log_active_switches(self):
        """Writes out entries to the log file of all switches that are
        currently active.

        This is used to set the "initial" switch states of standalone testing
        tools, like our log file playback utility, but it might be useful in
        other scenarios when weird things are happening.

        This method dumps these events with logging level "INFO."

        """

        self.log.info("Dumping current active switches")

        for k, v in self.switches.iteritems():
            if v['state']:
                self.log.info("Active Switch|%s",k)

    def _post_switch_events(self, switch_name, state):
        """Posts the game events based on this switch changing state. """

        # post events based on the switch tags

        # the following events all fire the moment a switch goes active
        if state == 1:

            for tag in self.machine.switches[switch_name].tags:

                self.machine.events.post('sw_' + tag)

        # the following events all fire the moment a switch becomes inactive
        elif state == 0:
            pass

    def _tick(self):
        """Called once per machine tick.

        Checks the current list of active timed switches to see if it's
        time to take action on any of them. If so, does the callback and then
        removes that entry from the list.

        """

        for k in self.active_timed_switches.keys():
            if k <= time.time():  # change to generator?
                for entry in self.active_timed_switches[k]:
                    self.log.debug("Processing timed switch handler. Switch: %s "
                                  " State: %s, ms: %s", entry['switch_name'],
                                  entry['state'], entry['ms'])
                    if entry['return_info']:
                        entry['callback'](switch_name=entry['switch_name'],
                                         state=entry['state'],
                                         ms=entry['ms'])
                    else:
                        entry['callback']()
                del self.active_timed_switches[k]

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
