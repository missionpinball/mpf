"""A generic state machine."""
import asyncio

from mpf.core.device_monitor import DeviceMonitor

from mpf.core.mode import Mode
from mpf.core.player import Player
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("state")
class StateMachine(SystemWideDevice, ModeDevice):

    """A generic state machine."""

    config_section = 'state_machines'
    collection = 'state_machines'
    class_label = 'state_machine'

    __slots__ = ["player", "_state", "_handlers", "_show"]

    def __init__(self, machine, name):
        """Initialise state machine."""
        super().__init__(machine, name)
        self.player = None
        self._state = None
        self._handlers = []
        self._show = None

    @asyncio.coroutine
    def device_added_system_wide(self):
        """Initialise internal state."""
        yield from super().device_added_system_wide()

        if self.config['persist_state']:
            self.raise_config_error("Cannot set persist_state for system-wide state_machine", 1)

        self._start_state("start")

    @property
    def state(self):
        """Return the current state."""
        if self.config['persist_state']:
            return self.player["state_machine_{}".format(self.name)]
        else:
            return self._state

    @state.setter
    def state(self, value):
        """Set the current state."""
        old = self.state
        if self.config['persist_state']:
            self.player["state_machine_{}".format(self.name)] = value
        else:
            self._state = value

        # notify monitors
        self.notify_virtual_change("state", old, self.state)

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Restore internal state from player if persist_state is set or create new state."""
        super().device_loaded_in_mode(mode, player)
        self.player = player
        if not self.state:
            self._start_state("start")
        else:
            self._add_handlers_for_current_state()
            self._run_show_for_current_state()

    def device_removed_from_mode(self, mode: Mode):
        """Unset internal state to prevent leakage."""
        super().device_removed_from_mode(mode)
        self._remove_handlers()
        self._state = None
        self.player = None

        if self._show:
            self._show.stop()
            self._show = None

    def _stop_current_state(self):
        self._remove_handlers()
        state_config = self.config['states'][self.state]
        if state_config['events_when_stopped']:
            for event_name in state_config['events_when_stopped']:
                self.machine.events.post(event_name)

        if self._show:
            self._show.stop()
            self._show = None

        self.state = None

    def _start_state(self, state):
        if state not in self.config['states']:
            raise AssertionError("Invalid state {}".format(state))

        state_config = self.config['states'][state]
        self.state = state
        if state_config['events_when_started']:
            for event_name in state_config['events_when_started']:
                self.machine.events.post(event_name)

        self._add_handlers_for_current_state()
        self._run_show_for_current_state()

    def _run_show_for_current_state(self):
        assert not self._show
        state_config = self.config['states'][self.state]
        if state_config['show_when_active']:
            self._show = self.machine.show_controller.play_show_with_config(state_config['show_when_active'],
                                                                            self.mode)

    def _add_handlers_for_current_state(self):
        for transition in self.config['transitions']:
            if self.state in transition['source']:
                for event in transition['events']:
                    self._handlers.append(self.machine.events.add_handler(event, self._transition,
                                                                          transition_config=transition))

    def _transition(self, transition_config, **kwargs):
        del kwargs
        self._stop_current_state()
        if transition_config['events_when_transitioning']:
            for event_name in transition_config['events_when_transitioning']:
                self.machine.events.post(event_name)
        self._start_state(transition_config['target'])

    def _remove_handlers(self):
        self.machine.events.remove_handlers_by_keys(self._handlers)
