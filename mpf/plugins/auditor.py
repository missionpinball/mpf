"""MPF plugin for an auditor which records switch events, high scores, shots, etc."""

from mpf.core.switch_controller import MonitoredSwitchChange
from mpf.core.plugin import MpfPlugin
from mpf.devices.shot import Shot

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import
    from typing import Any, Set     # pylint: disable-msg=cyclic-import,unused-import


class Auditor(MpfPlugin):

    """Writes switch events, regular events, and player variables to an audit log file."""

    __slots__ = ["switchnames_to_audit", "config", "_autosave",
                 "current_audits", "enabled", "data_manager"]

    config_section = 'auditor'

    def initialize(self):
        self.configure_logging(self.name)
        self.machine.auditor = self
        self.switchnames_to_audit = set()       # type: Set[str]
        self.config = None                      # type: Any
        self.current_audits = None              # type: Any

        self.enabled = False
        """Attribute that's viewed by other core components to let them know
        they should send auditing events. Set this via the enable() and
        disable() methods.
        """

        self.data_manager = self.machine.create_data_manager('audits')

        self.machine.events.add_handler('init_phase_4', self._initialize)

    def __repr__(self):
        """Return string representation."""
        return '<Auditor>'

    def _load_defaults(self):
        """Load defaults if audits are missing."""
        if not isinstance(self.current_audits, dict):
            self.current_audits = dict()

        # Make sure we have all the sections we need in our audit dict
        if 'switches' not in self.current_audits:
            self.current_audits['switches'] = dict()

        if 'events' not in self.current_audits:
            self.current_audits['events'] = dict()

        if 'player' not in self.current_audits:
            self.current_audits['player'] = dict()

        if 'missing_switches' not in self.current_audits:
            self.current_audits['missing_switches'] = dict()

        # build the list of switches we should audit
        try:
            is_free_play = self.machine.settings.get_setting_value('free_play')
        except AssertionError:
            # If the machine has never set up a setting for free_play, get_setting_value
            # will throw. Assume this is a homebrew and is free to play.
            is_free_play = True

        self.switchnames_to_audit = {x.name for x in self.machine.switches.values() if
            # Don't audit tagged switches, or credit switches during free play
            ('no_audit' not in x.tags) and ('no_audit_free' not in x.tags or not is_free_play)}

        # Make sure we have all the switches in our audit dict
        for switch_name in self.switchnames_to_audit:
            if switch_name not in self.current_audits['switches']:
                self.current_audits['switches'][switch_name] = 0

        for event in self.config['events']:
            if event not in self.current_audits['events']:
                self.current_audits['events'][event] = 0

        # Make sure we have all the player stuff in our audit dict
        if 'player' in self.config['audit']:
            for item in self.config['player']:
                if item not in self.current_audits['player']:
                    self.current_audits['player'][item] = dict()
                    self.current_audits['player'][item]['top'] = list()
                    self.current_audits['player'][item]['average'] = 0
                    self.current_audits['player'][item]['total'] = 0

    def _set_machine_variables(self):
        """Set machine variables for audits."""
        for category, audits in self.current_audits.items():
            if not isinstance(audits, dict):
                continue
            for name, value in audits.items():
                self.machine.variables.set_machine_var("audits_{}_{}".format(category, name), value)

    def _initialize(self, **kwargs):
        del kwargs
        # Initializes the auditor. We do this separate from __init__() since
        # we need everything else to be setup first.

        self.config = self.machine.config_validator.validate_config('auditor', self.machine.config['auditor'])

        self.current_audits = self.data_manager.get_data()
        self._autosave = self.config["autosave"]

        self._load_defaults()
        self._set_machine_variables()

        for event in self.config['reset_audit_events']:
            self.machine.events.add_handler(event, self._reset)
        for event in self.config['enable_events']:
            self.machine.events.add_handler(event, self.enable)
        for event in self.config['disable_events']:
            self.machine.events.add_handler(event, self.disable)

    def _reset(self, **kwargs):
        """Reset audits."""
        del kwargs
        self.log.info("Resetting audits")
        self.current_audits = {}
        self._load_defaults()
        self._set_machine_variables()
        self._save_audits()

    def audit(self, audit_class, event, value=None, **kwargs):
        """Log an auditable event.

        Args:
        ----
            audit_class: A string of the section we want this event to be
                logged to.
            event: A string name of the event we're auditing.
            value: If you specify a value the audit will be set to this value. Otherwise it will be incremented by one.
            **kwargs: Not used, but included since some of the audit events
                might include random kwargs.
        """
        del kwargs
        if not self.enabled:
            return

        if audit_class not in self.current_audits:
            self.current_audits[audit_class] = dict()

        if event not in self.current_audits[audit_class]:
            self.current_audits[audit_class][event] = 0

        if value is None:
            self.current_audits[audit_class][event] += 1
        else:
            self.current_audits[audit_class][event] = value
        self.machine.variables.set_machine_var("audits_{}_{}".format(audit_class, event),
                                               self.current_audits[audit_class][event])
        if self._autosave:
            self._save_audits()

    def get_audit(self, audit_class, event, **kwargs):
        """Return an auditable event or create one if it does not exist.

        Args:
        ----
            audit_class: A string of the section we want this event to be
                logged to.
            event: A string name of the event we're auditing.
            **kwargs: Not used, but included since some of the audit events
                might include random kwargs.
        """
        del kwargs
        return self.current_audits.get(audit_class, {}).get(event, 0)

    def audit_switch(self, change: MonitoredSwitchChange):
        """Record switch change."""
        if change.state and change.name in self.switchnames_to_audit:
            if change.name in self.current_audits['missing_switches']:
                del self.current_audits['missing_switches'][change.name]
            self.audit('switches', change.name)

    def audit_shot(self, name, profile, state):
        """Record shot hit."""
        del profile
        del state
        self.audit('shots', name)

    def audit_event(self, eventname, **kwargs):
        """Record this event in the audit log.

        Args:
        ----
            eventname: The string name of the event.
            **kwargs: not used, but included since some types of events include
                kwargs.
        """
        del kwargs
        # Any events defined in the configs will exist, but custom code
        # may call this method with other events that haven't been defined.
        # Using try/except for the lowest cost on majority of paths
        try:
            self.current_audits['events'][eventname] += 1
        except KeyError:
            self.current_audits['events'][eventname] = 1
        if self._autosave or self.config['autosave_events']:
            self._save_audits()

    def audit_player(self, **kwargs):
        """Write player data to the audit log.

        Typically this is only called at the end of a game.

        Args:
        ----
            **kwargs: not used, but included since some types of events include
                kwargs.
        """
        del kwargs
        if not self.machine.game or not self.machine.game.player_list:
            return

        for item in set(self.config['player']):
            for player in self.machine.game.player_list:
                # Don't audit values that haven't been initialized on the player, either by
                # a value set during gameplay or with an initial_value in the player_vars config
                if item not in self.machine.game.player.vars:
                    continue

                self.current_audits['player'][item]['top'] = (
                    self._merge_into_top_list(
                        player[item],
                        self.current_audits['player'][item]['top'],
                        self.config['num_player_top_records']))

                self.current_audits['player'][item]['average'] = int(
                    ((self.current_audits['player'][item]['total'] *
                      self.current_audits['player'][item]['average']) +
                     self.machine.game.player[item]) /
                    (self.current_audits['player'][item]['total'] + 1))

                self.current_audits['player'][item]['total'] += 1
        if self._autosave:
            self._save_audits()

    def report_missing_switches(self, missing_switch_min_games=None):
        min_threshold = missing_switch_min_games or \
            self.config['missing_switch_min_games']
        missing_switches = self.current_audits['missing_switches'].items()
        result = filter(lambda x: x[1] >= min_threshold, missing_switches)
        return list(result)

    @classmethod
    def _merge_into_top_list(cls, new_item, current_list, num_items):
        # takes a list of top integers and a new item and merges the new item
        # into the list, then trims it based on the num_items specified
        current_list.append(new_item)
        current_list.sort(reverse=True)
        return current_list[0:num_items]

    def enable(self, **kwargs):
        """Enable the auditor.

        This method lets you enable the auditor so it only records things when
        you want it to. Typically this is called at the beginning of a game.

        Args:
        ----
            **kwargs: No function here. They just exist to allow this method
                to be registered as a handler for events that might contain
                keyword arguments.

        """
        del kwargs
        if self.enabled:
            return  # this will happen if we get a mid game restart

        self.log.debug("Enabling the Auditor")
        self.enabled = True

        # Register for the events we're auditing
        if 'events' in self.config:
            for event in self.config['events']:
                self.machine.events.add_handler(event,
                                                self.audit_event,
                                                eventname=event,
                                                priority=2)
                # Make sure we have an entry in our audit file for this event
                if event not in self.current_audits['events']:
                    self.current_audits['events'][event] = 0

        # Track how many games played since each switch was triggered
        for switch_name in self.switchnames_to_audit:
            if switch_name not in self.current_audits['missing_switches']:
                self.current_audits['missing_switches'][switch_name] = 1
            else:
                self.current_audits['missing_switches'][switch_name] += 1

        # Register for the events the auditor needs to do its job
        # self.machine.events.add_handler('game_starting', self.enable)
        # self.machine.events.add_handler('game_ended', self.disable)
        if 'player' in self.config['audit']:
            self.machine.events.add_handler('game_ending', self.audit_player)

        # Enable the shots monitor
        if self.config["audit_shots"]:
            Shot.monitor_enabled = True
            self.machine.register_monitor('shots', self.audit_shot)

        # Add the switches monitor
        self.machine.switch_controller.add_monitor(self.audit_switch)

        # Add a save event handler
        for event in self.config['save_events']:
            self.machine.events.add_handler(event, self._save_audits)

    def _save_audits(self, **kwargs):
        del kwargs
        self.data_manager.save_all(data=self.current_audits)

    def disable(self, **kwargs):
        """Disable the auditor."""
        del kwargs
        self.log.debug("Disabling the Auditor")
        self.enabled = False

        # remove switch and event handlers
        self.machine.events.remove_handler(self.audit_event)
        self.machine.events.remove_handler(self.audit_player)
        self.machine.events.remove_handler(self.audit_shot)
        self.machine.events.remove_handler(self.audit_switch)
        self.machine.events.remove_handler(self._save_audits)
