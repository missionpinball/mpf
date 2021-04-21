"""Contains the Mode base class."""
from typing import Any, Optional, Union
from typing import Callable
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple

from mpf.core.delays import DelayManager
from mpf.core.logging import LogMixin
from mpf.core.switch_controller import SwitchHandler
from mpf.core.events import EventHandlerKey
from mpf.core.events import QueuedEvent  # pylint: disable-msg=cyclic-import,unused-import

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.mode_device import ModeDevice     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.player import Player  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


# pylint: disable-msg=too-many-instance-attributes
class Mode(LogMixin):

    """Base class for a mode."""

    __slots__ = ["machine", "config", "name", "path", "priority", "_active", "_starting", "_mode_start_wait_queue",
                 "stop_methods", "start_callback", "stop_callbacks", "event_handlers", "switch_handlers",
                 "mode_stop_kwargs", "mode_devices", "start_event_kwargs", "stopping", "delay", "player",
                 "auto_stop_on_ball_end", "restart_on_next_ball", "asset_paths"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, machine: "MachineController", config, name: str, path, asset_paths) -> None:
        """Initialise mode.

        Args:
        ----
            machine: the machine controller
            config: config dict for mode
            name: name of mode
            path: path of mode
            asset_paths: all paths to consider for assets in this mode
        """
        super().__init__()
        self.machine = machine                  # type: MachineController
        self.config = config                    # type: ignore
        self.name = name
        self.path = path
        self.asset_paths = asset_paths
        self.priority = 0
        self._active = False
        self._starting = False
        self._mode_start_wait_queue = None      # type: Optional[QueuedEvent]
        self.stop_methods = list()              # type: List[Tuple[Callable[[Any], None], Any]]
        self.start_callback = None              # type: Optional[Callable[[], None]]
        self.stop_callbacks = []                # type: List[Callable[[], None]]
        self.event_handlers = set()             # type: Set[EventHandlerKey]
        self.switch_handlers = list()           # type: List[SwitchHandler]
        self.mode_stop_kwargs = dict()          # type: Dict[str, Any]
        self.mode_devices = set()               # type: Set[ModeDevice]
        self.start_event_kwargs = {}            # type: Dict[str, Any]
        self.stopping = False

        self.delay = DelayManager(self.machine)
        '''DelayManager instance for delays in this mode. Note that all delays
        scheduled here will be automatically canceled when the mode stops.'''

        self.player = None                      # type: Optional[Player]
        '''Reference to the current player object.'''

        self.configure_logging('Mode.' + name,
                               self.config['mode']['console_log'],
                               self.config['mode']['file_log'])

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

        if self.config['mode']['game_mode'] and not self.config['mode']['stop_on_ball_end']:
            self.raise_config_error("All game modes need to stop at ball end. If you want to set stop_on_ball_end to "
                                    "False also set game_mode to False.", 1)

    @staticmethod
    def get_config_spec() -> Union[str, dict]:
        """Return config spec for mode_settings."""
        return {'__valid_in__': 'mode', '__allow_others__': ''}

    def __repr__(self):
        """Return string representation."""
        return '<Mode.{}>'.format(self.name)

    @property
    def active(self) -> bool:
        """Return *True* if this mode is active."""
        return self._active

    @active.setter
    def active(self, new_active: bool):
        """Setter for _active."""
        if self._active != new_active:
            self._active = new_active
            self.machine.mode_controller.set_mode_state(self, self._active)

    def configure_mode_settings(self, config: dict) -> None:
        """Process this mode's configuration settings from a config dictionary."""
        self.config['mode'] = self.machine.config_validator.validate_config(
            config_spec='mode', source=config, section_name='mode')

        for event in self.config['mode']['start_events']:
            self.machine.events.add_handler(event=event, handler=self.start,
                                            priority=self.config['mode']['priority'] +
                                            self.config['mode']['start_priority'])

    @property
    def is_game_mode(self) -> bool:
        """Return true if this is a game mode."""
        return bool(self.config['mode']['game_mode'])

    def start(self, mode_priority=None, callback=None, **kwargs) -> None:
        """Start this mode.

        Args:
        ----
            mode_priority: Integer value of what you want this mode to run at. If you
                don't specify one, it will use the "Mode: priority" setting from
                this mode's configuration file.
            callback: Callback to call when this mode has been started.
            **kwargs: Catch-all since this mode might start from events with
                who-knows-what keyword arguments.

        Warning: You can safely call this method, but do not override it in your
        mode code. If you want to write your own mode code by subclassing Mode,
        put whatever code you want to run when this mode starts in the
        mode_start method which will be called automatically.
        """
        # remove argument so we do not repost this
        kwargs.pop('_from_bcp', None)
        self.debug_log("Received request to start")

        if self.config['mode']['game_mode'] and not (self.machine.game and self.player):
            self.warning_log("Can only start mode %s during a game. Aborting start.", self.name)
            return

        if self._active:
            self.debug_log("Mode is already active. Aborting start.")
            return

        if self._starting:
            self.debug_log("Mode already starting. Aborting start.")
            return

        self._starting = True

        self.machine.events.post('mode_{}_will_start'.format(self.name), **kwargs)
        '''event: mode_(name)_will_start

        desc: Posted when a mode is about to start. The "name" part is replaced
        with the actual name of the mode, so the actual event posted is
        something like *mode_attract_will_start*, *mode_base_will_start*, etc.

        This is posted before the "mode_(name)_starting" event.
        '''

        if self.config['mode']['use_wait_queue'] and 'queue' in kwargs:

            self.debug_log("Registering a mode start wait queue")

            self._mode_start_wait_queue = kwargs['queue']
            assert isinstance(self._mode_start_wait_queue, QueuedEvent)
            self._mode_start_wait_queue.wait()

        if isinstance(mode_priority, int):
            self.priority = mode_priority
        else:
            self.priority = self.config['mode']['priority']

        self.start_event_kwargs = kwargs

        # hook for custom code. called before any mode devices are set up
        self.mode_will_start(**self.start_event_kwargs)

        self._add_mode_devices()

        self.debug_log("Registering mode_stop handlers")

        # register mode stop events
        if 'stop_events' in self.config['mode']:

            for event in self.config['mode']['stop_events']:
                # stop priority is +1 so if two modes of the same priority
                # start and stop on the same event, the one will stop before
                # the other starts
                self.add_mode_event_handler(event=event, handler=self.stop,
                                            priority=self.config['mode']['stop_priority'] + 1)

        self.start_callback = callback

        self.debug_log("Calling mode_start handlers")

        for item in self.machine.mode_controller.start_methods:
            if item.config_section in self.config or not item.config_section:
                result = item.method(config=self.config.get(item.config_section, self.config),
                                     priority=self.priority,
                                     mode=self,
                                     **item.kwargs)
                if result:
                    self.stop_methods.append(result)

        self._setup_device_control_events()

        self.machine.events.post_queue(event='mode_{}_starting'.format(self.name),
                                       callback=self._started, **kwargs)
        '''event: mode_(name)_starting

        desc: The mode called "name" is starting.

        This is a queue event. The mode will not fully start until the queue is
        cleared.
        '''

    def _started(self, **kwargs) -> None:
        """Handle result of mode_<name>_starting queue event."""
        del kwargs
        if self.machine.is_shutting_down:
            self.info_log("Will not start because machine is shutting down.")
            return

        self.info_log('Started. Priority: %s', self.priority)

        self.active = True
        self._starting = False

        for event_name in self.config['mode']['events_when_started']:
            self.machine.events.post(event_name)

        self.machine.events.post(event='mode_{}_started'.format(self.name), callback=self._mode_started_callback,
                                 **self.start_event_kwargs)
        '''event: mode_(name)_started

        desc: Posted when a mode has started. The "name" part is replaced
        with the actual name of the mode, so the actual event posted is
        something like *mode_attract_started*, *mode_base_started*, etc.

        This is posted after the "mode_(name)_starting" event.
        '''

    def _mode_started_callback(self, **kwargs) -> None:
        """Handle result of mode_<name>_started queue event."""
        del kwargs
        self.mode_start(**self.start_event_kwargs)

        self.start_event_kwargs = dict()

        if self.start_callback:
            self.start_callback()

        self.debug_log('Mode Start process complete.')

    def stop(self, callback: Any = None, **kwargs) -> bool:
        """Stop this mode.

        Args:
        ----
            callback: Method which will be called once this mode has stopped. Will only be called when the mode is
                running (includes currently stopping)
            **kwargs: Catch-all since this mode might start from events with
                who-knows-what keyword arguments.

        Warning: You can safely call this method, but do not override it in your
        mode code. If you want to write your own mode code by subclassing Mode,
        put whatever code you want to run when this mode stops in the
        mode_stop method which will be called automatically.

        Returns true if the mode is running. Otherwise false.
        """
        if not self._active:
            return False

        if callback:
            self.stop_callbacks.append(callback)

        # do not stop twice. only register callback in that case
        if self.stopping:
            # mode is still running
            return True

        self.machine.events.post('mode_' + self.name + '_will_stop')
        '''event: mode_(name)_will_stop

        desc: Posted when a mode is about to stop. The "name" part is replaced
        with the actual name of the mode, so the actual event posted is
        something like *mode_attract_will_stop*, *mode_base_will_stop*, etc.

        This is posted immediately before the "mode_(name)_stopping" event.
        '''

        self.stopping = True

        self.mode_stop_kwargs = kwargs

        self.debug_log('Mode Stopping.')

        self._remove_mode_switch_handlers()

        self.delay.clear()

        self.machine.events.post_queue(event='mode_' + self.name + '_stopping',
                                       callback=self._stopped)
        '''event: mode_(name)_stopping

        desc: The mode called "name" is stopping. This is a queue event. The
        mode won't actually stop until the queue is cleared.

        '''
        return True

    def _stopped(self) -> None:
        self.info_log('Stopped.')

        self.priority = 0
        self.active = False
        self.stopping = False

        for item in self.stop_methods:
            item[0](item[1])

        self.stop_methods = list()

        for event_name in self.config['mode']['events_when_stopped']:
            self.machine.events.post(event_name)

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

            self.debug_log("Clearing wait queue")

            self._mode_start_wait_queue.clear()
            self._mode_start_wait_queue = None

    def _mode_stopped_callback(self, **kwargs) -> None:
        del kwargs

        # Call the mode_stop() method before removing the devices
        self.mode_stop(**self.mode_stop_kwargs)
        self.mode_stop_kwargs = dict()

        # Clean up the mode handlers and devices
        self._remove_mode_event_handlers()
        self._remove_mode_devices()

        for callback in self.stop_callbacks:
            callback()

        self.stop_callbacks = []

    def _add_mode_devices(self) -> None:
        """Add and initialize mode devices which get removed at the end of the mode."""
        for config_key, config in self.config.items():
            if config_key not in self.machine.config['mpf']['device_modules']:
                continue

            collection = getattr(self.machine, config_key)
            for device_name in config.keys():
                device = collection[device_name]
                # Track that this device was added via this mode so we
                # can remove it when the mode ends.
                self.mode_devices.add(device)
                if not self.config['mode']['game_mode'] and not device.can_exist_outside_of_game:
                    raise AssertionError("Device {} cannot exist in non game-mode {}.".format(
                        device, self.name
                    ))

                # This lets the device know it was added to a mode
                device.device_loaded_in_mode(mode=self, player=self.player)

    def create_mode_devices(self) -> None:
        """Create new devices that are specified in a mode config that haven't been created in the machine-wide."""
        self.debug_log("Scanning config for mode-based devices")

        for config_key, config in self.config.items():
            if config_key not in self.machine.config['mpf']['device_modules']:
                continue

            collection = getattr(self.machine, config_key)
            for device, settings in config.items():
                if device not in collection:
                    # no existing device, create
                    self.debug_log("Creating mode-based device: %s",
                                   device)

                    self.machine.device_manager.create_devices(
                        collection.name, {device: settings})

    async def load_mode_devices(self) -> None:
        """Load config of mode devices."""
        for config_key, config in self.config.items():
            if config_key not in self.machine.config['mpf']['device_modules']:
                continue

            collection = getattr(self.machine, config_key)
            for device, settings in config.items():
                device = collection[device]
                settings = device.prepare_config(settings, True)
                settings = device.validate_and_parse_config(settings, True, "mode:" + self.name)

                if device.config:
                    self.debug_log("Overwrite mode-based device: %s", device)
                    # overload
                    device.overload_config_in_mode(self, settings)

                else:
                    self.debug_log("Initializing mode-based device: %s", device)
                    # load config
                    device.load_config(settings)

        for config_key, config in self.config.items():
            if config_key not in self.machine.config['mpf']['device_modules']:
                continue

            collection = getattr(self.machine, config_key)
            for device, settings in config.items():
                device = collection[device]
                await device.device_added_to_mode(mode=self)

    def _remove_mode_devices(self) -> None:
        for device in self.mode_devices:
            device.device_removed_from_mode(self)

        self.mode_devices = set()

    def _setup_device_control_events(self) -> None:
        # registers mode handlers for control events for all devices specified
        # in this mode's config (not just newly-created devices)

        self.debug_log("Scanning mode-based config for device control_events")

        for event, method, delay, device in (
                self.machine.device_manager.get_device_control_events(
                self.config)):

            if not delay:
                self.add_mode_event_handler(
                    event=event,
                    handler=method,
                    blocking_facility=device.class_label)
            else:
                self.add_mode_event_handler(
                    event=event,
                    handler=self._control_event_handler,
                    callback=method,
                    ms_delay=delay,
                    blocking_facility=device.class_label)

        # get all devices in the mode
        device_list = set()     # type: Set[ModeDevice]
        for collection in self.machine.device_manager.collections:
            if self.machine.device_manager.collections[collection].config_section in self.config:
                for device, _ in \
                        iter(self.config[self.machine.device_manager.collections[collection].config_section].items()):
                    device_list.add(self.machine.device_manager.collections[collection][device])

        for device in device_list:
            device.add_control_events_in_mode(self)

    def _control_event_handler(self, callback: Callable[..., None], ms_delay: int = 0, **kwargs) -> None:
        del kwargs
        self.debug_log("_control_event_handler: callback: %s,", callback)

        self.delay.add(ms=ms_delay, callback=callback, mode=self)

    def add_mode_event_handler(self, event: str, handler: Callable, priority: int = 0, **kwargs) -> EventHandlerKey:
        """Register an event handler which is automatically removed when this mode stops.

        This method is similar to the Event Manager's add_handler() method,
        except this method automatically unregisters the handlers when the mode
        ends.

        Args:
        ----
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

        Returns a EventHandlerKey to the handler which you can use to later remove
        the handler via ``remove_handler_by_key``. Though you don't need to
        remove the handler since the whole point of this method is they're
        automatically removed when the mode stops.

        Note that if you do add a handler via this method and then remove it
        manually, that's ok too.
        """
        key = self.machine.events.add_handler(event, handler, self.priority + priority, mode=self, **kwargs)

        self.event_handlers.add(key)

        return key

    def _remove_mode_event_handlers(self) -> None:
        for key in self.event_handlers:
            self.machine.events.remove_handler_by_key(key)
        self.event_handlers = set()

    def _remove_mode_switch_handlers(self) -> None:
        for handler in self.switch_handlers:
            self.machine.switch_controller.remove_switch_handler_by_key(handler)
        self.switch_handlers = list()

    def initialise_mode(self) -> None:
        """Initialise this mode."""
        self.mode_init()

    def mode_init(self) -> None:
        """User-overrideable method which will be called when this mode initializes as part of the MPF boot process."""

    def mode_will_start(self, **kwargs) -> None:
        """User-overrideable method which will be called whenever this mode starts (i.e. before it becomes active)."""

    def mode_start(self, **kwargs) -> None:
        """User-overrideable method which will be called whenever this mode starts (i.e. whenever it becomes active)."""

    def mode_stop(self, **kwargs) -> None:
        """User-overrideable method which will be called whenever this mode stops."""
