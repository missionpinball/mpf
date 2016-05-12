"""Contains the SwitchController class which is responsible for reading switch
states and posting events to the framework.

"""

import logging
from collections import defaultdict

from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.utility_functions import Util


class SwitchController(object):
    """Base class for the switch controller, which is responsible for receiving
    all switch activity in the machine and converting them into events.

    More info:
    http://missionpinball.com/docs/core-components/switch-controller/

    """

    log = logging.getLogger('SwitchController')

    def __init__(self, machine):
        self.machine = machine
        self.registered_switches = CaseInsensitiveDict()
        # Dictionary of switches and states that have been registered for
        # callbacks.

        self.active_timed_switches = defaultdict(list)
        # Dictionary of switches that are currently in a state counting ms
        # waiting to notify their handlers. In other words, this is the dict that
        # tracks current switches for things like "do foo() if switch bar is
        # active for 100ms."

        self.switches = CaseInsensitiveDict()
        # Dictionary which holds the master list of switches as well as their
        # current states. State here does factor in whether a switch is NO or NC,
        # so 1 = active and 0 = inactive.

        self.switch_event_active = (
            self.machine.config['mpf']['switch_event_active'])
        self.switch_event_inactive = (
            self.machine.config['mpf']['switch_event_inactive'])
        self.switch_tag_event = (
            self.machine.config['mpf']['switch_tag_event'])

        # register for events
        self.machine.clock.schedule_interval(self._tick, 0, 1000)
        self.machine.events.add_handler('init_phase_2',
                                        self._initialize_switches,
                                        1000)
        # priority 1000 so this fires first

        self.machine.events.add_handler('machine_reset_phase_3',
                                        self.log_active_switches)

        self.monitors = list()

    def register_switch(self, name):
        # Populate self.registered_switches
        self.registered_switches[name + '-0'] = list()
        self.registered_switches[name + '-1'] = list()

        self.set_state(name, 0, reset_time=True)

    def _initialize_switches(self):
        self.update_switches_from_hw()

        for switch in self.machine.switches:
            # Populate self.switches
            self.set_state(switch.name, switch.state, reset_time=True)

            if self.machine.config['mpf']['auto_create_switch_events']:
                switch.activation_events.add(
                    self.machine.config['mpf']['switch_event_active'].replace(
                        '%', switch.name))

                switch.deactivation_events.add(
                    self.machine.config['mpf'][
                        'switch_event_inactive'].replace(
                        '%', switch.name))

            if 'events_when_activated' in switch.config:
                for event in Util.string_to_lowercase_list(
                        switch.config['events_when_activated']):

                    if "|" in event:
                        ev_name, ev_time = event.split("|")
                        self.add_switch_handler(
                            switch_name=switch.name,
                            callback=self.machine.events.post,
                            ms=Util.string_to_ms(ev_time),
                            callback_kwargs={'event': ev_name}
                        )
                    else:
                        switch.activation_events.add(event)

            if 'events_when_deactivated' in switch.config:
                for event in Util.string_to_lowercase_list(
                        switch.config['events_when_deactivated']):

                    if "|" in event:
                        ev_name, ev_time = event.split("|")
                        self.add_switch_handler(
                            switch_name=switch.name,
                            callback=self.machine.events.post,
                            state=0,
                            ms=Util.string_to_ms(ev_time),
                            callback_kwargs={'event': ev_name}
                        )
                    else:
                        switch.deactivation_events.add(event)

    def update_switches_from_hw(self):
        """Updates the states of all the switches be re-reading the states from
        the hardware platform.

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
            switch_states = platform.get_hw_switch_states()

            for switch, number in switches:
                # if two platforms have the same number choose the right switch
                if switch.platform != platform:
                    continue
                try:
                    switch.state = switch_states[number] ^ switch.invert
                    switch.time = self.machine.clock.get_time()
                except (IndexError, KeyError):
                    self.log.warning("Received a status update from hardware "
                                     "switch %s, but that switch is not in "
                                     "your config. Just FYI.", number)

    def verify_switches(self):
        """Loops through all the switches and queries their hardware states via
        their platform interfaces and them compares that to the state that MPF
        thinks the switches are in.

        Throws logging warnings if anything doesn't match.

        This method is notification only. It doesn't fix anything.

        """
        current_states = dict()

        for switch in self.machine.switches:
            current_states[switch] = switch.state

        self.update_switches_from_hw()

        for switch in self.machine.switches:
            if switch.state ^ switch.invert != current_states[switch]:
                self.log.warning("Switch State Error! Switch: %s, HW State: "
                                 "%s, MPF State: %s", switch.name,
                                 current_states[switch],
                                 switch.state ^ switch.invert)

    def is_state(self, switch_name, state, ms=0):
        """Queries whether a switch is in a given state and (optionally)
        whether it has been in that state for the specified number of ms.

        Returns True if the switch_name has been in the state for the given
        number of ms. If ms is not specified, returns True if the switch
        is in the state regardless of how long it's been in that state.

        """

        if not ms:
            ms = 0

        return self.switches[switch_name]['state'] == state and ms <= self.ms_since_change(switch_name)

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

        return round((self.machine.clock.get_time() - self.switches[switch_name]['time']) * 1000.0, 0)

    def secs_since_change(self, switch_name):
        """Returns the number of ms that have elapsed since this switch
        last changed state.
        """

        return self.machine.clock.get_time() - self.switches[switch_name]['time']

    def set_state(self, switch_name, state=1, reset_time=False):
        """Sets the state of a switch."""

        if reset_time:
            timestamp = -1
        else:
            timestamp = self.machine.clock.get_time()

        self.switches.update({switch_name: {'state': state,
                                            'time': timestamp
                                            }
                              })

        # todo this method does not set the switch device's state. Either get
        # rid of it, or move the switch device settings from process_switch()
        # to here.

    def process_switch_by_num(self, num, state, platform, logical=False):
        for switch in self.machine.switches:
            if switch.hw_switch.number == num and switch.platform == platform:
                self.process_switch(name=switch.name, state=state, logical=logical)
                return

    def process_switch(self, name, state=1, logical=False):
        """Processes a new switch state change.

        Args:
            name: The string name of the switch. This is optional if you specify
                the switch via the 'num' or 'obj' parameters.
            state: Boolean or int of state of the switch you're processing,
                True/1 is active, False/0 is inactive.
            logical: Boolean which specifies whether the 'state' argument
                represents the "physical" or "logical" state of the switch. If
                True, a 1 means this switch is active and a 0 means it's
                inactive, regardless of the NC/NO configuration of the switch.
                If False, then the state paramenter passed will be inverted if
                the switch is configured to be an 'NC' type. Typically the
                hardware will send switch states in their raw (logical=False)
                states, but other interfaces like the keyboard and OSC will use
                logical=True.

        Note that there are three different paramter options to specify the
        switch: 'name', 'num', and 'obj'. You only need to pass one of them.

        This is the method that is called by the platform driver whenever a
        switch changes state. It's also used by the "other" modules that
        activate switches, including the keyboard and OSC interfaces.

        State 0 means the switch changed from active to inactive, and 1 means
        it changed from inactive to active. (The hardware & platform code
        handles NC versus NO switches and translates them to 'active' versus
        'inactive'.)

        """

        self.log.debug("Processing switch. Name: %s, state: %s, logical: %s,", name, state, logical)

        try:
            obj = self.machine.switches[name]
        except KeyError:
            raise AssertionError("Cannot process switch \"" + name + "\" as "
                                 "this is not a valid switch name.")

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

        # Update the hardware state since we always want this to match real hw
        obj.hw_state = hw_state

        # if the switch is active, check to see if it's recycle_time has passed
        if state and not self._check_recycle_time(obj, state):
            self.machine.clock.schedule_once(lambda dt: self._recycle_passed(obj, state, logical, obj.hw_state),
                                             timeout=obj.recycle_clear_time - self.machine.clock.get_time())
            return

        obj.state = state  # update the switch device

        if state:
            # update the switch's next recycle clear time
            obj.recycle_clear_time = (self.machine.clock.get_time() +
                                      obj.recycle_secs)

        # if the switch is already in this state, then abort
        if self.switches[name]['state'] == state:

            if not obj.recycle_secs:
                self.log.info("Received duplicate switch state, which means "
                              "this switch had some non-debounced state changes. This "
                              "could be nothing, but if it happens a lot it could "
                              "indicate noise or interference on the line. Switch: %s",
                              name)
            return

        self.log.info("<<<<< switch: %s, State:%s >>>>>", name, state)

        # Update the switch controller's logical state for this switch
        self.set_state(name, state)

        self._call_handlers(name, state)

        self._cancel_timed_handlers(name, state)

        for monitor in self.monitors:
            monitor(name, state)

        self._post_switch_events(name, state)

    def _recycle_passed(self, obj, state, logical, hw_state):
        if obj.hw_state == hw_state:
            self.process_switch(obj.name, state, logical)

    def _cancel_timed_handlers(self, name, state):
        # now check if the opposite state is in the active timed switches list
        # if so, remove it
        for k, v, in list(self.active_timed_switches.items()):
            # using items() instead of iteritems() since we might want to
            # delete while iterating

            for item in v:
                if item['switch_action'] == str(name) + '-' + str(state ^ 1):
                    # ^1 in above line invertes the state
                    if self.active_timed_switches[k]:
                        del self.active_timed_switches[k]

    def _call_handlers(self, name, state):
        # Combine name & state so we can look it up
        switch_key = str(name) + '-' + str(state)

        # Do we have any registered handlers for this switch/state combo?
        if switch_key in self.registered_switches:
            for entry in self.registered_switches[switch_key]:  # generator?
                # Found an entry.

                if entry['ms']:
                    # This entry is for a timed switch, so add it to our
                    # active timed switch list
                    key = self.machine.clock.get_time() + (entry['ms'] / 1000.0)
                    value = {'switch_action': str(name) + '-' + str(state),
                             'callback': entry['callback'],
                             'switch_name': name,
                             'state': state,
                             'ms': entry['ms'],
                             'removed': False,
                             'return_info': entry['return_info'],
                             'callback_kwargs': entry['callback_kwargs']}
                    self.active_timed_switches[key].append(value)
                    self.log.debug(
                        "Found timed switch handler for k/v %s / %s",
                        key, value)
                else:
                    # This entry doesn't have a timed delay, so do the action
                    # now
                    if entry['return_info']:

                        entry['callback'](switch_name=name, state=state, ms=0,
                                          **entry['callback_kwargs'])
                    else:
                        entry['callback'](**entry['callback_kwargs'])

                        # todo need to add args and kwargs support to callback

    def add_monitor(self, monitor):
        if monitor not in self.monitors:
            self.monitors.append(monitor)

    # pylint: disable-msg=too-many-arguments
    def add_switch_handler(self, switch_name, callback, state=1, ms=0,
                           return_info=False, callback_kwargs=None):
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
                milliseconds (rounded up to the nearst machine timer tick).
            return_info: If True, the switch controller will pass the
                parameters of the switch handler as arguments to the callback,
                including switch_name, state, and ms. If False (default), it
                just calls the callback with no parameters.
            callback_kwargs: Additional kwargs that will be passed with the
                callback.

        You can mix & match entries for the same switch here.

        """
        if not callback_kwargs:
            callback_kwargs = dict()

        self.log.debug("Registering switch handler: %s, %s, state: %s, ms: %s"
                       ", info: %s, cb_kwargs: %s", switch_name, callback,
                       state, ms,
                       return_info, callback_kwargs)

        entry_val = {'ms': ms, 'callback': callback,
                     'return_info': return_info,
                     'callback_kwargs': callback_kwargs}
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
                    key = self.machine.clock.get_time() + ((ms - self.ms_since_change(switch_name)) / 1000.0)
                    value = {'switch_action': entry_key,
                             'callback': callback,
                             'switch_name': switch_name,
                             'state': state,
                             'ms': ms,
                             'removed': False,
                             'return_info': return_info,
                             'callback_kwargs': callback_kwargs}
                    self.active_timed_switches[key].append(value)
            elif state == 0:
                if self.is_inactive(switch_name, 0) and (
                        self.ms_since_change(switch_name) < ms):
                    key = self.machine.clock.get_time() + ((ms - self.ms_since_change(switch_name)) / 1000.0)
                    value = {'switch_action': entry_key,
                             'callback': callback,
                             'switch_name': switch_name,
                             'state': state,
                             'ms': ms,
                             'removed': False,
                             'return_info': return_info,
                             'callback_kwargs': callback_kwargs}
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
        will remove either / both.

        """

        self.log.debug(
            "Removing switch handler. Switch: %s, State: %s, ms: %s",
            switch_name, state, ms)

        entry_key = str(switch_name) + '-' + str(state)

        if entry_key in self.registered_switches:
            for dummy_index, settings in enumerate(
                    self.registered_switches[entry_key]):
                if settings['ms'] == ms and settings['callback'] == callback:
                    self.registered_switches[entry_key].remove(settings)

        for dummy_timed_key, timed_entry in self.active_timed_switches.items():
            for dummy_key, entry in enumerate(timed_entry):
                if entry['switch_action'] == entry_key and entry['ms'] == ms and entry['callback'] == callback:
                    entry['removed'] = True

    def log_active_switches(self):
        """Writes out entries to the log file of all switches that are
        currently active.

        This is used to set the "initial" switch states of standalone testing
        tools, like our log file playback utility, but it might be useful in
        other scenarios when weird things are happening.

        This method dumps these events with logging level "INFO."

        """

        self.log.info("Dumping current active switches")

        for k, v in self.switches.items():
            if v['state']:
                self.log.info("Active Switch|%s", k)

    def _check_recycle_time(self, switch, state):
        # checks to see when a switch is ok to be activated again after it's
        # been last activated

        if self.machine.clock.get_time() >= switch.recycle_clear_time:
            return True

        else:
            if state:
                switch.recycle_jitter_count += 1
            return False

    def _post_switch_events(self, switch_name, state):
        """Posts the game events based on this switch changing state. """

        # the following events all fire the moment a switch goes active
        if state == 1:

            for event in self.machine.switches[switch_name].activation_events:
                self.machine.events.post(event)

            for tag in self.machine.switches[switch_name].tags:
                self.machine.events.post(
                    self.switch_tag_event.replace('%', tag))
            '''event: sw_(tag_name)

            desc: A switch tagged with *tag_name* was just activated.

            For example, if in the ``switches:`` section of your config, you
            have a switch with ``tags: start, hello``, then the events
            *sw_start* and *sw_hello* will be posted when that switch is hit.

            Note that you can change the format of these events in your
            machine config file, but *sw_(tag_name)* is the default.

            '''

        # the following events all fire the moment a switch becomes inactive
        elif state == 0:
            for event in self.machine.switches[switch_name].deactivation_events:
                self.machine.events.post(event)

    def get_next_timed_switch_event(self):
        if not self.active_timed_switches:
            return False
        return min(self.active_timed_switches.keys())

    def _tick(self, dt):
        """Called once per machine tick.

        Checks the current list of active timed switches to see if it's
        time to take action on any of them. If so, does the callback and then
        removes that entry from the list.

        """
        del dt

        for k in list(self.active_timed_switches.keys()):
            if k <= self.machine.clock.get_time():  # change to generator?
                for entry in self.active_timed_switches[k]:
                    if entry['removed']:
                        continue
                    self.log.debug(
                        "Processing timed switch handler. Switch: %s "
                        " State: %s, ms: %s", entry['switch_name'],
                        entry['state'], entry['ms'])
                    if entry['return_info']:
                        entry['callback'](switch_name=entry['switch_name'],
                                          state=entry['state'],
                                          ms=entry['ms'],
                                          **entry['callback_kwargs'])
                    else:
                        entry['callback'](**entry['callback_kwargs'])
                del self.active_timed_switches[k]

        self.machine.events.process_event_queue()
