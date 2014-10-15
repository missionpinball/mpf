""" Contains the base classes for Targets and TargetGroups."""
# target.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from mpf.system.devices import Device
from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing
from mpf.system.show_controller import Playlist
from collections import deque


class Target(Device):

    config_section = 'Targets'
    collection = 'targets'

    # todo need to add complete show and complete script
    # todo support multiple switches & multiple lights

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('Target.' + name)
        super(Target, self).__init__(machine, name, config, collection)

        self.lit = False
        self.device_str = 'target'

        # set config defaults
        if 'light' not in self.config:
            self.config['light'] = None
        else:
            # todo figure out if light is LED or matrix light
            # change this to the object
            try:
                if self.config['light'] in self.machine.lights:
                    self.config['light'] = self.machine.lights[self.config['light']]
            except:
                if self.config['light'] in self.machine.leds:
                    self.config['light'] = self.machine.leds[self.config['light']]

        if 'light_if_unlit' not in self.config:
            self.config['light_if_unlit'] = True

        if 'unlight_if_lit' not in self.config:
            self.config['unlight_if_lit'] = False

        if 'default_state' not in self.config:
            self.config['default_state'] = 'unlit'

        if 'reset_events' in self.config:
            self.config['reset_events'] = self.machine.string_to_list(
                self.config['reset_events'])
        else:
            self.config['reset_events'] = [None]
        # todo change this to dict with timing delays?

        # light script
        # unlight script
        # light color
        # unlight color

        # register for switch handlers so we know if this switch is hit
        # note this only looks for activations
        self.machine.switch_controller.add_switch_handler(self.config['switch'],
                                                          self.hit, 1)

        # register for events

        for event in self.config['reset_events']:
            self.machine.events.add_handler(event, self.reset)

        self.machine.events.add_handler('action_target_' + self.name +
                                        '_light', self.light)

        self.machine.events.add_handler('action_target_' + self.name +
                                        '_unlight', self.unlight)

        self.machine.events.add_handler('action_target_' + self.name +
                                        '_toggle', self.toggle)

    def hit(self, stealth=False):
        """This target was just hit.

        Stealth lets us change the status without posting the events. Used for
        rotation.
        """
        self.log.debug("Hit. Currently lit: %s", self.lit)

        # todo make this only duing active balls?

        if not self.lit:
            if not stealth:
                self.machine.events.post(self.device_str + '_' +
                                         self.name + '_unlit_hit')
            if self.config['light_if_unlit']:  # light
                self.light(stealth)

        elif self.lit:
            if not stealth:
                self.machine.events.post(self.device_str + '_' +
                                         self.name + '_lit_hit')
            if self.config['unlight_if_lit']:  # unlight
                self.unlight(stealth)

    def light(self, stealth=False):
        self.lit = True
        self.log.debug("Lighting Target. Stealth: %s", stealth)

        # todo add state param

        if not stealth:
            self.machine.events.post(self.device_str + '_' +
                                     self.name + '_lit')

        if self.config['light']:
            if self.config['light_script']:
                pass
                # todo add lit script or light color
            else:
                self.config['light'].on()
                self.log.debug("turning on light")

    def unlight(self, stealth=False):
        self.lit = False
        self.log.debug("Unlighting Target. Stealth: %s", stealth)

        # todo add state param

        if not stealth:
            self.machine.events.post(self.device_str + '_' +
                                     self.name + '_unlit')

        if self.config['light']:
            if self.config['unlight_script']:
                pass
                # todo add lit script or light color
            else:
                self.config['light'].off()
                self.log.debug("turning off light")

    def toggle(self, stealth=False):
        self.log.debug("Toggling lit state")
        if self.lit:
            self.unlight(stealth)
        else:
            self.light(stealth)

    def reset(self):
        self.log.debug("Resetting Target. Default state: %s",
                       self.config['default_state'])
        # todo add state param

        if self.config['default_state'] == 'lit':
            self.light(False)
        else:
            self.unlight(False)


class TargetGroup(Device):

    config_section = 'TargetGroups'
    collection = 'target_groups'

    # todo need to add complete_scripts
    # todo add show playback speed
    # need to add some concept of active that makes sure completion & rotations
    # only happen when they should

    def __init__(self, machine, name, config, collection=None,
                 member_collection=None, device_str=None):
        self.log = logging.getLogger('TargetGroup.' + name)
        super(TargetGroup, self).__init__(machine, name, config, collection)

        self.delay = DelayManager()
        if not device_str:
            self.device_str = 'targets'
        else:
            self.device_str = device_str

        if not member_collection:
            member_collection = self.machine.targets

        self.num_lit = 0
        self.num_unlit = 0
        self.num_targets = 0
        self.targets = list()

        # make sure our target list is a list
        self.config[self.device_str] = self.machine.string_to_list(
            self.config[self.device_str])

        # create our list of objects
        for target in self.config[self.device_str]:
            self.targets.append(member_collection[target])

        if 'lit_complete_show' not in self.config:
            self.config['lit_complete_show'] = None

        if 'lit_complete_script' not in self.config:
            self.config['lit_complete_script'] = None

        if 'unlit_complete_show' not in self.config:
            self.config['unlit_complete_show'] = None

        if 'unlit_complete_script' not in self.config:
            self.config['unlt_complete_script'] = None

        if 'rotate_left_events' not in self.config:
            self.config['rotate_left_events'] = list()
        else:
            self.config['rotate_left_events'] = self.machine.string_to_list(
                self.config['rotate_left_events'])

        if 'rotate_right_events' not in self.config:
            self.config['rotate_right_events'] = list()
        else:
            self.config['rotate_right_events'] = self.machine.string_to_list(
                self.config['rotate_right_events'])

        # If no reset events are specified, just self reset when complete
        if 'reset_events' not in self.config:
            self.config['reset_events'] = {(self.device_str + '_' +
                                           self.name + '_complete'): 0}
        # todo look for config typo where they don't enter a delay time?

        self.num_targets = len(self.targets)

        # set event handlers to watch for target state changes
        for target in self.targets:
            self.machine.events.add_handler(
                target.device_str + '_' + target.name + '_lit',
                self.update_count)
            self.machine.events.add_handler(
                target.device_str + '_' + target.name + '_unlit',
                self.update_count)

        # need to wait until after the show controller is loaded
        self.machine.events.add_handler('machine_init_phase2', self.load_shows)

        # watch for rotation events
        for event in self.config['rotate_left_events']:
            self.machine.events.add_handler(event, self.rotate, direction='left')
        for event in self.config['rotate_right_events']:
            self.machine.events.add_handler(event, self.rotate, direction='right')

        self.enable_reset_events()

    def load_shows(self):
        if self.config['lit_complete_show']:
            playlist = Playlist(self.machine)
            playlist.add_show(step_num=1,
                              show=self.machine.shows[self.config[
                                                      'lit_complete_show']],
                              num_repeats=1,
                              tocks_per_sec=10)
            playlist.step_settings(step=1)
            self.config['lit_complete_show'] = playlist

        if self.config['unlit_complete_show']:
            playlist = Playlist(self.machine)
            playlist.add_show(step_num=1,
                              show=self.machine.shows[self.config[
                                                      'unlit_complete_show']],
                              num_repeats=1,
                              tocks_per_sec=10)
            playlist.step_settings(step=1)
            self.config['unlit_complete_show'] = playlist

    def update_count(self):
        """One of this group's targets changed state. Let's recount them all.
        """

        self.log.info("entering update count for device: %s", self.name)

        num_lit = 0
        for target in self.targets:
            if target.lit:
                num_lit += 1

        self.log.info("current number lit: %s", num_lit)
        self.log.info("previous number lit: %s", self.num_lit)

        old_lit = self.num_lit

        # Post events for this group based on new lits or unlits
        if num_lit > old_lit:  # we have a new lit
            self.log.info("found a new lit")
            for new_hit in range(num_lit - old_lit):
                self.machine.events.post(self.device_str + '_' + self.name +
                                         '_lit_hit')

        elif old_lit > num_lit:  # we have a new unlit
            self.log.info("found a new unlit")
            for new_hit in range(old_lit - num_lit):
                self.machine.events.post(self.device_str + '_' + self.name +
                                         '_unlit_hit')


        self.num_lit = num_lit
        self.num_unlit = self.num_targets - self.num_lit

        self.log.debug("Updated target group state. Num lit: %s, Num unlit:"
                       " %s", self.num_lit, self.num_unlit)

        if self.num_lit == self.num_targets:
            self.lit_complete()
        elif self.num_unlit == self.num_targets:
            self.unlit_complete()

    def lit_complete(self):
        """All the targets in this group are lit."""
        self.log.debug("All targets in group are lit")

        if self.config['lit_complete_show']:
            self.config['lit_complete_show'].start(priority=100, repeat=False,
                                                   reset=True)

        self.machine.events.post(self.device_str + '_' +
                                 self.name + '_lit_complete')

    def unlit_complete(self):
        """All the targets in this group are lit."""
        self.log.debug("All targets in group are unlit")

        if self.config['unlit_complete_show']:
            self.config['unlit_complete_show'].start(priority=100, repeat=False,
                                                     reset=True)

        self.machine.events.post(self.device_str + '_' +
                                 self.name + '_unlit_complete')

    def enable_reset_events(self):
        """Causes this target to watch for the reset events."""

        for event, delay in self.config['reset_events'].iteritems():
            self.machine.events.add_handler(event=event,
                                        handler=self.reset_request,
                                        ms_delay=Timing.string_to_ms(delay))

    def disable_reset_events(self):
        """Disables this target group watching for reset events. In other
        words, if the reset events are posted, this target group will not
        respond.
        """

        for event, delay in self.config['reset_events'].iteritems():
            self.machine.events.remove_handler(method=self.reset_request,
                                        ms_delay=(Timing.string_to_ms(delay)))

    def reset_request(self, ms_delay=0, **kwargs):
        """Received a request to reset this target group.

        This method will set a delay to wait for the amount of time specified
        in the reset delay, then call reset().

        **kwargs since we don't know where this is coming from

        """

        if ms_delay:
            self.delay.add(self.name + '_target_reset', ms_delay, self.reset)
        else:
            self.reset()

    def reset(self):
        """Resets this group of targets."""
        # todo only do this if we have completed targets? Add a force?
        self.log.debug("Resetting target group")

        for target in self.targets:
            target.reset()

        self.update_count()

        # todo do reset show or script

    def rotate(self, direction='right', move_state=True, steps=1):

        if not self.machine.game or not self.machine.game.num_balls_in_play:
            return

        self.log.debug("Rotating target group. Direction: %s, Moving state:"
                       "%s, Steps: %s", direction, move_state, steps)

        # todo implement move_colors

        # create a list which shows which targets are lit.
        lit_list = deque()
        for target in self.targets:
            if target.lit:
                lit_list.append(True)
            else:
                lit_list.append(False)

        # rotate that list
        if direction == 'right':
            lit_list.rotate(steps)
        else:
            lit_list.rotate(steps * -1)

        # step through all our targets and update their complete status
        for i in range(self.num_targets):
            if lit_list[i]:
                self.targets[i].light(stealth=True)
            else:
                self.targets[i].unlight(stealth=True)


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