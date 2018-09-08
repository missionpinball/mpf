"""MPF plugin for an auditor which records switch events, high scores, shots, etc."""

import logging

from mpf.core.switch_controller import MonitoredSwitchChange
from mpf.devices.shot import Shot

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController
    from typing import Any, Set


class Auditor:

    """Writes switch events, regular events, and player variables to an audit log file."""

    __slots__ = ["log", "machine", "switchnames_to_audit", "config", "current_audits", "enabled", "data_manager"]

    def __init__(self, machine: "MachineController") -> None:
        """Initialise auditor.

        Args:
            machine: A reference to the machine controller object.
        """
        if 'auditor' not in machine.config:
            machine.log.debug('"Auditor:" section not found in machine '
                              'configuration, so the auditor will not be '
                              'used.')
            return

        self.log = logging.getLogger('Auditor')
        self.machine = machine

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

    def _initialize(self, **kwargs):
        del kwargs
        # Initializes the auditor. We do this separate from __init__() since
        # we need everything else to be setup first.

        self.config = self.machine.config_validator.validate_config('auditor', self.machine.config['auditor'])

        self.current_audits = self.data_manager.get_data()

        if not isinstance(self.current_audits, dict):
            self.current_audits = dict()

        # Make sure we have all the sections we need in our audit dict
        if 'switches' not in self.current_audits:
            self.current_audits['switches'] = dict()

        if 'events' not in self.current_audits:
            self.current_audits['events'] = dict()

        if 'player' not in self.current_audits:
            self.current_audits['player'] = dict()

        # Make sure we have all the switches in our audit dict
        for switch in self.machine.switches:
            if (switch.name not in self.current_audits['switches'] and
                    'no_audit' not in switch.tags):
                self.current_audits['switches'][switch.name] = 0

        # build the list of switches we should audit
        self.switchnames_to_audit = {x.name for x in self.machine.switches
                                     if 'no_audit' not in x.tags}

        # Make sure we have all the player stuff in our audit dict
        if 'player' in self.config['audit']:
            for item in self.config['player']:
                if item not in self.current_audits['player']:
                    self.current_audits['player'][item] = dict()
                    self.current_audits['player'][item]['top'] = list()
                    self.current_audits['player'][item]['average'] = 0
                    self.current_audits['player'][item]['total'] = 0

        # Register for the events the auditor needs to do its job
        self.machine.events.add_handler('game_starting', self.enable)
        self.machine.events.add_handler('game_ended', self.disable)
        if 'player' in self.config['audit']:
            self.machine.events.add_handler('game_ending', self.audit_player)

        # Enable the shots monitor
        Shot.monitor_enabled = True
        self.machine.register_monitor('shots', self.audit_shot)

        # Add the switches monitor
        self.machine.switch_controller.add_monitor(self.audit_switch)

        for category, audits in self.current_audits.items():
            if not isinstance(audits, dict):
                continue
            for name, value in audits.items():
                self.machine.set_machine_var("audits_{}_{}".format(category, name), value)

    def audit(self, audit_class, event, **kwargs):
        """Log an auditable event.

        Args:
            audit_class: A string of the section we want this event to be
                logged to.
            event: A string name of the event we're auditing.
            **kwargs: Not used, but included since some of the audit events
                might include random kwargs.
        """
        del kwargs

        if audit_class not in self.current_audits:
            self.current_audits[audit_class] = dict()

        if event not in self.current_audits[audit_class]:
            self.current_audits[audit_class][event] = 0

        self.current_audits[audit_class][event] += 1
        self.machine.set_machine_var("audits_{}_{}".format(audit_class, event), self.current_audits[audit_class][event])
        self._save_audits()

    def audit_switch(self, change: MonitoredSwitchChange):
        """Record switch change."""
        if self.enabled and change.state and change.name in self.switchnames_to_audit:
            self.audit('switches', change.name)

    def audit_shot(self, name, profile, state):
        """Record shot hit."""
        del profile
        del state
        self.audit('shots', name)

    def audit_event(self, eventname, **kwargs):
        """Record this event in the audit log.

        Args:
            eventname: The string name of the event.
            **kwargs: not used, but included since some types of events include
                kwargs.
        """
        del kwargs

        self.current_audits['events'][eventname] += 1
        self._save_audits()

    def audit_player(self, **kwargs):
        """Write player data to the audit log.

        Typically this is only called at the end of a game.

        Args:
            **kwargs: not used, but included since some types of events include
                kwargs.
        """
        del kwargs
        if not self.machine.game or not self.machine.game.player_list:
            return

        for item in self.config['player']:
            for player in self.machine.game.player_list:

                self.current_audits['player'][item]['top'] = (
                    self._merge_into_top_list(
                        player[item],
                        self.current_audits['player'][item]['top'],
                        self.config['num_player_top_records']))

                self.current_audits['player'][item]['average'] = (
                    ((self.current_audits['player'][item]['total'] *
                      self.current_audits['player'][item]['average']) +
                     self.machine.game.player[item]) /
                    (self.current_audits['player'][item]['total'] + 1))

                self.current_audits['player'][item]['total'] += 1
        self._save_audits()

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
        if 'events' in self.config['audit']:
            for event in self.config['events']:
                self.machine.events.add_handler(event,
                                                self.audit_event,
                                                eventname=event,
                                                priority=2)
                # Make sure we have an entry in our audit file for this event
                if event not in self.current_audits['events']:
                    self.current_audits['events'][event] = 0

    def _save_audits(self):
        self.data_manager.save_all(data=self.current_audits)

    def disable(self, **kwargs):
        """Disable the auditor."""
        del kwargs
        self.log.debug("Disabling the Auditor")
        self.enabled = False

        # remove switch and event handlers
        self.machine.events.remove_handler(self.audit_event)


plugin_class = Auditor
