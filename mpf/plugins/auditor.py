"""MPF plugin for an auditor which records switch events, high scores, shots,
etc."""
# devices.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import os
import yaml
import errno


def preload_check(machine):

    return True


class Auditor(object):

    def __init__(self, machine):
        """Base class for the auditor.

        Args:
            machine: A refence to the machine controller object.
        """
        self.log = logging.getLogger('Auditor')
        self.machine = machine

        self.machine.auditor = self

        self.enabled = False
        """Attribute that's viewed by other system components to let them know
        they should send auditing events. Set this via the enable() and
        disable() methods.
        """

        self.config = self.machine.config['Auditor']
        self.machine.events.add_handler('machine_init_phase3', self._initialize)

    def _initialize(self):
        # Initializes the auditor. We do this separate from __init__() since
        # we need everything else to be setup first.

        self.filename = os.path.join(self.machine.options['machinepath'],
            self.machine.config['MPF']['paths']['audits'])

        # set config defaults:
        if 'save_events' not in self.config:
            self.config['save_events'] = ['ball_ended']
        else:
            self.config['save_events'] = self.machine.string_to_list(
                self.config['save_events'])

        if 'events' in self.config:
            self.config['events'] = self.machine.string_to_list(
                self.config['events'])

        if 'player' in self.config:
            self.config['player'] = self.machine.string_to_list(
                self.config['player'])

        self.current_audits = self.load_from_disk(self.filename)

        self.make_sure_path_exists(os.path.dirname(self.filename))

        if not self.current_audits:
            self.current_audits = dict()

        # Make sure we have all the sections we need in our audit dict
        if ('shots' in self.config['audit'] and
                'Shots' not in self.current_audits):
            self.current_audits['Shots'] = dict()

        if ('switches' in self.config['audit'] and
                'Switches' not in self.current_audits):
            self.current_audits['Switches'] = dict()

        if ('events' in self.config['audit'] and
                'Events' not in self.current_audits):
            self.current_audits['Events'] = dict()

        if ('player' in self.config['audit'] and
                'Player' not in self.current_audits):
            self.current_audits['Player'] = dict()

        # Make sure we have all the switches in our audit dict
        for switch in self.machine.switches:
            if switch.name not in self.current_audits['Switches']:
                self.current_audits['Switches'][switch.name] = 0

        # Make sure we have all the shots in our audit dict
        for shot in self.machine.shots.shots:
            if shot.name not in self.current_audits['Shots']:
                self.current_audits['Shots'][shot.name] = 0

        # Make sure we have all the player stuff in our audit dict
        if 'player' in self.config['audit']:
            for item in self.config['player']:
                if item not in self.current_audits['Player']:
                    self.current_audits['Player'][item] = dict()
                    self.current_audits['Player'][item]['top'] = list()
                    self.current_audits['Player'][item]['average'] = 0
                    self.current_audits['Player'][item]['total'] = 0

        # Register for the events the auditor needs to do its job
        self.machine.events.add_handler('game_starting', self.enable)
        self.machine.events.add_handler('game_ended', self.disable)
        if 'player' in self.config['audit']:
            self.machine.events.add_handler('game_ending', self.audit_player)

    def audit(self, audit_class, event, **kwargs):
        """Called to log an auditable event.

        Args:
            audit_class: A string of the section we want this event to be
            logged to.
            event: A string name of the event we're auditing.
            **kawargs: Not used, but included since some of the audit events
                might include random kwargs.
        """
        self.current_audits[audit_class][event] += 1

    def audit_switch(self, switch_name, state, ms):
        self.audit('Switches', switch_name)

    def audit_event(self, eventname, **kwargs):
        """Registered as an event handlers to log an event to the audit log.

        Args:
            eventname: The string name of the event.
            **kwargs, not used, but included since some types of events include
                kwargs.
        """

        self.current_audits['Events'][eventname] += 1

    def audit_player(self, **kwargs):
        """Called to write player data to the audit log. Typically this is only
        called at the end of a game.

        Args:
            **kwargs, not used, but included since some types of events include
                kwargs.
        """
        for item in self.config['player']:
            for player in self.machine.game.player_list:

                self.current_audits['Player'][item]['top'] = \
                    self._merge_into_top_list(
                        player.vars[item],
                        self.current_audits['Player'][item]['top'],
                        self.config['num_player_top_records'])

                self.current_audits['Player'][item]['average'] = (
                    ((self.current_audits['Player'][item]['total'] *
                      self.current_audits['Player'][item]['average']) +
                     self.machine.game.player.vars[item]) /
                    (self.current_audits['Player'][item]['total'] + 1))

                self.current_audits['Player'][item]['total'] += 1

    def _merge_into_top_list(self, new_item, current_list, num_items):
        # takes a list of top integers and a new item and merges the new item
        # into the list, then trims it based on the num_items specified
        current_list.append(new_item)
        current_list.sort(reverse=True)
        return current_list[0:num_items]

    def load_from_disk(self, filename):
        """Loads an audit log from disk.

        Args:
            filename: The path and file of the audit file location.
        """
        self.log.debug("Loading audits from %s", filename)
        if os.path.isfile(filename):
            try:
                audits_from_file = yaml.load(open(filename, 'r'))
            except yaml.YAMLError, exc:
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    self.log.error("Error found in config file %s. Line %, "
                                   "Position %s", filename, mark.line+1,
                                   mark.column+1)
            except:
                self.log.warning("Couldn't load audits from file: %s", filename)

            return audits_from_file
        else:
            self.log.info("Didn't find the audits file. No prob. We'll create "
                          "it when we save.")

    def save_to_disk(self, filename):
        """Dumps the audits from memory to disk.

        Args:
            filename: The path and file the audits will be written to.
        """
        self.log.debug("Savings the audits to: %s", filename)
        with open(filename, 'w') as output_file:
            output_file.write(yaml.dump(self.current_audits,
                                        default_flow_style=False))

    def make_sure_path_exists(self, path):
        """Checks to see if the audits folder exists and creates it if not."""
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    def enable(self, **kwags):
        """Enables the auditor.

        This method lets you enable the auditor so it only records things when
        you want it to. Typically this is called at the beginning of a game.
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
                                                eventname=event)
                # Make sure we have an entry in our audit file for this event
                if event not in self.current_audits['Events']:
                    self.current_audits['Events'][event] = 0

        for event in self.config['save_events']:
            self.machine.events.add_handler(event,
                                            self.save_to_disk,
                                            filename=self.filename)

        # Register for the switches we're auditing
        for switch in self.machine.switches:
            if 'no_audit' not in switch.tags:
                self.machine.switch_controller.add_switch_handler(switch.name,
                    self.audit_switch, 1, 0, True)

    def disable(self, **kwargs):
        """Disables the auditor.
        """
        self.log.debug("Disabling the Auditor")
        self.enabled = False

        # remove switch and event handlers
        self.machine.events.remove_handler(self.audit_event)
        self.machine.events.remove_handler(self.save_to_disk)

        for switch in self.machine.switches:
            if 'no_audit' not in switch.tags:
                self.machine.switch_controller.remove_switch_handler(
                    switch.name, self.audit_switch, 1, 0)


# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

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
