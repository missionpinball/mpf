"""Switch controller which handles all switches in MPF.

Contains the SwitchController class which is responsible for reading switch
states and posting events to the framework.
"""

import logging
from collections import defaultdict, namedtuple
import asyncio
from functools import partial
from typing import Any, Callable, Dict, List, Tuple

from mpf.core.platform import SwitchPlatform

from mpf.core.machine import MachineController
from mpf.core.mpf_controller import MpfController
from mpf.devices.switch import Switch

MonitoredSwitchChange = namedtuple("MonitoredSwitchChange", ["name", "label", "platform", "num", "state"])
SwitchHandler = namedtuple("SwitchHandler", ["switch_name", "callback", "state", "ms"])
TimedSwitchHandler = namedtuple("TimedSwitchHandler", ["callback", 'switch_name', 'state', 'ms'])


class RegisteredSwitch:

    """Registered switch handler."""

    __slots__ = ["ms", "callback", "cancelled"]

    def __init__(self, ms, callback):
        """Initialise registered switch."""
        self.ms = ms
        self.callback = callback
        self.cancelled = False


class SwitchController(MpfController):

    """Tracks all switches in the machine, receives switch activity, and converts switch changes into events."""

    config_name = "switch_controller"

    __slots__ = ["registered_switches", "_timed_switch_handler_delay", "active_timed_switches",
                 "_switch_lookup", "monitors", "_initialised"]

    def __init__(self, machine: MachineController) -> None:
        """Initialise switch controller."""
        super().__init__(machine)
        self.registered_switches = dict()                       # type: Dict[Switch, List[List[RegisteredSwitch]]]
        # Dictionary of switches and states that have been registered for
        # callbacks.

        self._timed_switch_handler_delay = dict()               # type: Any

        self.active_timed_switches = defaultdict(list)          # type: Dict[float, List[TimedSwitchHandler]]
        # Dictionary of switches that are currently in a state counting ms
        # waiting to notify their handlers. In other words, this is the dict
        # that tracks current switches for things like "do foo() if switch bar
        # is active for 100ms."

        self._switch_lookup = dict()                            # type: Dict[Tuple[str, SwitchPlatform], Switch]
        # Lookup table for switch + platform to an Switch object

        # register for events
        self.machine.events.add_async_handler('init_phase_2', self._initialize_switches, 1000)
        # priority 1000 so this fires first

        self.monitors = list()      # type: List[Callable[[MonitoredSwitchChange], None]]

        # to detect early switch changes before init
        self._initialised = False

    def register_switch(self, switch: Switch):
        """Add the name of a switch to the switch controller for tracking.

        Args:
            switch: Switch object to add
        """
        self.registered_switches[switch] = [list(), list()]

    @asyncio.coroutine
    def _initialize_switches(self, **kwargs):
        del kwargs
        yield from self.update_switches_from_hw()

        for switch in self.machine.switches.values():
            # Populate self.switches
            self.set_state(switch.name, switch.state, reset_time=True)
            self._switch_lookup[(switch.hw_switch.number, switch.platform)] = switch

        self._initialised = True

        self.log_active_switches()

    @asyncio.coroutine
    def update_switches_from_hw(self):
        """Update the states of all the switches be re-reading the states from the hardware platform.

        This method works silently and does not post any events if any switches
        changed state.
        """
        # create a list of hw switch numbers, platforms, and switch objects
        platforms = set()
        switches = set()  # (switch_object, number)

        for switch in self.machine.switches:
            platforms.add(switch.platform)
            switches.add((switch, switch.hw_switch.number))

        for platform in platforms:
            switch_states = yield from platform.get_hw_switch_states()

            for switch, number in switches:
                # if two platforms have the same number choose the right switch
                if switch.platform != platform:
                    continue
                try:
                    switch.state = switch_states[number] ^ switch.invert
                except (IndexError, KeyError):
                    raise AssertionError("Missing switch {} in update from hw.  Update from HW: {}, switches: {}".
                                         format(number, switch_states, switches))

    def verify_switches(self) -> bool:
        """Verify that switches states match the hardware.

        Loops through all the switches and queries their hardware states via
        their platform interfaces and then compares that to the state that MPF
        thinks the switches are in.

        Throws logging warnings if anything doesn't match.

        This method is notification only. It doesn't fix anything.
        """
        current_states = dict()

        for switch in self.machine.switches.values():
            current_states[switch] = switch.state

        self.update_switches_from_hw()

        ok = True

        for switch in self.machine.switches.values():
            if switch.state != current_states[switch]:  # pragma: no cover
                ok = False
                self.warning_log("Switch State Error! Switch: %s, HW State: "
                                 "%s, MPF State: %s", switch.name,
                                 current_states[switch],
                                 switch.state)

        return ok

    def is_state(self, switch_name, state, ms=0.0):
        """Check if switch is in state.

        Query whether a switch is in a given state and (optionally)
        whether it has been in that state for the specified number of ms.

        Args:
            switch_name: String name of the switch to check.
            state: Bool of the state to check. True is active and False is
                inactive.
            ms: Milliseconds that the switch has been in that state. If this
                is non-zero, then this method will only return True if the
                switch has been in that state for at least the number of ms
                specified.

        Returns: True if the switch_name has been in the state for the given
            number of ms. If ms is not specified, returns True if the switch
            is in the state regardless of how long it's been in that state.
        """
        if not self._initialised:
            raise AssertionError("Cannot read switch state before init_phase_3")
        if not ms:
            ms = 0.0

        return self.machine.switches[switch_name].state == state and ms <= self.ms_since_change(switch_name)

    def is_active(self, switch_name, ms=None):
        """Query whether a switch is active.

        Args:
            switch_name: String name of the switch to check.
            ms: Milliseconds that the switch has been active. If this
                is non-zero, then this method will only return True if the
                switch has been in that state for at least the number of ms
                specified.

        Returns: True if the switch_name has been active for the given
            number of ms. If ms is not specified, returns True if the switch
            is in the state regardless of how long it's been in that state.
        """
        return self.is_state(switch_name=switch_name,
                             state=1,
                             ms=ms)

    def is_inactive(self, switch_name, ms=None):
        """Query whether a switch is inactive.

        Args:
            switch_name: String name of the switch to check.
            ms: Milliseconds that the switch has been inactive. If this
                is non-zero, then this method will only return True if the
                switch has been in that state for at least the number of ms
                specified.

        Returns: True if the switch_name has been inactive for the given
            number of ms. If ms is not specified, returns True if the switch
            is in the state regardless of how long it's been in that state.
        """
        return self.is_state(switch_name=switch_name,
                             state=0,
                             ms=ms)

    def ms_since_change(self, switch_name):
        """Return the number of ms that have elapsed since this switch last changed state.

        Args:
            switch_name: String name of the switch to check.

        Returns:
            Integer of milliseconds.
        """
        return round((self.machine.clock.get_time() - self.machine.switches[switch_name].last_change) * 1000.0, 0)

    def set_state(self, switch_name, state=1, reset_time=False):
        """Set the state of a switch.

        Note that since this method just sets the logical state of the switch,
        weird things can happen if the state diverges from the physical state
        of the switch.

        It's mainly used with the virtual platforms to set the initial states
        of switches on MPF boot.

        Args:
            switch_name: String name of the switch to set.
            state: Logical state to set. 0 is inactive and 1 is active.
            reset_time: Sets the timestamp of the change to -100000 which
                indicates that this switch was in this state when the machine
                was powered on and therefore the various timed switch
                handlers will not be triggered.

        """
        if reset_time:
            timestamp = -100000     # clock can be 0 at start
        else:
            timestamp = self.machine.clock.get_time()

        switch = self.machine.switches[switch_name]
        switch.state = state
        switch.last_change = timestamp

    def process_switch_by_num(self, num, state, platform, logical=False):
        """Process a switch state change by switch number.

        Args:
            num: The switch number (based on the platform number) for the
                switch you're setting.
            state: The state to set, either 0 or 1.
            platform: The platform this switch is on.
            logical: Whether the state you're setting is the logical or
                physical state of the switch. If a switch is NO (normally
                open), then the logical and physical states will be the same.
                NC (normally closed) switches will have physical and
                logical states that are inverted from each other.

        """
        if not self._initialised:
            raise AssertionError("Got early switch change for switch {} to state {}. platform: {}".format(
                num, state, platform))
        switch = self._switch_lookup.get((num, platform), None)
        if switch:
            self.process_switch_obj(switch, state, logical)
        else:
            if self._debug_to_console or self._debug_to_file:
                self.debug_log("Unknown switch %s change to state %s on platform %s", num, state, platform)
            # if the switch is not configured still trigger the monitor
            for monitor in self.monitors:
                monitor(MonitoredSwitchChange(name=str(num), label="{}-{}".format(str(platform), str(num)),
                                              platform=platform, num=str(num), state=state))

    def process_switch(self, name, state, logical=False):
        """Process a new switch state change for a switch by name.

        This is the method that is called by the platform driver whenever a
        switch changes state. It's also used by the "other" modules that
        activate switches, including the keyboard and OSC interfaces.

        State 0 means the switch changed from active to inactive, and 1 means
        it changed from inactive to active. (The hardware & platform code
        handles NC versus NO switches and translates them to 'active' versus
        'inactive'.)

        Args:
            name: The string name of the switch.
            state: Boolean or int of state of the switch you're processing,
                True/1 is active, False/0 is inactive.
            logical: Boolean which specifies whether the 'state' argument
                represents the "physical" or "logical" state of the switch. If
                True, a 1 means this switch is active and a 0 means it's
                inactive, regardless of the NC/NO configuration of the switch.
                If False, then the state parameter passed will be inverted if
                the switch is configured to be an 'NC' type. Typically the
                hardware will send switch states in their raw (logical=False)
                states, but other interfaces like the keyboard and OSC will use
                logical=True.

        """
        self.debug_log("Processing switch. Name: %s, state: %s, logical: %s,", name, state, logical)

        try:
            obj = self.machine.switches[name]
        except KeyError:    # pragma: no cover
            raise AssertionError("Cannot process switch \"" + name + "\" as "
                                 "this is not a valid switch name.")

        self.process_switch_obj(obj, state, logical)

    def process_switch_obj(self, obj: Switch, state, logical):
        """Process a new switch state change for a switch by name.

        Args:
            obj: The switch object.
            state: Boolean or int of state of the switch you're processing,
                True/1 is active, False/0 is inactive.
            logical: Boolean which specifies whether the 'state' argument
                represents the "physical" or "logical" state of the switch. If
                True, a 1 means this switch is active and a 0 means it's
                inactive, regardless of the NC/NO configuration of the switch.
                If False, then the state parameter passed will be inverted if
                the switch is configured to be an 'NC' type. Typically the
                hardware will send switch states in their raw (logical=False)
                states, but other interfaces like the keyboard and OSC will use
                logical=True.

        This is the method that is called by the platform driver whenever a
        switch changes state. It's also used by the "other" modules that
        activate switches, including the keyboard and OSC interfaces.

        State 0 means the switch changed from active to inactive, and 1 means
        it changed from inactive to active. (The hardware & platform code
        handles NC versus NO switches and translates them to 'active' versus
        'inactive'.)
        """
        # We need int, but this lets it come in as boolean also
        if state:
            state = 1
        else:
            state = 0

        # flip the logical & physical states for NC switches
        hw_state = state

        if obj.invert:
            if logical:  # NC + logical means hw_state is opposite of state
                hw_state ^= 1
            else:
                # NC w/o logical (i.e. hardware state was sent) means logical
                # state is the opposite
                state ^= 1

        # if the switch is already in this state, then abort
        if obj.state == state:
            if not self.machine.options['production']:
                self.warning_log(
                    "Received duplicate switch state %s for switch %s from the platform interface.",
                    state, obj.name, error_no=1)
            return

        # Update the hardware state since we always want this to match real hw
        obj.hw_state = hw_state
        # update the switch device
        obj.state = state
        obj.last_change = self.machine.clock.get_time()

        if state:
            self.info_log("<<<<<<< '%s' active >>>>>>>", obj.name)
        else:
            self.info_log("<<<<<<< '%s' inactive >>>>>>>", obj.name)

        self._call_handlers(obj, state)

        self._cancel_timed_handlers(obj.name, state)

        for monitor in self.monitors:
            monitor(MonitoredSwitchChange(name=obj.name, label=obj.label, platform=obj.platform,
                                          num=obj.hw_switch.number, state=state))

    def wait_for_switch(self, switch_name: str, state: int = 1, only_on_change=True, ms=0):
        """Wait for a switch to change into a state.

        Args:
            switch_name: String name of the switch to wait for.
            state: The state to wait for. 0 = inactive, 1 = active, 2 = opposite to current.
            only_on_change: Bool which controls whether this wait will be
                triggered now if the switch is already in the state, or
                whether it will wait until the switch changes into that state.
            ms: How long the switch needs to be in the new state to trigger
                the wait.

        """
        return self.wait_for_any_switch([switch_name], state, only_on_change, ms)

    def wait_for_any_switch(self, switch_names: List[str], state: int = 1, only_on_change=True, ms=0):
        """Wait for the first switch in the list to change into state.

        Args:
            switch_names: Iterable of strings of switch names. Whichever switch changes first will trigger this wait.
            state: The state to wait for. 0 = inactive, 1 = active, 2 = opposite to current.
            only_on_change: Bool which controls whether this wait will be
                triggered now if the switch is already in the state, or
                whether it will wait until the switch changes into that state.
            ms: How long the switch needs to be in the new state to trigger
                the wait.

        """
        future = asyncio.Future(loop=self.machine.clock.loop)   # type: asyncio.Future

        if not only_on_change:
            for switch_name in switch_names:
                if self.is_state(switch_name, state, ms):
                    future.set_result({"switch_name": switch_name, "state": state, "ms": ms})
                    return future

        handlers = []   # type: List[SwitchHandler]
        future.add_done_callback(partial(self._future_done, handlers))      # type: ignore
        for switch_name in switch_names:
            if state == 2:
                handler_state = 0 if self.is_active(switch_name) else 1
            else:
                handler_state = state
            handlers.append(self.add_switch_handler(switch_name, state=handler_state, ms=ms,
                                                    callback=partial(self._wait_handler,
                                                                     ms=ms,
                                                                     _future=future,
                                                                     switch_name=switch_name)))
        return future

    def _future_done(self, handlers: List[SwitchHandler], future: asyncio.Future):
        del future
        for handler in handlers:
            self.remove_switch_handler_by_key(handler)

    @staticmethod
    def _wait_handler(_future: asyncio.Future, **kwargs):
        if not _future.done():
            _future.set_result(kwargs)

    def _cancel_timed_handlers(self, name, state):
        # now check if the opposite state is in the active timed switches list
        # if so, remove it
        for k, v, in self.active_timed_switches.items():
            # using items() instead of iteritems() since we might want to
            # delete while iterating
            for k2, item in enumerate(v):
                if item.switch_name == str(name) and item.state == state ^ 1:
                    # ^1 in above line invertes the state
                    if self.active_timed_switches[k] and self.active_timed_switches[k][k2]:
                        del self.active_timed_switches[k][k2]

    def _add_timed_switch_handler(self, switch, time: float, timed_switch_handler: TimedSwitchHandler):
        self.active_timed_switches[time].append(timed_switch_handler)

        next_event_time = self.get_next_timed_switch_event()
        add_handler = False

        if switch not in self._timed_switch_handler_delay:
            add_handler = True
        elif next_event_time < self._timed_switch_handler_delay[switch][1]:
            add_handler = True
            self.machine.clock.unschedule(self._timed_switch_handler_delay[switch][0])

        if add_handler:
            handler = self.machine.clock.loop.call_at(
                next_event_time, partial(self._process_active_timed_switches, switch))
            self._timed_switch_handler_delay[switch] = (handler, next_event_time)

    def _call_handlers(self, switch, state):
        for entry in self.registered_switches[switch][state][:]:  # generator?
            # Found an entry.

            # skip if the handler has been removed in the meantime
            if entry.cancelled:
                continue

            if entry.ms:
                # This entry is for a timed switch, so add it to our
                # active timed switch list
                key = switch.last_change + (entry.ms / 1000.0)
                value = TimedSwitchHandler(callback=entry.callback,
                                           switch_name=switch.name,
                                           state=state,
                                           ms=entry.ms)
                self._add_timed_switch_handler(switch, key, value)
                if self._debug_to_console or self._debug_to_file:
                    self.debug_log(
                        "Found timed switch handler for k/v %s / %s",
                        key, value)
            else:
                # This entry doesn't have a timed delay, so do the action
                # now
                entry.callback()

    def add_monitor(self, monitor: Callable[[MonitoredSwitchChange], None]):
        """Add a monitor callback which is called on switch changes."""
        if monitor not in self.monitors:
            self.monitors.append(monitor)

    def remove_monitor(self, monitor: Callable[[MonitoredSwitchChange], None]):
        """Remove a monitor callback."""
        if monitor in self.monitors:
            self.monitors.remove(monitor)

    # pylint: disable-msg=too-many-arguments
    def add_switch_handler(self, switch_name, callback, state=1, ms=0,
                           return_info=False, callback_kwargs=None) -> SwitchHandler:
        """Register a handler to take action on a switch event.

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
                milliseconds.
            return_info: If True, the switch controller will pass the
                parameters of the switch handler as arguments to the callback,
                including switch_name, state, and ms. If False (default), it
                just calls the callback with no parameters.
            callback_kwargs: Additional kwargs that will be passed with the
                callback.

        You can mix & match entries for the same switch here.
        """
        switch = self.machine.switches[switch_name]
        return self.add_switch_handler_obj(switch, callback, state, ms, return_info, callback_kwargs)

    def add_switch_handler_obj(self, switch, callback, state=1, ms=0,
                               return_info=False, callback_kwargs=None):
        """Register a handler to take action on a switch event.

        Same as add_switch_handler but you can pass a switch object instead of a name.
        """
        if callback_kwargs and return_info:
            callback = partial(callback, switch_name=switch.name, state=state, ms=ms, **callback_kwargs)
        elif return_info:
            callback = partial(callback, switch_name=switch.name, state=state, ms=ms)
        elif callback_kwargs:
            callback = partial(callback, **callback_kwargs)

        if self._debug_to_console or self._debug_to_file:
            self.debug_log("Registering switch handler: %s, %s, state: %s, ms: %s"
                           ", info: %s", switch.name, callback,
                           state, ms, return_info)

        entry_val = RegisteredSwitch(ms=ms, callback=callback)
        self.registered_switches[switch][state].append(entry_val)

        # If the switch handler that was just registered has a delay (i.e. ms>0,
        # then let's see if the switch is currently in the state that the
        # handler was registered for. If so, and if the switch has been in this
        # state for less time than the ms registered, then we need to add this
        # switch to our active_timed_switches list so this handler is called
        # when this switch's active time expires. (in other words, we're
        # catching delayed switches that were in progress when this handler was
        # registered.

        if ms and self.ms_since_change(switch.name) < ms:  # only do this for handlers that have delays
            if (state == 1 and self.is_active(switch.name, 0)) or (state == 0 and self.is_inactive(switch.name, 0)):
                # figure out when this handler should fire based on the
                # switch's original activation time.
                key = self.machine.clock.get_time() + ((ms - self.ms_since_change(switch.name)) / 1000.0)
                value = TimedSwitchHandler(callback=callback,
                                           switch_name=switch.name,
                                           state=state,
                                           ms=ms)
                self._add_timed_switch_handler(switch, key, value)

        # Return the args we used to setup this handler for easy removal later
        return SwitchHandler(switch, callback, state, ms)

    def remove_switch_handler_by_key(self, switch_handler: SwitchHandler):
        """Remove switch handler by key returned from add_switch_handler."""
        self.remove_switch_handler_obj(switch_handler.switch_name, switch_handler.callback, switch_handler.state,
                                       switch_handler.ms)

    def remove_switch_handler(self, switch_name, callback, state=1, ms=0):
        """Remove a registered switch handler.

        Currently this only works if you specify everything exactly as you set
        it up. (Except for return_info, which doesn't matter if true or false,
        it will remove either / both.
        """
        switch = self.machine.switches[switch_name]
        self.remove_switch_handler_obj(switch, callback, state, ms)

    def remove_switch_handler_obj(self, switch, callback, state=1, ms=0):
        """Remove a registered switch handler.

        Same as remove_switch_handler but takes a switch object instead of the name.
        """
        if self._debug_to_console or self._debug_to_file:
            self.debug_log(
                "Removing switch handler. Switch: %s, State: %s, ms: %s",
                switch.name, state, ms)

        for entry in list(self.registered_switches[switch][state]):
            if entry.ms == ms and entry.callback == callback:
                entry.cancelled = True
                self.registered_switches[switch][state].remove(entry)

        for k in list(self.active_timed_switches.keys()):
            timed_entry = self.active_timed_switches[k]
            for dummy_key, entry in enumerate(timed_entry):
                if (entry.switch_name == switch.name and entry.state == state and entry.ms == ms and
                        entry.callback == callback):
                    del self.active_timed_switches[k][dummy_key]

    def log_active_switches(self, **kwargs):
        """Write out entries to the INFO log file of all switches that are currently active."""
        del kwargs
        for k, v in self._switch_lookup.items():
            if v.state:
                self.info_log("Found active switch: %s", k)

    @staticmethod
    def get_active_event_for_switch(switch_name):
        """Return the event name which is posted when switch_name becomes active."""
        return "{}_active".format(switch_name)

    def get_next_timed_switch_event(self):
        """Return time of the next timed switch event."""
        if not self.active_timed_switches:
            raise AssertionError("No active timed switches")
        return min(self.active_timed_switches.keys())

    def _process_active_timed_switches(self, switch):
        """Process active times switches.

        Checks the current list of active timed switches to see if it's
        time to take action on any of them. If so, does the callback and then
        removes that entry from the list.
        """
        del self._timed_switch_handler_delay[switch]
        next_event_time = False
        current_time = self.machine.clock.get_time()
        for k in list(self.active_timed_switches.keys()):
            if k <= current_time:  # change to generator?
                for entry in list(self.active_timed_switches[k]):
                    # check if removed by previous entry
                    if entry not in self.active_timed_switches[k]:
                        continue
                    if self._debug_to_console or self._debug_to_file:
                        self.debug_log(
                            "Processing timed switch handler. Switch: %s "
                            " State: %s, ms: %s", entry.switch_name,
                            entry.state, entry.ms)
                    entry.callback()
                del self.active_timed_switches[k]
            else:
                if not next_event_time or next_event_time > k:
                    next_event_time = k

        self.machine.events.process_event_queue()
        if next_event_time:
            handler = self.machine.clock.loop.call_at(
                next_event_time,
                partial(self._process_active_timed_switches, switch))
            self._timed_switch_handler_delay[switch] = (handler, next_event_time)
