"""MPF plugin for an auditor which records switch events, high scores, shots,
etc."""
# auditor.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os
import yaml
import errno
import thread
import time

from mpf.system.config import Config
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

        self.machine.events.add_handler('init_phase_4', self._initialize)

    def __repr__(self):
        return '<Auditor>'


    def _initialize(self):
        # Initializes the auditor. We do this separate from __init__() since
        # we need everything else to be setup first.

        config = '''
                    save_events: list|ball_ended
                    audit: list|None
                    events: list|None
                    player: list|None
                    num_player_top_records: int|10
                    '''

        self.config = Config.process_config(config,
                                            self.machine.config['auditor'])

        self.filename = os.path.join(self.machine.machine_path,
            self.machine.config['mpf']['paths']['audits'])

        # todo add option for abs path outside of machine root

        self.current_audits = self.load_from_disk(self.filename)

        self.make_sure_path_exists(os.path.dirname(self.filename))

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

        # build this list of swithces we should audit
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

                self.current_audits['player'][item]['top'] = \
                    self._merge_into_top_list(
                        player[item],
                        self.current_audits['player'][item]['top'],
                        self.config['num_player_top_records'])

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
            self.log.debug("Didn't find the audits file. No prob. We'll create "
                          "it when we save.")

    def save_to_disk(self, filename):
        """Dumps the audits from memory to disk.

        Args:
            filename: The path and file the audits will be written to.
        """
        thread.start_new_thread(self._saving_thread, (filename,))

    def _saving_thread(self, filename):
        # Audits are usually saved to disk based on events that happen when MPF
        # is really busy.. ball start, game end, etc. So we sleep for 3 secs to
        # stay out of the way until things calm down a bit.
        time.sleep(3)
        self.log.debug("Writing audits to: %s", filename)
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
                                                eventname=event,
                                                priority=2)
                # Make sure we have an entry in our audit file for this event
                if event not in self.current_audits['events']:
                    self.current_audits['events'][event] = 0

        for event in self.config['save_events']:
            self.machine.events.add_handler(event,
                                            self.save_to_disk,
                                            filename=self.filename,
                                            priority=0)

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


plugin_class = Auditor


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
