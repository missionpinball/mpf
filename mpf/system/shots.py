""" Base class for the shot controller which converts series of switch events
to 'shots' in the game."""
# shot_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework
import logging
from mpf.system.timing import Timing
from mpf.system.tasks import DelayManager


class ShotController(object):

    def __init__(self, machine):
        """Base class for the shot controller.

        The shot controller sets up and keeps track of all the shots in the
        machine.

        TODO: There's a lot to do still with this, but the basics are working.
        The todo list includes:

        * Figure out when & how are shots enabled? Does the ball start do it?
        Does each shot have an enable event and disable event so they can
        enable and disable themselves? (This could default to ball start?)
        * Lots more shot options need to be added, including kill switches,
        time extensions, etc.
        * Need to implement the functionality to work around broken switches
        * Need to add the ability for a shot to "advertise" itself which would
        be light, display, or sound effects that are kicked off when a shot
        wants to let the player know it's available.

        Parameters
        ----------

        machine : object
            The MachineController object

        """
        self.machine = machine
        self.log = logging.getLogger("Shots")
        self.log.debug("Loading the ShotController")
        self.shots = []

        if 'Shots' in self.machine.config:
            self.log.debug("Configuring the Shots")
            for shot in self.machine.config['Shots']:
                if ('Type' in self.machine.config['Shots'][shot] and
                        self.machine.config['Shots'][shot]['Type'] ==
                        'Sequence'):
                    self.shots.append(SequenceShot(self.machine, shot,
                        self.machine.config['Shots'][shot]))
                else:
                    self.shots.append(StandardShot(self.machine, shot,
                        self.machine.config['Shots'][shot]))
        else:
            self.log.debug("No shot configuration found. Skipping...")


class Shot(object):

    def __init__(self, machine, name, config):
        """Parent class that all shots are based on.

        Parameters
        ----------

        machine : object
            The MachineController object

        name : str
            The name of this shot

        config : dict
            The dictionary that holds the configuration for this shot.

        """
        self.log = logging.getLogger('Shot.' + name)
        self.log.debug("Creating shot")
        self.name = name
        self.active = True
        self.advertising = False
        self.tags = list()
        self.ms_to_complete = 0
        self.advertising_macro = []
        self.machine = machine
        self.config = config

    def advertise(self):
        pass  # todo


class StandardShot(Shot):

    def __init__(self, machine, name, config):
        """StandardShot base class which maps a single switch to a shot.

        Subclass of `Shot`

        Parameters
        ----------

        machine : object
            The MachineController object

        name : str
            The name of this shot

        config : dict
            The dictionary that holds the configuration for this shot.

        """
        super(StandardShot, self).__init__(machine, name, config)

        self.switches = []
        self.backup_switches = []
        self.enable()

    def enable(self):
        """Enables the shot."""
        self.log.debug("Enabling")
        for switch in self.machine.string_to_list(self.config['Switch']):
            self.machine.switch_controller.add_switch_handler(
                switch, self._switch_handler, return_info=True)
        self.active = True

    def disable(self):
        """Disables the shot."""
        self.log.debug("Disabling")
        self.active = False
        for switch in self.machine.string_to_list(self.config['Switch']):
            self.machine.switch_controller.remove_switch_handler(
                switch, self._switch_handler)

    def _switch_handler(self, switch_name, state, ms):
            self.machine.events.post('shot_' + self.name)
            if self.machine.auditor.enabled:
                self.machine.auditor.audit('Shots', self.name)


class SequenceShot(Shot):

    def __init__(self, machine, name, config):
        """SequenceShot is where you need certain switches to be hit in the
        right order, possibly within a time limit.

        Subclass of `Shot`

        Parameters
        ----------

        machine : object
            The MachineController object

        name : str
            The name of this shot

        config : dict
            The dictionary that holds the configuration for this shot.

        """
        super(SequenceShot, self).__init__(machine, name, config)

        self.delay = DelayManager()

        self.progress_index = 0
        """Tracks how far along through this sequence the current shot is."""

        self.configure()
        self.enable()
        self.active_delay = False

    def configure(self):
        """Configures the shot."""

        # convert our switches config to a list
        if 'Switches' in self.config:
            self.config['Switches'] = \
                self.machine.string_to_list(self.config['Switches'])

        # convert our timout to ms
        if 'Time' in self.config:
            self.config['Time'] = Timing.string_to_ms(self.config['Time'])
        else:
            self.config['Time'] = 0

    def enable(self):
        """Enables the shot. If it's not enabled, the switch handlers aren't
        active and the shot event will not be posted."""
        self.log.debug("Enabling")
        # create the switch handlers
        for switch in self.config['Switches']:
            self.machine.switch_controller.add_switch_handler(
                switch, self._switch_handler, return_info=True)
        self.progress_index = 0
        self.active = True

    def disable(self):
        """Disables the shot. If it's disabled, the switch handlers aren't
        active and the shot event will not be posted."""
        self.log.debug("Disabling")
        self.active = False
        for switch in self.config['Switches']:
            self.machine.switch_controller.remove_switch_handler(
                switch, self.switch_handler)
        self.progress_index = 0

    def _switch_handler(self, switch_name, state, ms):
        # does this current switch meet the next switch in the progress index?
        if switch_name == self.config['Switches'][self.progress_index]:

            # are we at the end?
            if self.progress_index == len(self.config['Switches']) - 1:
                self.confirm_shot()
            else:
                # does this shot specific a time limit?
                if self.config['Time']:
                    # do we need to set a delay?
                    if not self.active_delay:
                        self.delay.reset(name='shot_timer',
                                         ms=self.config['Time'],
                                         callback=self.reset)
                        self.active_delay = True

                # advance the progress index
                self.progress_index += 1

    def confirm_shot(self):
        """Called when the shot is complete to confirm and reset it."""
        # kill the delay
        self.delay.remove('shot_timer')
        # reset our shot
        self.reset()
        # post the success event
        if self.machine.auditor.enabled:
                self.machine.auditor.audit('Shots', self.name)
        self.machine.events.post('shot_' + self.name)

    def reset(self):
        """Resets the progress without disabling the shot."""
        self.log.debug("Resetting this shot")
        self.progress_index = 0
        self.active_delay = False

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
