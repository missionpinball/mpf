"""Contains the Mode base class."""
import copy
import logging

from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.delays import DelayManager

from mpf.core.mode_timer import ModeTimer
from mpf.core.utility_functions import Util


# pylint: disable-msg=too-many-instance-attributes
class Mode(object):

    """Parent class for in-game mode code."""

    def __init__(self, machine, config: dict, name: str, path):
        """Initialise mode.

        Args:
            machine(mpf.core.machine.MachineController): the machine controller
            config: config dict for mode
            name: name of mode
            path: path of mode

        Returns:

        """
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
        self.mode_stop_kwargs = dict()
        self.mode_devices = set()
        self.start_event_kwargs = None

        self.player = None
        '''Reference to the current player object.'''

        self._create_mode_devices()

        self._validate_mode_config()

        self._initialise_mode_devices()

        self.configure_mode_settings(config.get('mode', dict()))

        self.auto_stop_on_ball_end = self.config['mode']['stop_on_ball_end']
        '''Controls whether this mode is stopped when the ball ends,
        regardless of its stop_events settings.
        '''

        self.restart_on_next_ball = self.config['mode']['restart_on_next_ball']
        '''Controls whether this mode will restart on the next ball. This only
        works if the mode was running when the ball ended. It's tracked per-
        player in the 'restart_modes_on_next_ball' player variable.
        '''

        # Call registered remote loader methods
        for item in self.machine.mode_controller.loader_methods:
            if (item.config_section and
                    item.config_section in self.config and
                    self.config[item.config_section]):
                item.method(config=self.config[item.config_section],
                            mode_path=self.path,
                            mode=self,
                            root_config_dict=self.config,
                            **item.kwargs)
            elif not item.config_section:
                item.method(config=self.config, mode_path=self.path,
                            **item.kwargs)

        self.mode_init()

    @staticmethod
    def get_config_spec():
        """Return config spec for mode_settings."""
        return '''
                __valid_in__: mode
                __allow_others__:
                '''

    def __repr__(self):
        """Return string representation."""
        return '<Mode.{}>'.format(self.name)

    @property
    def active(self):
        """Return true if mode is active."""
        return self._active

    @active.setter
    def active(self, active):
        """Setter for _active."""
        if self._active != active:
            self._active = active
            self.machine.mode_controller.set_mode_state(self, self._active)

    def configure_mode_settings(self, config):
        """Process this mode's configuration settings from a config dictionary."""
        self.config['mode'] = self.machine.config_validator.validate_config(
            config_spec='mode', source=config, section_name='mode')

        for event in self.config['mode']['start_events']:
            self.machine.events.add_handler(event=event, handler=self.start,
                                            priority=self.config['mode']['priority'] +
                                            self.config['mode']['start_priority'])

    def _validate_mode_config(self):
        """Validate mode config."""
        for section in self.machine.config['mpf']['mode_config_sections']:
            this_section = self.config.get(section, None)

            # do not double validate devices
            if section in self.machine.device_manager.device_classes:
                continue

            if this_section:
                if isinstance(this_section, dict):
                    for device, settings in this_section.items():
                        self.config[section][device] = (
                            self.machine.config_validator.validate_config(
                                section, settings, "mode:" + self.name))

                else:
                    self.config[section] = (self.machine.config_validator.validate_config(section, this_section))

    def _get_merged_settings(self, section_name):
        """Return a dict of a config section from the machine-wide config with the mode-specific config merged in."""
        if section_name in self.machine.config:
            return_dict = copy.deepcopy(self.machine.config[section_name])
        else:
            return_dict = CaseInsensitiveDict()

        if section_name in self.config:
            return_dict = Util.dict_merge(return_dict,
                                          self.config[section_name],
                                          combine_lists=False)

        return return_dict

    def start(self, mode_priority=None, callback=None, **kwargs):
        """Start this mode.

        Args:
            mode_priority: Integer value of what you want this mode to run at. If you
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

        if isinstance(mode_priority, int):
            self.priority = mode_priority
        else:
            self.priority = self.config['mode']['priority']

        self.start_event_kwargs = kwargs

        self.log.info('Mode Starting. Priority: %s', self.priority)

        self._add_mode_devices()

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
        '''event: mode_(name)_starting

        desc: The mode called "name" is starting.

        This is a queue event. The mode will not fully start until the queue is
        cleared.
        '''

    def _started(self):
        """Called after the mode_<name>_starting queue event has finished."""
        self.log.debug('Mode Started. Priority: %s', self.priority)

        self.active = True

        if 'timers' in self.config:
            self._setup_timers()

        self._start_timers()

        self.machine.events.post('mode_' + self.name + '_started',
                                 callback=self._mode_started_callback)
        '''event: mode_(name)_started

        desc: Posted when a mode has started. The "name" part is replaced
        with the actual name of the mode, so the actual event posted is
        something like *mode_attract_started*, *mode_base_started*, etc.

        This is posted after the "mode_(name)_starting" event.
        '''

    def _mode_started_callback(self, **kwargs):
        """Called after the mode_<name>_started queue event has finished."""
        del kwargs
        self.mode_start(**self.start_event_kwargs)

        self.start_event_kwargs = dict()

        if self.start_callback:
            self.start_callback()

        self.log.debug('Mode Start process complete.')

    def stop(self, callback=None, **kwargs):
        """Stop this mode.

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
        '''event: mode_(name)_stopping

        The mode called "name" is stopping. This is a queue event. The
        mode won't actually stop until the queue is cleared.

        '''

    def _stopped(self):
        self.log.debug('Mode Stopped.')

        self.priority = 0
        self.active = False

        for callback in self.machine.mode_controller.stop_methods:
            callback[0](self)

        for item in self.stop_methods:
            item[0](item[1])

        self.stop_methods = list()

        self.machine.events.post('mode_' + self.name + '_stopped',
                                 callback=self._mode_stopped_callback)
        '''event: mode_(name)_stopped

        desc: Posted when a mode has stopped. The "name" part is replaced
        with the actual name of the mode, so the actual event posted is
        something like *mode_attract_stopped*, *mode_base_stopped*, etc.
        '''

        self.machine.events.post('clear', key=self.name)
        '''event: clear

        args:
            key: string name of the configs to clear

        desc: Posted to cause config players to clear whatever they're running
            based on the key passed. Typically posted when a show or mode ends.
        '''

        if self._mode_start_wait_queue:

            self.log.debug("Clearing wait queue")

            self._mode_start_wait_queue.clear()
            self._mode_start_wait_queue = None

    def _mode_stopped_callback(self, **kwargs):
        del kwargs
        self._remove_mode_event_handlers()
        self._remove_mode_devices()

        self.mode_stop(**self.mode_stop_kwargs)

        self.mode_stop_kwargs = dict()

        if self.stop_callback:
            self.stop_callback()

    def _add_mode_devices(self):
        # adds and initializes mode devices which get removed at the end of the mode

        for collection_name, device_class in (
                iter(self.machine.device_manager.device_classes.items())):

            # check if there is config for the device type
            if device_class.config_section in self.config:

                for device_name in self.config[device_class.config_section]:

                    collection = getattr(self.machine, collection_name)

                    # get device
                    device = collection[device_name]

                    # Track that this device was added via this mode so we
                    # can remove it when the mode ends.
                    self.mode_devices.add(device)

                    # This lets the device know it was added to a mode
                    device.device_added_to_mode(mode=self,
                                                player=self.player)

    def _create_mode_devices(self):
        """Create new devices that are specified in a mode config that haven't been created in the machine-wide."""
        self.log.debug("Scanning config for mode-based devices")

        for collection_name, device_class in iter(self.machine.device_manager.device_classes.items()):

            # check if there is config for the device type
            if device_class.config_section not in self.config:
                continue

            # check if it is supposed to be used in mode
            if collection_name not in self.machine.config['mpf']['mode_config_sections']:
                raise AssertionError("Found config for device {} in mode {} which may not be used in modes".format(
                    collection_name, self.name
                ))

            for device, settings in iter(self.config[device_class.config_section].items()):

                collection = getattr(self.machine, collection_name)

                if device not in collection:  # no existing device, create

                    self.log.debug("Creating mode-based device: %s",
                                   device)

                    self.machine.device_manager.create_devices(
                        collection.name, {device: settings})

    def _initialise_mode_devices(self):
        """Initialise new devices that are specified in a mode config."""

        for collection_name, device_class in iter(self.machine.device_manager.device_classes.items()):

            # check if there is config for the device type
            if device_class.config_section not in self.config:
                continue

            for device, settings in iter(self.config[device_class.config_section].items()):

                collection = getattr(self.machine, collection_name)
                device = collection[device]
                if device.config:
                    self.log.debug("Overwrite mode-based device: %s", device)
                    # TODO: implement this
                    # 1. check if the device allows this
                    # 2. validate overload section
                    self.config[collection_name][device.name] = device.validate_and_parse_config(settings, True)
                    # 3. load overload

                else:
                    self.log.debug("Initialising mode-based device: %s", device)

                    # prepare config for mode
                    settings = device.prepare_config(settings, True)
                    settings = device.validate_and_parse_config(settings, True)

                    # load config
                    device.load_config(settings)

    def _remove_mode_devices(self):
        for device in self.mode_devices:
            device.device_removed_from_mode(self)

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
            device.add_control_events_in_mode(self)

    def _control_event_handler(self, callback, ms_delay=0, **kwargs):
        del kwargs
        self.log.debug("_control_event_handler: callback: %s,", callback)

        if ms_delay:
            self.delay.add(name=callback, ms=ms_delay, callback=callback,
                           mode=self)
        else:
            callback(mode=self)

    def add_mode_event_handler(self, event, handler, priority=1, **kwargs):
        """Register an event handler which is automatically removed when this mode stops.

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
        key = self.machine.events.add_handler(event, handler, priority, mode=self, **kwargs)

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
        """User-overrideable method which will be called when this mode initializes as part of the MPF boot process."""
        pass

    def mode_start(self, **kwargs):
        """User-overrideable method which will be called whenever this mode starts (i.e. whenever it becomes active)."""
        pass

    def mode_stop(self, **kwargs):
        """User-overrideable method which will be called whenever this mode stops."""
        pass
