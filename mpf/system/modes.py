""" Contains the ModeController, Mode, and ModeTimers parent classes"""
# modes.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os

from collections import namedtuple

from mpf.system.timing import Timing, Timer
from mpf.system.tasks import DelayManager

RemoteMethod = namedtuple('RemoteMethod', 'method config_section kwargs',
                          verbose=False)
"""RemotedMethod is used by other modules that want to register a method to
be called on mode_start or mode_stop.
"""


class ModeController(object):

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger('ModeController')

        self.queue = None  # ball ending event queue

        self.active_modes = list()
        self.mode_stop_count = 0

        # The following two lists hold namedtuples of any remote components that
        # need to be notified when a mode object is created and/or started.
        self.loader_methods = list()
        self.start_methods = list()

        if 'Modes' in self.machine.config:
            self.machine.events.add_handler('machine_init_phase_4',
                                            self.load_modes)

        self.machine.events.add_handler('ball_ending', self.ball_ending,
                                        priority=0)

    def load_modes(self):
        """Loads the modes from the Modes: section of the machine configuration
        file.
        """

        for mode in self.machine.config['Modes']:
            self.machine.game_modes.append(self.load_mode(mode))

    def load_mode(self, mode_string):
        """Loads a mode, reads in its config, and creates the Mode object.

        Args:
            mode: String name of the mode you're loading. This is the name of
                the mode's folder in your game's machine_files/modes folder.
        """
        self.log.info('Processing mode: %s', mode_string)

        mode_path = os.path.join(self.machine.machine_path,
                                 self.machine.config['MPF']['paths']['modes'],
                                 mode_string)
        mode_config_file = os.path.join(self.machine.machine_path,
                                        self.machine.config['MPF']['paths']['modes'],
                                        mode_string,
                                        'config',
                                        mode_string + '.yaml')
        config = self.machine.load_config_yaml(yaml_file=mode_config_file)

        if 'code' in config['Mode']:

            import_str = 'modes.' + mode_string + '.code.' + config['Mode']['code'].split('.')[0]
            i = __import__(import_str, fromlist=[''])
            mode_object = getattr(i, config['Mode']['code'].split('.')[1])(
                self.machine, config, mode_string, mode_path)

        else:
            mode_object = Mode(self.machine, config, mode_string, mode_path)

        return mode_object

    def ball_ending(self, queue):
        # unloads all the active modes, like when the ball ends

        self.queue = queue
        self.queue.wait()
        self.mode_stop_count = 0

        for mode in self.active_modes:
            self.mode_stop_count += 1
            mode.stop(callback=self._mode_stopped_callback)

    def _mode_stopped_callback(self):
        self.mode_stop_count -= 1

        if not self.mode_stop_count:
            self.queue.clear()

    def register_load_method(self, load_method, config_section_name=None,
                             **kwargs):
        """Used by system components, plugins, etc. to register themselves with
        the Mode Controller for anything that they a mode to do when its
        registered.

        Args:
            load_method: The method that will be called when this mode code
                loads.
            config_section_name: An optional string for the section of the
                configuration file that will be passed to the load_method when
                it's called.
            **kwargs: Any additional keyword arguments specified will be passed
                to the load_method.

        Note that these methods will be called once, when the mode code is first
        initialized.
        """
        self.loader_methods.append(RemoteMethod(method=load_method,
                                                config_section=config_section_name,
                                                kwargs=kwargs))

    def register_start_method(self, start_method, config_section_name=None,
                              **kwargs):
        """Used by system components, plugins, etc. to register themselves with
        the Mode Controller for anything that they a mode to do when it starts.

        Args:
            start_method: The method that will be called when this mode code
                loads.
            config_section_name: An optional string for the section of the
                configuration file that will be passed to the start_method when
                it's called.
            **kwargs: Any additional keyword arguments specified will be passed
                to the start_method.

        Note that these methods will be called every single time this mode is
        started.
        """
        self.start_methods.append(RemoteMethod(method=start_method,
                                               config_section=config_section_name,
                                               kwargs=kwargs))

    def _active_change(self, mode, active):
        # called when a mode goes active or inactive

        if active:
            self.active_modes.append(mode)
        else:
            self.active_modes.remove(mode)

        # sort the active mode list by priority
        self.active_modes.sort(key=lambda x: x.priority, reverse=True)

        self.dump()

    def dump(self):
        """Dumps the current status of the running modes to the log file."""

        self.log.info('================ ACTIVE GAME MODES ===================')

        for mode in self.active_modes:
            if mode.active:
                self.log.info('%s : %s', mode.name, mode.priority)

        self.log.info('======================================================')


class Mode(object):
    """Parent class for in-game mode code."""

    def __init__(self, machine, config, name, path):
        self.machine = machine
        self.config = config
        self.name = name
        self.path = path

        self.log = logging.getLogger('Mode.' + name)

        self.priority = 0
        self._active = False
        self.stop_methods = list()
        self.timers = dict()
        self.start_callback = None
        self.stop_callback = None

        if 'Mode' in self.config:
            self.configure_mode_settings(config['Mode'])

        for asset_manager in self.machine.asset_managers.values():

            config_data = self.config.get(asset_manager.config_section, dict())

            self.config[asset_manager.config_section] = (
                asset_manager.register_assets(config=config_data,
                                              mode_path=self.path))

        # Call registered remote loader methods
        for item in self.machine.modes.loader_methods:
            if item.config_section in self.config and self.config[item.config_section]:
                item.method(config=self.config[item.config_section],
                            mode_path=self.path,
                            **item.kwargs)

        self.mode_init()

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        if self._active != active:
            self._active = active
            self.machine.modes._active_change(self, self._active)

    def configure_mode_settings(self, config):

        if not ('priority' in config and type(config['priority']) is int):
            config['priority'] = 0

        if 'start_events' in config:
            config['start_events'] = self.machine.string_to_list(
                config['start_events'])
        else:
            config['start_events'] = list()

        if 'stop_events' in config:
            config['stop_events'] = self.machine.string_to_list(
                config['stop_events'])
        else:
            config['stop_events'] = list()

        # register mode start events
        if 'start_events' in config:
            for event in config['start_events']:
                self.machine.events.add_handler(event, self.start)

       # register mode stop events
        if 'stop_events' in config:
            for event in config['stop_events']:
                self.machine.events.add_handler(event, self.stop)

        self.config['Mode'] = config

    def start(self, priority=None, callback=None, **kwargs):
        """Starts this mode.

        Args:
            priority: Integer value of what you want this mode to run at. If you
                don't specify one, it will use the "Mode: priority" setting from
                this mode's configuration file.
            **kwargs: Catch-all since this mode might start from events with
                who-knows-what keyword arguments.

        Warning: Do not override this method. If you want to write your own mode
        code by subclassing Mode, put whatever code you want to run when this
        mode starts in the mode_start method which will be called automatically.
        """

        if self.active:
            return

        if type(priority) is int:
            self.priority = priority
        else:
            self.priority = self.config['Mode']['priority']

        self.log.info('Mode Starting. Priority: %s', self.priority)

        self.start_callback = callback

        if 'Timers' in self.config:
            self.setup_timers()

        self.machine.events.post_queue(event='mode_' + self.name + '_starting',
                                       callback=self._started)

    def _started(self):

        self.log.info('Mode Started. Priority: %s', self.priority)

        self.active = True

        for item in self.machine.modes.start_methods:
            if item.config_section in self.config:
                self.stop_methods.append(
                    item.method(config=self.config[item.config_section],
                                priority=self.priority,
                                mode=self,
                                **item.kwargs))

        self.start_timers()

        self.machine.events.post('mode_' + self.name + '_started')

        self.mode_start()  # change to callback

        if self.start_callback:
            self.start_callback()

    def stop(self, callback=None, **kwargs):
        """Stops this mode.

        Args:
            **kwargs: Catch-all since this mode might start from events with
                who-knows-what keyword arguments.

        Warning: Do not override this method. If you want to write your own mode
        code by subclassing Mode, put whatever code you want to run when this
        mode stops in the mode_stop method which will be called automatically.
        """

        if not self.active:
            return

        self.log.info('Mode Stopping.')

        self.stop_callback = callback

        self.kill_timers()

        # self.machine.events.remove_handler(self.stop)
        # todo is this ok here? Or should we only remove ones that we know this
        # mode added?

        self.machine.events.post_queue(event='mode_' + self.name + '_stopping',
                                       callback=self._stopped)

    def _stopped(self):

        self.log.info('Mode Stopped.')

        self.priority = 0
        self.active = False

        for item in self.stop_methods:
            item[0](item[1])

        self.stop_methods = list()

        self.machine.events.post('mode_' + self.name + '_stopped')

        self.mode_stop()  # change to callback

        if self.stop_callback:
            self.stop_callback()

    def setup_timers(self):
        # config is localized

        for timer, settings in self.config['Timers'].iteritems():

            self.timers[timer] = ModeTimer(machine=self.machine, name=timer,
                                           config=settings)

        return self.kill_timers

    def start_timers(self):
        for timer in self.timers.values():
            if timer.running:
                timer.start()

    def kill_timers(self, ):
        for timer in self.timers.values():
            timer.kill()

        self.timers = dict()

    def mode_init(self):
        """User-overrideable method which will be called when this mode
        initializes as part of the MPF boot process.
        """
        pass

    def mode_start(self):
        """User-overrideable method which will be called whenever this mode
        starts (i.e. whenever it becomes active).
        """
        pass

    def mode_stop(self):
        """User-overrideable method which will be called whenever this mode
        stops (i.e. whenever it becomes inactive).
        """
        pass


class ModeTimer(object):

    def __init__(self, machine, name, config):
        self.machine = machine
        self.name = name
        self.config = config

        self.running = False
        self.start_value = 0
        self.ticks = 0
        self.end_value = 0
        self.direction = 'up'
        self.tick_secs = 1
        self.timer = None
        self.event_keys = set()
        self.delay = DelayManager()

        if 'start_value' in self.config:
            self.start_value = self.config['start_value']
        else:
            self.start_value = 0

        if 'start_running' in self.config and self.config['start_running']:
            self.running = True

        if 'end_value' in self.config:
            self.end_value = self.config['end_value']

        if 'control_events' in self.config and self.config['control_events']:
            if type(self.config['control_events']) is dict:
                self.config['control_events'] = [self.config['control_events']]
        else:
            self.config['control_events'] = list()

        if 'direction' in self.config and self.config['direction'] == 'down':
            self.direction = 'down'

        if 'tick_interval' in self.config:
            self.tick_secs = Timing.string_to_secs(self.config['tick_interval'])

        self.ticks = self.start_value

        self.setup_control_events(self.config['control_events'])

    def setup_control_events(self, event_list):

        kwargs = None

        for entry in event_list:
            if entry['action'] == 'add':
                handler = self.add_time
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] == 'subtract':
                handler = self.subtract_time
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] == 'jump':
                handler = self.set_current_time
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] == 'start':
                handler = self.start

            elif entry['action'] == 'stop':
                handler = self.stop

            elif entry['action'] == 'pause':
                handler = self.pause
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] == 'set_tick_interval':
                handler = self.set_tick_interval
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] == 'change_tick_interval':
                handler = self.change_tick_interval
                kwargs = {'change': entry['value']}

            if kwargs:
                self.event_keys.add(self.machine.events.add_handler(
                                    entry['event'], handler, **kwargs))
            else:
                self.event_keys.add(self.machine.events.add_handler(
                                    entry['event'], handler))

    def remove_control_events(self):
        for key in self.event_keys:
            self.machine.events.remove_handler_by_key(key)

    def start(self, **kwargs):
        self.running = True

        self.delay.remove('pause')
        self.create_timer()

        self.machine.events.post('timer_' + self.name + '_started',
                                 ticks_remaining=self.ticks)

    def stop(self, **kwargs):
        self.delay.remove('pause')

        self.running = False
        self.remove_timer()

        self.machine.events.post('timer_' + self.name + '_stopped',
                                 ticks=self.ticks)

    def pause(self, timer_value=0, **kwargs):
        self.running = False

        pause_secs = timer_value

        if pause_secs > 0:
            self.delay.add('pause', pause_secs, self.start)
            self.machine.events.post('timer_' + self.name + '_paused',
                                     ticks=self.ticks,
                                     pause_secs=pause_secs)
        else:
            self.stop()

    def timer_complete(self):
        self.stop()

        self.machine.events.post('timer_' + self.name + '_complete')

    def timer_tick(self):
        if self.direction == 'down':
            self.ticks -= 1
        else:
            self.ticks += 1

        if not self.check_for_done():
            self.machine.events.post('timer_' + self.name + '_tick',
                                     ticks=self.ticks)

    def add_time(self, timer_value, **kwargs):
        ticks_added = timer_value

        self.ticks += ticks_added

        self.machine.events.post('timer_' + self.name + '_time_added',
                                 ticks=self.ticks,
                                 ticks_added=ticks_added)

        self.check_for_done()

    def subtract_time(self, timer_value, **kwargs):
        ticks_subtracted = timer_value

        self.ticks -= ticks_subtracted

        self.machine.events.post('timer_' + self.name + '_time_subtracted',
                                 ticks=self.ticks,
                                 ticks_subtracted=ticks_subtracted)

        self.check_for_done()

    def check_for_done(self):
        if self.direction == 'up' and self.ticks >= self.end_value:
            self.timer_complete()
            return True
        elif self.ticks <= self.end_value:
            self.timer_complete()
            return True

        return False

    def create_timer(self):

        self.remove_timer()
        self.timer = Timer(callback=self.timer_tick, frequency=self.tick_secs)
        self.machine.timing.add(self.timer)

    def remove_timer(self):
        if self.timer:
            self.machine.timing.remove(self.timer)
            self.timer = None

    def change_tick_interval(self, change=0.0, **kwargs):
        self.tick_secs *= change
        self.create_timer()

    def set_tick_interval(self, timer_value, **kwargs):
        self.tick_secs = timer_value
        self.create_timer()

    def set_current_time(self, timer_value, **kwargs):
        self.ticks = timer_value

    def kill(self):
        self.stop()
        self.remove_control_events()


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
