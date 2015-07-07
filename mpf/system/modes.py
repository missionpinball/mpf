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
from mpf.system.config import Config

RemoteMethod = namedtuple('RemoteMethod', 'method config_section kwargs',
                          verbose=False)
"""RemotedMethod is used by other modules that want to register a method to
be called on mode_start or mode_stop.
"""


# todo
# override player var
# override event strings


class ModeController(object):
    """Parent class for the Mode Controller. There is one instance of this in
    MPF and it's responsible for loading, unloading, and managing all game
    modes.
    """

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

        if 'modes' in self.machine.config:
            self.machine.events.add_handler('init_phase_4',
                                            self._load_modes)

        self.machine.events.add_handler('ball_ending', self._ball_ending,
                                        priority=0)

    def _load_modes(self):
        #Loads the modes from the Modes: section of the machine configuration
        #file.

        for mode in self.machine.config['modes']:
            self.machine.game_modes.append(self._load_mode(mode))

    def _load_mode(self, mode_string):
        """Loads a mode, reads in its config, and creates the Mode object.

        Args:
            mode: String name of the mode you're loading. This is the name of
                the mode's folder in your game's machine_files/modes folder.
        """
        self.log.info('Processing mode: %s', mode_string)

        mode_path = os.path.join(self.machine.machine_path,
            self.machine.config['mpf']['paths']['modes'], mode_string)
        mode_config_file = os.path.join(self.machine.machine_path,
            self.machine.config['mpf']['paths']['modes'], mode_string, 'config',
            mode_string + '.yaml')
        config = Config.load_config_yaml(yaml_file=mode_config_file)

        if 'code' in config['mode']:

            import_str = ('modes.' + mode_string + '.code.' +
                          config['mode']['code'].split('.')[0])
            i = __import__(import_str, fromlist=[''])
            mode_object = getattr(i, config['mode']['code'].split('.')[1])(
                self.machine, config, mode_string, mode_path)

        else:
            mode_object = Mode(self.machine, config, mode_string, mode_path)

        return mode_object

    def _ball_ending(self, queue):
        # unloads all the active modes, like when the ball ends

        if not self.active_modes:
            return()

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
            config_section=config_section_name, kwargs=kwargs))

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
            config_section=config_section_name, kwargs=kwargs))

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
        self.name = name.lower()
        self.path = path

        self.log = logging.getLogger('Mode.' + name)

        self.priority = 0
        self._active = False
        self.stop_methods = list()
        self.timers = dict()
        self.start_callback = None
        self.stop_callback = None
        self.event_handlers = set()
        self.player = None
        '''Reference to the current player object.'''

        if 'mode' in self.config:
            self.configure_mode_settings(config['mode'])

        for asset_manager in self.machine.asset_managers.values():

            config_data = self.config.get(asset_manager.config_section, dict())

            self.config[asset_manager.config_section] = (
                asset_manager.register_assets(config=config_data,
                                              mode_path=self.path))

        # Call registered remote loader methods
        for item in self.machine.modes.loader_methods:
            if (item.config_section and
                    item.config_section in self.config and
                    self.config[item.config_section]):
                item.method(config=self.config[item.config_section],
                            mode_path=self.path,
                            **item.kwargs)
            elif not item.config_section:
                item.method(config=self.config, mode_path=self.path,
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
        """Processes this mode's configuration settings from a config
        dictionary.
        """

        if not ('priority' in config and type(config['priority']) is int):
            config['priority'] = 0

        if 'start_events' in config:
            config['start_events'] = Config.string_to_list(
                config['start_events'])
        else:
            config['start_events'] = list()

        if 'stop_events' in config:
            config['stop_events'] = Config.string_to_list(
                config['stop_events'])
        else:
            config['stop_events'] = list()

        # register mode start events
        if 'start_events' in config:
            for event in config['start_events']:
                self.machine.events.add_handler(event, self.start)

        self.config['mode'] = config

    def start(self, priority=None, callback=None, **kwargs):
        """Starts this mode.

        Args:
            priority: Integer value of what you want this mode to run at. If you
                don't specify one, it will use the "Mode: priority" setting from
                this mode's configuration file.
            **kwargs: Catch-all since this mode might start from events with
                who-knows-what keyword arguments.

        Warning: You can safely call this method, but do not override it in your
        mode code. If you want to write your own mode code by subclassing Mode,
        put whatever code you want to run when this mode starts in the
        mode_start method which will be called automatically.
        """

        if self.active or not self.machine.game.player:
            # Only start the mode if it's not already started and there's an
            # active player.
            self.log.debug('Mode Start Aborted')
            return

        self.player = self.machine.game.player

        if type(priority) is int:
            self.priority = priority
        else:
            self.priority = self.config['mode']['priority']

        self.log.info('Mode Starting. Priority: %s', self.priority)

        # register mode stop events
        if 'stop_events' in self.config['mode']:
            for event in self.config['mode']['stop_events']:
                self.add_mode_event_handler(event, self.stop)

        self.start_callback = callback

        if 'timers' in self.config:
            self._setup_timers()

        self.machine.events.post_queue(event='mode_' + self.name + '_starting',
                                       callback=self._started)

    def _started(self):
        # Called after the mode_<name>_starting queue event has finished.

        self.log.info('Mode Started. Priority: %s', self.priority)

        self.active = True

        for item in self.machine.modes.start_methods:
            if item.config_section in self.config:
                self.stop_methods.append(
                    item.method(config=self.config[item.config_section],
                                priority=self.priority,
                                mode=self,
                                **item.kwargs))

        self._start_timers()

        self.machine.events.post('mode_' + self.name + '_started',
                                 callback=self._mode_started_callback)

    def _mode_started_callback(self, **kwargs):
        # Called after the mode_<name>_started queue event has finished.
        self.mode_start()

        if self.start_callback:
            self.start_callback()

    def stop(self, callback=None, **kwargs):
        """Stops this mode.

        Args:
            **kwargs: Catch-all since this mode might start from events with
                who-knows-what keyword arguments.

        Warning: You can safely call this method, but do not override it in your
        mode code. If you want to write your own mode code by subclassing Mode,
        put whatever code you want to run when this mode stops in the
        mode_stop method which will be called automatically.
        """

        if not self.active:
            return

        self.log.debug('Mode Stopping.')

        self._remove_mode_event_handlers()

        self.stop_callback = callback

        self._kill_timers()

        # self.machine.events.remove_handler(self.stop)
        # todo is this ok here? Or should we only remove ones that we know this
        # mode added?

        self.machine.events.post_queue(event='mode_' + self.name + '_stopping',
                                       callback=self._stopped)

    def _stopped(self):

        self.log.debug('Mode Stopped.')

        self.priority = 0
        self.active = False

        for item in self.stop_methods:
            try:
                item[0](item[1])
            except TypeError:
                pass

        self.stop_methods = list()

        self.machine.events.post('mode_' + self.name + '_stopped',
                                 callback=self._mode_stopped_callback)

    def _mode_stopped_callback(self, **kwargs):
        self.mode_stop()

        if self.stop_callback:
            self.stop_callback()

        self.player = None

    def add_mode_event_handler(self, event, handler, priority=1, **kwargs):
        """Registers an event handler which is automatically removed when this
        mode stops.

        This method is similar to the Event Manager's add_handler() method,
        except this method automatically unregisters the handlers when the mode
        ends.

        Args:
            event: String name of the event you're adding a handler for. Since
                events are text strings, they don't have to be pre-defined.
            handler: The method that will be called when the event is fired.
            priority: An arbitrary integer value that defines what order the
                handlers will be called in. The default is 1, so if you have a
                handler that you want to be called first, add it here with a
                priority of 2. (Or 3 or 10 or 100000.) The numbers don't matter.
                They're called from highest to lowest. (i.e. priority 100 is
                called before priority 1.)
            **kwargs: Any any additional keyword/argument pairs entered here
                will be attached to the handler and called whenever that handler
                is called. Note these are in addition to kwargs that could be
                passed as part of the event post. If there's a conflict, the
                event-level ones will win.

        Returns:
            A GUID reference to the handler which you can use to later remove
            the handler via ``remove_handler_by_key``. Though you don't need to
            remove the handler since the whole point of this method is they're
            automatically removed when the mode stops.

        Note that if you do add a handler via this method and then remove it
        manually, that's ok too.
        """

        key = self.machine.events.add_handler(event, handler, priority,
                                              **kwargs)

        self.event_handlers.add(key)

        return key

    def _remove_mode_event_handlers(self):
        for key in self.event_handlers:
            self.machine.events.remove_handler_by_key(key)
        self.event_handlers = set()

    def _setup_timers(self):
        # config is localized

        for timer, settings in self.config['timers'].iteritems():

            self.timers[timer] = ModeTimer(machine=self.machine, mode=self,
                                           name=timer, config=settings)

        return self._kill_timers

    def _start_timers(self):
        for timer in self.timers.values():
            if timer.running:
                timer.start()

    def _kill_timers(self, ):
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
    """Parent class for a mode timer.

    Args:
        machine: The main MPF MachineController object.
        mode: The parent mode object that this timer belongs to.
        name: The string name of this timer.
        config: A Python dictionary which contains the configuration settings
            for this timer.

    """

    def __init__(self, machine, mode, name, config):
        self.machine = machine
        self.mode = mode
        self.name = name
        self.config = config

        self.tick_var = self.mode.name + '_' + self.name + '_tick'
        self.mode.player[self.tick_var] = 0

        self.running = False
        self.start_value = 0
        self.restart_on_complete = False
        self._ticks = 0
        self.end_value = None
        self.ticks_remaining = 0
        self.max_value = None
        self.direction = 'up'
        self.tick_secs = 1
        self.timer = None
        self.bcp = False
        self.event_keys = set()
        self.delay = DelayManager()
        self.log = None

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

        if ('direction' in self.config and
                self.config['direction'].lower() == 'down'):
            self.direction = 'down'

            if not self.end_value:
                self.end_value = 0  # need it to be 0 not None

        if 'tick_interval' in self.config:
            self.tick_secs = Timing.string_to_secs(self.config['tick_interval'])

        if 'max_value' in self.config:
            self.max_value = self.config['max_value']

        if ('restart_on_complete' in self.config and
                self.config['restart_on_complete']):
            self.restart_on_complete = True

        if 'bcp' in self.config and self.config['bcp']:
            self.bcp = True

        if 'debug_logger' in self.config and self.config['debug_logger']:
            self.log = logging.getLogger(self.config['debug_logger'])
            self.log.info("Enabling Debug Logging")

        self.mode.player[self.tick_var] = self.start_value

        if self.log:
            self.log.info("----------- Initial Values -----------")
            self.log.info("running: %s", self.running)
            self.log.info("start_value: %s", self.start_value)
            self.log.info("restart_on_complete: %s", self.restart_on_complete)
            self.log.info("_ticks: %s", self._ticks)
            self.log.info("end_value: %s", self.end_value)
            self.log.info("ticks_remaining: %s", self.ticks_remaining)
            self.log.info("max_value: %s", self.max_value)
            self.log.info("direction: %s", self.direction)
            self.log.info("tick_secs: %s", self.tick_secs)
            self.log.info("--------------------------------------")

        self._setup_control_events(self.config['control_events'])

    def _setup_control_events(self, event_list):

        if self.log:
            self.log.info("Setting up control events")

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

            elif entry['action'] == 'reset':
                handler = self.reset

            elif entry['action'] == 'restart':
                handler = self.restart

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

    def _remove_control_events(self):

        if self.log:
            self.log.info("Removing control events")

        for key in self.event_keys:
            self.machine.events.remove_handler_by_key(key)

    def reset(self, **kwargs):
        """Resets this timer based to the starting value that's already been
        configured. Does not start or stop the timer.

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        if self.log:
            self.log.info("Resetting timer. New value: %s", self.start_value)

        self.set_current_time(self.start_value)

    def start(self, **kwargs):
        """Starts this timer based on the starting value that's already been
        configured. Use set_current_time() if you want to set the starting time
        value.

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        if self.log:
            self.log.info("Starting Timer.")

        if self._check_for_done():
            return()

        self.running = True

        self.delay.remove('pause')
        self._create_system_timer()

        self.machine.events.post('timer_' + self.name + '_started',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_remaining=self.ticks_remaining)

        if self.bcp:
            self.machine.bcp.send('timer', name=self.name, action='started',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_remaining=self.ticks_remaining)

    def restart(self, **kwargs):
        """Restarts the timer by resetting it and then starting it. Essentially
        this is just a reset() then a start()

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.

        """
        self.reset()
        self.start()

    def stop(self, **kwargs):
        """Stops the timer and posts the 'timer_<name>_stopped' event.

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        if self.log:
            self.log.info("Stopping Timer")

        self.delay.remove('pause')

        self.running = False
        self._remove_system_timer()

        self.machine.events.post('timer_' + self.name + '_stopped',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_remaining=self.ticks_remaining)

        if self.bcp:
            self.machine.bcp.send('timer', name=self.name, action='stopped',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_remaining=self.ticks_remaining)

    def pause(self, timer_value=0, **kwargs):
        """Pauses the timer and posts the 'timer_<name>_paused' event

        Args:
            timer_value: How many seconds you want to pause the timer for. Note
                that this pause time is real-world seconds and does not take
                into consideration this timer's tick interval.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        if self.log:
            self.log.info("Pausing Timer for %s secs", timer_value)

        self.running = False

        pause_secs = timer_value

        self._remove_system_timer()
        self.machine.events.post('timer_' + self.name + '_paused',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_remaining=self.ticks_remaining)
        if self.bcp:
            self.machine.bcp.send('timer', name=self.name, action='paused',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_remaining=self.ticks_remaining)

        if pause_secs > 0:
            self.delay.add('pause', pause_secs, self.start)

    def timer_complete(self):
        """Automatically called when this timer completes. Posts the
        'timer_<name>_complete' event. Can be manually called to mark this timer
        as complete.

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        if self.log:
            self.log.info("Timer Complete")

        self.stop()

        if self.bcp:  # must be before the event post in case it stops the mode
            self.machine.bcp.send('timer', name=self.name, action='complete',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_remaining=self.ticks_remaining)

        self.machine.events.post('timer_' + self.name + '_complete',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_remaining=self.ticks_remaining)

        if self.restart_on_complete:

            if self.log:
                self.log.info("Restart on complete: True")

            self.reset()
            self.start()

    def _timer_tick(self):
        # Automatically called by the sytem timer each tick

        if self.log:
            self.log.info("Timer Tick")

        if not self.running:

            if self.log:
                self.log.info("Timer is not running. Will remove.")

            self._remove_system_timer()
            return

        if self.direction == 'down':
            self.mode.player[self.tick_var] -= 1
        else:
            self.mode.player[self.tick_var] += 1

        if not self._check_for_done():
            self.machine.events.post('timer_' + self.name + '_tick',
                                     ticks=self.mode.player[self.tick_var],
                                     ticks_remaining=self.ticks_remaining)

            if self.log:
                self.log.info("Ticks: %s, Remaining: %s",
                              self.mode.player[self.tick_var],
                              self.ticks_remaining)

            if self.bcp:
                self.machine.bcp.send('timer', name=self.name, action='tick',
                                      ticks=self.mode.player[self.tick_var],
                                      ticks_remaining=self.ticks_remaining)

    def add_time(self, timer_value, **kwargs):
        """Adds ticks to this timer.

        Args:
            Args:
            timer_value: The number of ticks you want to add to this timer's
                current value.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        ticks_added = timer_value

        new_value = self.mode.player[self.tick_var] + ticks_added

        if self.max_value and new_value > self.max_value:
            new_value = self.max_value

        self.mode.player[self.tick_var] = new_value
        ticks_added = new_value - timer_value

        self.machine.events.post('timer_' + self.name + '_time_added',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_added=ticks_added,
                                 ticks_remaining=self.ticks_remaining)

        if self.bcp:
            self.machine.bcp.send('timer', name=self.name, action='time_added',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_added=ticks_added,
                                  ticks_remaining=self.ticks_remaining)

        self._check_for_done()

    def subtract_time(self, timer_value, **kwargs):
        """Subracts ticks from this timer.

        Args:
            timer_value: The numebr of ticks you want to subtract from this
                timer's current value.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        ticks_subtracted = timer_value

        self.mode.player[self.tick_var] -= ticks_subtracted

        self.machine.events.post('timer_' + self.name + '_time_subtracted',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_subtracted=ticks_subtracted,
                                 ticks_remaining=self.ticks_remaining)

        if self.bcp:
            self.machine.bcp.send('timer', name=self.name,
                                  action='time_subtracted',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_subtracted=ticks_subtracted,
                                  ticks_remaining=self.ticks_remaining)

        self._check_for_done()

    def _check_for_done(self):
        # Checks to see if this timer is done. Automatically called anytime the
        # timer's value changes.

        if self.log:
            self.log.info("Checking to see if timer is done. Ticks: %s, End "
                          "Value: %s, Direction: %s",
                          self.mode.player[self.tick_var], self.end_value,
                          self.direction)

        if (self.direction == 'up' and self.end_value is not None and
                self.mode.player[self.tick_var] >= self.end_value):
            self.timer_complete()
            return True
        elif (self.direction == 'down' and
                self.mode.player[self.tick_var] <= self.end_value):
            self.timer_complete()
            return True

        if self.end_value is not None:
            self.ticks_remaining = abs(self.end_value -
                                       self.mode.player[self.tick_var])

        if self.log:
            self.log.info("Timer is not done")

        return False

    def _create_system_timer(self):
        # Creates the system timer which drives this mode timer's tick method.
        self._remove_system_timer()
        self.timer = Timer(callback=self._timer_tick, frequency=self.tick_secs)
        self.machine.timing.add(self.timer)

    def _remove_system_timer(self):
        # Removes the system timer associated with this mode timer.
        if self.timer:
            self.machine.timing.remove(self.timer)
            self.timer = None

    def change_tick_interval(self, change=0.0, **kwargs):
        """Changes the interval for each "tick" of this timer.

        Args:
            change: Float or int of the change you want to make to this timer's
                tick rate. Note this value is added to the current tick
                interval. To set an absolute value, use the set_tick_interval()
                method. To shorten the tick rate, use a negative value.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        self.tick_secs *= change
        self._create_system_timer()

    def set_tick_interval(self, timer_value, **kwargs):
        """Sets the number of seconds between ticks for this timer. This is an
        absolute setting. To apply a change to the current value, use the
        change_tick_interval() method.

        Args:
            timer_value: The new number of seconds between each tick of this
                timer. This value should always be positive.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        self.tick_secs = abs(timer_value)
        self._create_system_timer()

    def set_current_time(self, timer_value, **kwargs):
        """Sets the current amount of time of this timer. This value is
        expressed in "ticks" since the interval per tick can be something other
        than 1 second).

        Args:
            timer_value: Integer of the current value you want this timer to be.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        self.mode.player[self.tick_var] = int(timer_value)

        if self.max_value and self.mode.player[self.tick_var] > self.max_value:
            self.mode.player[self.tick_var] = self.max_value

    def kill(self):
        """Stops this timer and also removes all the control events.

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        self.stop()
        self._remove_control_events()


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
