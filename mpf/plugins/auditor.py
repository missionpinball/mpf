"""MPF plugin for an auditor which records switch events, high scores, shots,
etc."""

import logging
from mpf.system.config import Config
from mpf.system.data_manager import DataManager
from mpf.devices.shot import Shot


class Auditor(object):

    def __init__(self, machine):
        """Base class for the auditor.

        Args:
            machine: A refence to the machine controller object.
        """

        if 'auditor' not in machine.config:
            machine.log.debug('"Auditor:" section not found in machine '
                              'configuration, so the auditor will not be '
                              'used.')
            return

        self.log = logging.getLogger('Auditor')
        self.machine = machine

        self.machine.auditor = self
        self.switchnames_to_audit = set()

        self.enabled = False
        """Attribute that's viewed by other system components to let them know
        they should send auditing events. Set this via the enable() and
        disable() methods.
        """

        self.data_manager = DataManager(self.machine, 'audits')

        self.machine.events.add_handler('init_phase_4', self._initialize)

    def __repr__(self):
        return '<Auditor>'

    def _initialize(self):
        # Initializes the auditor. We do this separate from __init__() since
        # we need everything else to be setup first.

        self.config = self.machine.config_processor.process_config2('auditor',
                                            self.machine.config['auditor'])

        self.current_audits = self.data_manager.get_data()

        if not self.current_audits:
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

    def audit(self, audit_class, event, **kwargs):
        """Called to log an auditable event.

        Args:
            audit_class: A string of the section we want this event to be
            logged to.
            event: A string name of the event we're auditing.
            **kawargs: Not used, but included since some of the audit events
                might include random kwargs.
        """

        if audit_class not in self.current_audits:
            self.current_audits[audit_class] = dict()

        if event not in self.current_audits[audit_class]:
            self.current_audits[audit_class][event] = 0

        self.current_audits[audit_class][event] += 1

    def audit_switch(self, switch_name, state):
        if state and switch_name in self.switchnames_to_audit:
            self.audit('switches', switch_name)

    def audit_shot(self, name, profile, state):
        self.audit('shots', name)

    def audit_event(self, eventname, **kwargs):
        """Registered as an event handlers to log an event to the audit log.

        Args:
            eventname: The string name of the event.
            **kwargs, not used, but included since some types of events include
                kwargs.
        """

        self.current_audits['events'][eventname] += 1

    def audit_player(self, **kwargs):
        """Called to write player data to the audit log. Typically this is only
        called at the end of a game.

        Args:
            **kwargs, not used, but included since some types of events include
                kwargs.
        """
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

    def _merge_into_top_list(self, new_item, current_list, num_items):
        # takes a list of top integers and a new item and merges the new item
        # into the list, then trims it based on the num_items specified
        current_list.append(new_item)
        current_list.sort(reverse=True)
        return current_list[0:num_items]

    def enable(self, **kwags):
        """Enables the auditor.

        This method lets you enable the auditor so it only records things when
        you want it to. Typically this is called at the beginning of a game.

        Args:
            **kwargs: No function here. They just exist to allow this method
                to be registered as a handler for events that might contain
                keyword arguments.

        """
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

        for event in self.config['save_events']:
            self.machine.events.add_handler(event, self._save_audits,
                                            priority=0)

    def _save_audits(self, delay_secs=3):
        self.data_manager.save_all(data=self.current_audits,
                                   delay_secs=delay_secs)

    def disable(self, **kwargs):
        """Disables the auditor."""
        self.log.debug("Disabling the Auditor")
        self.enabled = False

        # remove switch and event handlers
        self.machine.events.remove_handler(self.audit_event)
        self.machine.events.remove_handler(self._save_audits)

        for switch in self.machine.switches:
            if 'no_audit' not in switch.tags:
                self.machine.switch_controller.remove_switch_handler(
                    switch.name, self.audit_switch, 1, 0)


plugin_class = Auditor
