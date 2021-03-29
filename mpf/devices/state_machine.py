"""A generic state machine."""
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

    async def device_added_system_wide(self):
        """Initialise internal state."""
        await super().device_added_system_wide()

        if self.config['persist_state']:
            self.raise_config_error("Cannot set persist_state for system-wide state_machine", 1)

        self._start_state(self.config['starting_state'])

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None):
        """Validate transitions."""
        result = super().validate_and_parse_config(config, is_mode_config, debug_prefix)
        states = config.get("states", {})
        for transition in config.get("transitions", []):
            for state in transition["source"]:
                if state not in states:
                    self.raise_config_error("Source {} of transition {} not found in states.".format(
                        transition["source"], transition), 2)
            if transition["target"] not in states:
                self.raise_config_error("Target {} of transition {} not found in states.".format(
                    transition["target"], transition), 3)
        return result

    @property
    def can_exist_outside_of_game(self) -> bool:
        """Return true if persist_state is not set."""
        return not self.config['persist_state']

    @property
    def state(self):
        """Return the current state."""
        if self.config['persist_state'] and self.player:
            return self.player["state_machine_{}".format(self.name)]

        return self._state

    @state.setter
    def state(self, value):
        """Set the current state."""
        old = self.state
        if self.config['persist_state']:
            old = self.player["state_machine_{}".format(self.name)]
            self.player["state_machine_{}".format(self.name)] = value
            self.notify_virtual_change(self, old, value)
        else:
            self._state = value

        # notify monitors
        self.notify_virtual_change("state", old, self.state)

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Restore internal state from player if persist_state is set or create new state."""
        super().device_loaded_in_mode(mode, player)
        self.player = player
        if not self.state:
            self._start_state(self.config['starting_state'])
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
        self.log.debug("Stopping state %s", self.state)
        self._remove_handlers()
        state_config = self.config['states'][self.state]
        if state_config['events_when_stopped']:
            for event_name in state_config['events_when_stopped']:
                self.machine.events.post(event_name)

        if self._show:
            self.log.debug("Stopping show %s", self._show)
            self._show.stop()
            self._show = None

        self.state = None

    def _start_state(self, state):
        self.log.debug("Starting state %s", state)
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
            self.log.debug("Starting show %s", state_config['show_when_active'])
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
        self.log.info("Transitioning from %s to %s", self.state, transition_config["target"])
        self._stop_current_state()
        if transition_config['events_when_transitioning']:
            for event_name in transition_config['events_when_transitioning']:
                self.machine.events.post(event_name)
        self._start_state(transition_config['target'])

    def _remove_handlers(self):
        self.machine.events.remove_handlers_by_keys(self._handlers)
