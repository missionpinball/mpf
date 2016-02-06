""" Contains the Mode and ModeTimers parent classes"""

import copy
import logging

from mpf.system.case_insensitive_dict import CaseInsensitiveDict
from mpf.system.timing import Timing, Timer
from mpf.system.tasks import DelayManager

# todo
# override player var
# override event strings
from mpf.system.utility_functions import Util


class Mode(object):
    """Parent class for in-game mode code."""

    def __init__(self, machine, config, name, path):
        self.machine = machine
        self.config = config
        self.name = name.lower()
        self.path = path

        self.log = logging.getLogger('Mode.' + name)

        self.delay = DelayManager(self.machine.delayRegistry)

        self.priority = 0
        self._active = False
        self._mode_start_wait_queue = None
        self.stop_methods = list()
        self.timers = dict()
        self.start_callback = None
        self.stop_callback = None
        self.event_handlers = set()
        self.switch_handlers = list()
        self.mode_start_kwargs = dict()
        self.mode_stop_kwargs = dict()
        self.mode_devices = set()

        self.player = None
        '''Reference to the current player object.'''

        self._validate_mode_config()

        self.configure_mode_settings(config.get('mode', dict()))

        self.auto_stop_on_ball_end = self.config['mode']['stop_on_ball_end']
        '''Controls whether this mode is stopped when the ball ends,
        regardless of its stop_events settings.
        '''

        self.restart_on_next_ball = self.config['mode']['restart_on_next_ball']
        '''Controls whether this mode will restart on the next ball. This only
        works if the mode was running when the ball ended. It's tracked per-
        player in the '_restart_modes_on_next_ball' untracked player variable.
        '''

        # for asset_manager in list(self.machine.asset_managers.values()):
        #
        #     config_data = self.config.get(asset_manager.config_section, dict())
        #
        #     self.config[asset_manager.config_section] = (
        #         asset_manager.register_assets(config=config_data,
        #                                       mode_path=self.path))

        # Call registered remote loader methods
        for item in self.machine.mode_controller.loader_methods:
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

    def __repr__(self):
        return '<Mode.{}>'.format(self.name)

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        if self._active != active:
            self._active = active
            self.machine.mode_controller._active_change(self, self._active)

    def configure_mode_settings(self, config):
        """Processes this mode's configuration settings from a config
        dictionary.
        """

        self.config['mode'] = self.machine.config_processor.process_config2(
            config_spec='mode', source=config, section_name='mode')

        for event in self.config['mode']['start_events']:
            self.machine.events.add_handler(event=event, handler=self.start,
                priority=self.config['mode']['priority'] +
                self.config['mode']['start_priority'])

    def _validate_mode_config(self):
        for section in self.machine.config['mpf']['mode_config_sections']:
            this_section = self.config.get(section, None)

            if this_section:
                if type(this_section) is dict:
                    for device, settings in this_section.items():
                        self.config[section][device] = (
                            self.machine.config_processor.process_config2(
                                section, settings))

                else:
                    self.config[section] = (
                        self.machine.config_processor.process_config2(section,
                        this_section))

    def _get_merged_settings(self, section_name):
        # Returns a dict_merged dict of a config section from the machine-wide
        # config with the mode-specific config merged in.

        if section_name in self.machine.config:
            return_dict = copy.deepcopy(self.machine.config[section_name])
        else:
            return_dict = CaseInsensitiveDict()

        if section_name in self.config:
            return_dict = Util.dict_merge(return_dict,
                                          self.config[section_name],
                                          combine_lists=False)

        return return_dict

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

        self.log.debug("Received request to start")

        if self._active:
            self.log.debug("Mode is already active. Aborting start")
            return

        if self.config['mode']['use_wait_queue'] and 'queue' in kwargs:

            self.log.debug("Registering a mode start wait queue")

            self._mode_start_wait_queue = kwargs['queue']
            self._mode_start_wait_queue.wait()

        if type(priority) is int:
            self.priority = priority
        else:
            self.priority = self.config['mode']['priority']

        self.start_event_kwargs = kwargs

        self.log.info('Mode Starting. Priority: %s', self.priority)

        self._create_mode_devices()

        self.log.debug("Registering mode_stop handlers")

        # register mode stop events
        if 'stop_events' in self.config['mode']:

            for event in self.config['mode']['stop_events']:
                # stop priority is +1 so if two modes of the same priority
                # start and stop on the same event, the one will stop before
                # the other starts
                self.add_mode_event_handler(event=event, handler=self.stop,
                    priority=self.priority + 1 +
                    self.config['mode']['stop_priority'])

        self.start_callback = callback

        if 'timers' in self.config:
            self._setup_timers()

        self.log.debug("Calling mode_start handlers")

        for item in self.machine.mode_controller.start_methods:
            if item.config_section in self.config or not item.config_section:
                self.stop_methods.append(
                    item.method(config=self.config.get(item.config_section,
                                                       self.config),
                                priority=self.priority,
                                mode=self,
                                **item.kwargs))

        self._setup_device_control_events()

        self.machine.events.post_queue(event='mode_' + self.name + '_starting',
                                       callback=self._started)

    def _started(self):
        # Called after the mode_<name>_starting queue event has finished.

        self.log.debug('Mode Started. Priority: %s', self.priority)

        self.active = True

        self._start_timers()

        self.machine.events.post('mode_' + self.name + '_started',
                                 callback=self._mode_started_callback)

    def _mode_started_callback(self, **kwargs):
        # Called after the mode_<name>_started queue event has finished.
        self.mode_start(**self.start_event_kwargs)

        self.start_event_kwargs = dict()

        if self.start_callback:
            self.start_callback()

        self.log.debug('Mode Start process complete.')

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

        if not self._active:
            return

        self.mode_stop_kwargs = kwargs

        self.log.debug('Mode Stopping.')

        self._remove_mode_switch_handlers()

        self.stop_callback = callback

        self._kill_timers()
        self.delay.clear()

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
                try:
                    item()
                except TypeError:
                    pass

        self.stop_methods = list()

        self.machine.events.post('mode_' + self.name + '_stopped',
                                 callback=self._mode_stopped_callback)

        if self._mode_start_wait_queue:

            self.log.debug("Clearing wait queue")

            self._mode_start_wait_queue.clear()
            self._mode_start_wait_queue = None

    def _mode_stopped_callback(self, **kwargs):
        self._remove_mode_event_handlers()
        self._remove_mode_devices()

        self.mode_stop(**self.mode_stop_kwargs)

        self.mode_stop_kwargs = dict()

        if self.stop_callback:
            self.stop_callback()

    def _create_mode_devices(self):
        # Creates new devices that are specified in a mode config that haven't
        # been created in the machine-wide config

        self.log.debug("Scanning config for mode-based devices")

        for collection_name, device_class in (
                iter(self.machine.device_manager.device_classes.items())):
            if device_class.config_section in self.config:
                for device, settings in (
                        iter(self.config[device_class.config_section].items())):

                    collection = getattr(self.machine, collection_name)

                    if device not in collection:  # no existing device, create

                        self.log.debug("Creating mode-based device: %s",
                                       device)

                        # TODO this config is already validated, so add
                        # something so it doesn't validate it again?

                        self.machine.device_manager.create_devices(
                            collection.name, {device: settings},
                            validate=False)

                        # change device from str to object
                        device = collection[device]

                        # Track that this device was added via this mode so we
                        # can remove it when the mode ends.
                        self.mode_devices.add(device)

                        # This lets the device know it was created by a mode
                        # instead of machine-wide, as some devices want to do
                        # certain things here. We also pass the player object
                        # in case this device wants to do something with that
                        # too.
                        device.device_added_to_mode(mode=self,
                                                    player=self.player)

    def _remove_mode_devices(self):

        for device in self.mode_devices:
            device.remove()

        self.mode_devices = set()

    def _setup_device_control_events(self):
        # registers mode handlers for control events for all devices specified
        # in this mode's config (not just newly-created devices)

        self.log.debug("Scanning mode-based config for device control_events")

        device_list = set()

        for event, method, delay, device in (
                self.machine.device_manager.get_device_control_events(
                self.config)):

            try:
                event, priority = event.split('|')
            except ValueError:
                priority = 0

            self.add_mode_event_handler(
                event=event,
                handler=self._control_event_handler,
                priority=self.priority + 2 + int(priority),
                callback=method,
                ms_delay=delay)

            device_list.add(device)

        for device in device_list:
            device.control_events_in_mode(self)

    def _control_event_handler(self, callback, ms_delay=0, **kwargs):

        self.log.debug("_control_event_handler: callback: %s,", callback)

        if ms_delay:
            self.delay.add(name=callback, ms=ms_delay, callback=callback,
                           mode=self)
        else:
            callback(mode=self)

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
                                              mode=self, **kwargs)

        self.event_handlers.add(key)

        return key

    def _remove_mode_event_handlers(self):
        for key in self.event_handlers:
            self.machine.events.remove_handler_by_key(key)
        self.event_handlers = set()

    def _remove_mode_switch_handlers(self):
        for handler in self.switch_handlers:
            self.machine.switch_controller.remove_switch_handler(
                switch_name=handler['switch_name'],
                callback=handler['callback'],
                state=handler['state'],
                ms=handler['ms'])
        self.switch_handlers = list()

    def _setup_timers(self):
        # config is localized

        for timer, settings in self.config['timers'].items():

            self.timers[timer] = ModeTimer(machine=self.machine, mode=self,
                                           name=timer, config=settings)

        return self._kill_timers

    def _start_timers(self):
        for timer in list(self.timers.values()):
            if timer.running:
                timer.start()

    def _kill_timers(self, ):
        for timer in list(self.timers.values()):
            timer.kill()

        self.timers = dict()

    def mode_init(self):
        """User-overrideable method which will be called when this mode
        initializes as part of the MPF boot process.
        """
        pass

    def mode_start(self, **kwargs):
        """User-overrideable method which will be called whenever this mode
        starts (i.e. whenever it becomes active).
        """
        pass

    def mode_stop(self, **kwargs):
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
        self.delay = DelayManager(self.machine.delayRegistry)
        self.log = None
        self.debug = False

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
            self.tick_secs = Timing.string_to_secs(self.config[
                                                       'tick_interval'])

        if 'max_value' in self.config:
            self.max_value = self.config['max_value']

        if ('restart_on_complete' in self.config and
                self.config['restart_on_complete']):
            self.restart_on_complete = True

        if 'bcp' in self.config and self.config['bcp']:
            self.bcp = True

        if 'debug' in self.config and self.config['debug']:
            self.debug = True
            self.log.debug("Enabling Debug Logging")

        self.mode.player[self.tick_var] = self.start_value

        if self.log:
            self.log.debug("----------- Initial Values -----------")
            self.log.debug("running: %s", self.running)
            self.log.debug("start_value: %s", self.start_value)
            self.log.debug("restart_on_complete: %s", self.restart_on_complete)
            self.log.debug("_ticks: %s", self._ticks)
            self.log.debug("end_value: %s", self.end_value)
            self.log.debug("ticks_remaining: %s", self.ticks_remaining)
            self.log.debug("max_value: %s", self.max_value)
            self.log.debug("direction: %s", self.direction)
            self.log.debug("tick_secs: %s", self.tick_secs)
            self.log.debug("--------------------------------------")

        self._setup_control_events(self.config['control_events'])

    def _setup_control_events(self, event_list):

        if self.debug:
            self.log.debug("Setting up control events")

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

        if self.debug:
            self.log.debug("Removing control events")

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

        if self.debug:
            self.log.debug("Resetting timer. New value: %s", self.start_value)

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

        if self.debug:
            self.log.debug("Starting Timer.")

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

        if self.debug:
            self.log.debug("Stopping Timer")

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

        if self.debug:
            self.log.debug("Pausing Timer for %s secs", timer_value)

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
            self.delay.add(name='pause', ms=pause_secs, callback=self.start)

    def timer_complete(self, **kwargs):
        """Automatically called when this timer completes. Posts the
        'timer_<name>_complete' event. Can be manually called to mark this timer
        as complete.

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """

        if self.debug:
            self.log.debug("Timer Complete")

        self.stop()

        if self.bcp:  # must be before the event post in case it stops the mode
            self.machine.bcp.send('timer', name=self.name, action='complete',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_remaining=self.ticks_remaining)

        self.machine.events.post('timer_' + self.name + '_complete',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_remaining=self.ticks_remaining)

        if self.restart_on_complete:

            if self.debug:
                self.log.debug("Restart on complete: True")

            self.reset()
            self.start()

    def _timer_tick(self, dt):
        # Automatically called by the system clock each tick

        if self.debug:
            self.log.debug("Timer Tick")

        if not self.running:

            if self.debug:
                self.log.debug("Timer is not running. Will remove.")

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

            if self.debug:
                self.log.debug("Ticks: %s, Remaining: %s",
                              self.mode.player[self.tick_var],
                              self.ticks_remaining)

            if self.bcp:
                self.machine.bcp.send('timer', name=self.name, action='tick',
                                      ticks=self.mode.player[self.tick_var],
                                      ticks_remaining=self.ticks_remaining)

    def add_time(self, timer_value, **kwargs):
        """Adds ticks to this timer.

        Args:
            timer_value: The number of ticks you want to add to this timer's
                current value.
            kwargs: Not used in this method. Only exists since this method is
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
        """Subtracts ticks from this timer.

        Args:
            timer_value: The number of ticks you want to subtract from this
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

        if self.debug:
            self.log.debug("Checking to see if timer is done. Ticks: %s, End "
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

        if self.debug:
            self.log.debug("Timer is not done")

        return False

    def _create_system_timer(self):
        # Creates the clock event which drives this mode timer's tick method.
        self._remove_system_timer()
        self.timer = self.machine.clock.schedule_interval(self._timer_tick, self.tick_secs)

    def _remove_system_timer(self):
        # Removes the clock event associated with this mode timer.
        if self.timer:
            self.machine.clock.unschedule(self.timer)
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
