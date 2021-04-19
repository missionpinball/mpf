# pylint: disable-msg=too-many-lines
"""Contains the MachineController base class."""
import asyncio
import logging
import sys
import threading
from typing import Any, Callable, Dict, List, Set, Optional

from pkg_resources import iter_entry_points

from mpf._version import __version__
from mpf.core.clock import ClockBase
from mpf.core.config_validator import ConfigValidator
from mpf.core.data_manager import DataManager
from mpf.core.delays import DelayManager
from mpf.core.device_manager import DeviceCollection
from mpf.core.logging import LogMixin
from mpf.core.machine_vars import MachineVariables
from mpf.core.utility_functions import Util
from mpf.core.config_loader import MpfConfig

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.modes.game.code.game import Game   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.events import EventManager    # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.switch_controller import SwitchController     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.show_controller import ShowController     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.service_controller import ServiceController   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.light_controller import LightController   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.platform_controller import PlatformController     # pylint: disable-msg=cyclic-import,unused-import

    from mpf.core.custom_code import CustomCode     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.mode_controller import ModeController     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.settings_controller import SettingsController     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.bcp.bcp import Bcp    # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.text_ui import TextUi     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.assets.show import Show    # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.switch import Switch   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.driver import Driver   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.mode import Mode  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.ball_device.ball_device import BallDevice  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.ball_controller import BallController     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.playfield import Playfield     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.placeholder_manager import PlaceholderManager     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.platforms.smart_virtual import SmartVirtualHardwarePlatform    # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.core.device_manager import DeviceManager   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.plugins.auditor import Auditor     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.light import Light     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.accelerometer import Accelerometer     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.drop_target import DropTarget, DropTargetBank  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.logic_blocks import Accrual, Sequence, Counter     # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.devices.servo import Servo     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.segment_display import SegmentDisplay      # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.shot_group import ShotGroup    # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.shot import Shot   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.motor import Motor     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.digital_output import DigitalOutput    # pylint: disable-msg=cyclic-import,unused-import
    from logging import Logger  # noqa
    from mpf.devices.autofire import AutofireCoil   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.stepper import Stepper     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.config_players.show_player import ShowPlayer   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.dmd import Dmd     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.rgb_dmd import RgbDmd  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.flipper import Flipper     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.diverter import Diverter   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.multiball_lock import MultiballLock    # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.multiball import Multiball     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.ball_hold import BallHold      # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.ball_save import BallSave      # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.magnet import Magnet           # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.state_machine import StateMachine  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.extra_ball import ExtraBall    # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.extra_ball_group import ExtraBallGroup     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.achievement_group import AchievementGroup  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.achievement import Achievement     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.combo_switch import ComboSwitch    # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.score_queue import ScoreQueue      # pylint: disable-msg=cyclic-import,unused-import


# pylint: disable-msg=too-many-instance-attributes
class MachineController(LogMixin):

    """Base class for the Machine Controller object.

    The machine controller is the main entity of the entire framework. It's the
    main part that's in charge and makes things happen.

    Args:
    ----
        config(MpfConfig): The machine configuration
        options(dict): A dictionary of options built from the command line options
            used to launch mpf.py.
    """

    __slots__ = ["log", "options", "mpf_path", "machine_path", "_exception", "_boot_holds",
                 "is_init_done", "_done", "monitors", "plugins", "custom_code", "modes", "game",
                 "variables", "thread_stopper", "config", "config_validator",
                 "delay", "hardware_platforms", "default_platform", "clock",
                 "stop_future", "events", "switch_controller", "mode_controller", "settings",
                 "bcp", "ball_controller", "show_controller", "placeholder_manager", "device_manager", "auditor",
                 "tui", "service", "switches", "shows", "coils", "ball_devices", "lights", "playfield", "playfields",
                 "autofire_coils", "_crash_handlers", "__dict__", "mpf_config", "is_shutting_down"]

    # pylint: disable-msg=too-many-statements
    def __init__(self, options: dict, config: MpfConfig) -> None:
        """Initialize machine controller."""
        super().__init__()
        self.log = logging.getLogger("Machine")     # type: Logger
        self.log.info("Mission Pinball Framework Core Engine v%s", __version__)
        self._crash_handlers = []   # type: List[Callable]
        self.is_shutting_down = False

        self.log.info("Command line arguments: %s", options)
        self.options = options

        self.mpf_path = config.get_mpf_path()
        self.log.info("MPF path: %s", self.mpf_path)

        self.machine_path = config.get_machine_path()
        self.log.info("Machine path: %s", self.machine_path)

        self.verify_system_info()
        self._exception = None      # type: Any
        self._boot_holds = set()    # type: Set[str]
        self.is_init_done = None    # type: Optional[asyncio.Event]

        self._done = False
        self.monitors = dict()      # type: Dict[str, Set[Callable]]
        self.plugins = list()       # type: List[Any]
        self.custom_code = list()   # type: List[CustomCode]
        self.modes = DeviceCollection(self, 'modes', None)          # type: Dict[str, Mode]
        self.game = None            # type: Optional[Game]
        self.thread_stopper = threading.Event()

        self.config = config.get_machine_config()       # type: Any
        self.mpf_config = config                        # type: MpfConfig
        self.config_validator = ConfigValidator(self, self.mpf_config.get_config_spec())

        self.variables = MachineVariables(self)  # type: MachineVariables

        # add some type hints
        if MYPY:   # pragma: no cover
            # controllers
            self.events = self.events                               # type: EventManager
            self.switch_controller = self.switch_controller         # type: SwitchController
            self.mode_controller = self.mode_controller             # type: ModeController
            self.settings = self.settings                           # type: SettingsController
            self.bcp = self.bcp                                     # type: Bcp
            self.ball_controller = self.ball_controller             # type: BallController
            self.show_controller = self.show_controller             # type: ShowController
            self.placeholder_manager = self.placeholder_manager     # type: PlaceholderManager
            self.device_manager = self.device_manager               # type: DeviceManager
            self.auditor = self.auditor                             # type: Auditor
            self.tui = self.tui                                     # type: TextUi
            self.service = self.service                             # type: ServiceController
            self.show_player = self.show_player                     # type: ShowPlayer
            self.light_controller = self.light_controller           # type: LightController
            self.platform_controller = self.platform_controller     # type: PlatformController

            # devices
            self.autofire_coils = {}                    # type: Dict[str, AutofireCoil]
            self.motors = {}                            # type: Dict[str, Motor]
            self.digital_outputs = {}                   # type: Dict[str, DigitalOutput]
            self.shows = {}                             # type: Dict[str, Show]
            self.shots = {}                             # type: Dict[str, Shot]
            self.shot_groups = {}                       # type: Dict[str, ShotGroup]
            self.switches = {}                          # type: Dict[str, Switch]
            self.steppers = {}                          # type: Dict[str, Stepper]
            self.coils = {}                             # type: Dict[str, Driver]
            self.lights = {}                            # type: Dict[str, Light]
            self.ball_devices = {}                      # type: Dict[str, BallDevice]
            self.accelerometers = {}                    # type: Dict[str, Accelerometer]
            self.playfield = None                       # type: Optional[Playfield]
            self.playfields = {}                        # type: Dict[str, Playfield]
            self.counters = {}                          # type: Dict[str, Counter]
            self.sequences = {}                         # type: Dict[str, Sequence]
            self.accruals = {}                          # type: Dict[str, Accrual]
            self.drop_targets = {}                      # type: Dict[str, DropTarget]
            self.drop_target_banks = {}                 # type: Dict[str, DropTargetBank]
            self.servos = {}                            # type: Dict[str, Servo]
            self.segment_displays = {}                  # type: Dict[str, SegmentDisplay]
            self.dmds = {}                              # type: Dict[str, Dmd]
            self.rgb_dmds = {}                          # type: Dict[str, RgbDmd]
            self.flippers = {}                          # type: Dict[str, Flipper]
            self.diverters = {}                         # type: Dict[str, Diverter]
            self.multiball_locks = {}                   # type: Dict[str, MultiballLock]
            self.multiballs = {}                        # type: Dict[str, Multiball]
            self.ball_holds = {}                        # type: Dict[str, BallHold]
            self.ball_saves = {}                        # type: Dict[str, BallSave]
            self.magnets = {}                           # type: Dict[str, Magnet]
            self.state_machines = {}                    # type: Dict[str, StateMachine]
            self.extra_balls = {}                       # type: Dict[str, ExtraBall]
            self.extra_ball_groups = {}                 # type: Dict[str, ExtraBallGroup]
            self.achievements = {}                      # type: Dict[str, Achievement]
            self.achievement_groups = {}                # type: Dict[str, AchievementGroup]
            self.combo_switches = {}                    # type: Dict[str, ComboSwitch]
            self.score_queues = {}                      # type: Dict[str, ScoreQueue]

        self._set_machine_path()

        self.configure_logging(
            'Machine',
            self.config['logging']['console']['machine_controller'],
            self.config['logging']['file']['machine_controller'])

        self.delay = DelayManager(self)

        self.hardware_platforms = dict()    # type: Dict[str, SmartVirtualHardwarePlatform]
        self.default_platform = None        # type: Optional[SmartVirtualHardwarePlatform]

        self.clock = self._load_clock()
        self.stop_future = asyncio.Future()     # type: asyncio.Future

    def add_crash_handler(self, handler: Callable):
        """Add a crash handler which is called on a crash.

        This can be used to restore the output and prepare logging.
        """
        self._crash_handlers.append(handler)

    async def initialise_core_and_hardware(self) -> None:
        """Load core modules and hardware."""
        self._boot_holds = set()
        self.is_init_done = asyncio.Event()
        self.register_boot_hold('init')
        self._load_hardware_platforms()

        self._load_core_modules()
        # order is specified in mpfconfig.yaml

        self._validate_config()

        # This is called so hw platforms have a chance to register for events,
        # and/or anything else they need to do with core modules since
        # they're not set up yet when the hw platforms are constructed.
        await self._initialize_platforms()

    async def initialise(self) -> None:
        """Initialise machine."""
        await self.initialise_core_and_hardware()

        self._initialize_credit_string()

        self._register_config_players()
        self._register_system_events()
        self._load_machine_vars()
        await self._run_init_phases()
        self._init_phases_complete()

        await self._start_platforms()

        # wait until all boot holds were released
        assert self.is_init_done is not None
        await self.is_init_done.wait()
        await self.init_done()

    def _exception_handler(self, loop, context):    # pragma: no cover
        """Handle asyncio loop exceptions."""
        # call original exception handler
        loop.set_exception_handler(None)
        loop.call_exception_handler(context)

        # remember exception
        self._exception = context
        self.stop("Exception thrown")

    # pylint: disable-msg=no-self-use
    def _load_clock(self) -> ClockBase:  # pragma: no cover
        """Load clock and loop."""
        clock = ClockBase(self)
        clock.loop.set_exception_handler(self._exception_handler)
        return clock

    async def _run_init_phases(self) -> None:
        """Run init phases."""
        await self.events.post_queue_async("init_phase_1")
        '''event: init_phase_1

        desc: Posted during the initial boot up of MPF.
        '''
        await self.events.post_queue_async("init_phase_2")
        '''event: init_phase_2

        desc: Posted during the initial boot up of MPF.
        '''
        self._load_plugins()
        await self.events.post_queue_async("init_phase_3")
        '''event: init_phase_3

        desc: Posted during the initial boot up of MPF.
        '''
        self._load_custom_code()

        await self.events.post_queue_async("init_phase_4")
        '''event: init_phase_4

        desc: Posted during the initial boot up of MPF.
        '''

        await self.events.post_queue_async("init_phase_5")
        '''event: init_phase_5

        desc: Posted during the initial boot up of MPF.
        '''

    def _init_phases_complete(self, **kwargs) -> None:
        """Cleanup after init and remove boot holds."""
        del kwargs
        self.events.remove_all_handlers_for_event("init_phase_1")
        self.events.remove_all_handlers_for_event("init_phase_2")
        self.events.remove_all_handlers_for_event("init_phase_3")
        self.events.remove_all_handlers_for_event("init_phase_4")
        self.events.remove_all_handlers_for_event("init_phase_5")

        self.clear_boot_hold('init')

    async def _initialize_platforms(self) -> None:
        """Initialise all used hardware platforms."""
        init_done = []
        # collect all platform init futures
        for hardware_platform in list(self.hardware_platforms.values()):
            init_done.append(hardware_platform.initialize())

        # wait for all of them in parallel
        results = await asyncio.wait(init_done)
        for result in results[0]:
            result.result()

    async def _start_platforms(self) -> None:
        """Start all used hardware platforms."""
        for hardware_platform in list(self.hardware_platforms.values()):
            await hardware_platform.start()
            if not hardware_platform.features['tickless']:
                self.clock.schedule_interval(hardware_platform.tick, 1 / self.config['mpf']['default_platform_hz'])

    def _initialize_credit_string(self):
        """Set default credit string."""
        # Do this here so there's a credit_string var even if they're not using
        # the credits mode
        try:
            credit_string = self.config['credits']['free_play_string']
        except KeyError:
            credit_string = 'FREE PLAY'

        self.variables.set_machine_var('credits_string', credit_string)
        '''machine_var: credits_string

        desc: Holds a displayable string which shows how many
        credits are on the machine. For example, "CREDITS: 1". If the machine
        is set to free play, the value of this string will be "FREE PLAY".

        You can change the format and value of this string in the ``credits:``
        section of the machine config file.
        '''

    def _validate_config(self) -> None:
        """Validate game and machine config."""
        self.validate_machine_config_section('machine')
        self.validate_machine_config_section('game')
        self.validate_machine_config_section('mpf')

    def validate_machine_config_section(self, section: str) -> None:
        """Validate a config section."""
        if section not in self.config_validator.get_config_spec():
            return

        if section not in self.config:
            self.config[section] = dict()

        self.config[section] = self.config_validator.validate_config(
            section, self.config[section], section)

    def _register_system_events(self) -> None:
        """Register default event handlers."""
        self.events.add_handler('quit', self.stop)
        self.events.add_handler(self.config['mpf']['switch_tag_event'].
                                replace('%', 'quit'), self.stop)

    def _register_config_players(self) -> None:
        """Register config players."""
        # todo move this to config_player module
        for name, module_class in self.config['mpf']['config_players'].items():
            config_player_class = Util.string_to_class(module_class)
            setattr(self, '{}_player'.format(name),
                    config_player_class(self))

        self._register_plugin_config_players()

    def _register_plugin_config_players(self):
        """Register plugin config players."""
        self.debug_log("Registering Plugin Config Players")
        for entry_point in iter_entry_points(group='mpf.config_player',
                                             name=None):
            self.debug_log("Registering %s", entry_point)
            name, player = entry_point.load()(self)
            setattr(self, '{}_player'.format(name), player)

    def create_data_manager(self, config_name: str) -> DataManager:     # pragma: no cover
        """Return a new DataManager for a certain config.

        Args:
        ----
            config_name: Name of the config
        """
        return DataManager(self, config_name)

    def _load_machine_vars(self) -> None:
        """Load machine vars from data manager."""
        machine_var_data_manager = self.create_data_manager('machine_vars')
        current_time = self.clock.get_time()

        self.variables.load_machine_vars(machine_var_data_manager, current_time)

    def _set_machine_path(self) -> None:
        """Add the machine folder to sys.path so we can import modules from it."""
        sys.path.insert(0, self.machine_path)

    def verify_system_info(self):
        """Dump information about the Python installation to the log.

        Information includes Python version, Python executable, platform, and
        core architecture.
        """
        python_version_info = sys.version_info

        if not (python_version_info[0] == 3 and python_version_info[1] in (5, 6, 7, 8, 9)):
            raise AssertionError("Incorrect Python version. MPF requires "
                                 "Python 3.5, 3.6, 3.7, 3.8 or 3.9. You have Python {}.{}.{}."
                                 .format(python_version_info[0], python_version_info[1],
                                         python_version_info[2]))

        self.log.info("Platform: %s", sys.platform)
        self.log.info("Python executable location: %s", sys.executable)

        if sys.maxsize < 2**32:
            self.log.info("Python version: %s.%s.%s (32-bit)", python_version_info[0],
                          python_version_info[1], python_version_info[2])
        else:
            self.log.info("Python version: %s.%s.%s (64-bit)", python_version_info[0],
                          python_version_info[1], python_version_info[2])

    def _load_core_modules(self) -> None:
        """Load core modules."""
        self.debug_log("Loading core modules...")
        for name, module_class in self.config['mpf']['core_modules'].items():
            self.debug_log("Loading '%s' core module", module_class)
            m = Util.string_to_class(module_class)(self)
            setattr(self, name, m)

    def _load_hardware_platforms(self) -> None:
        """Load all hardware platforms."""
        self.validate_machine_config_section('hardware')

        # load internal platforms
        self.add_platform("drivers")

        # if platform is forced use that one
        if self.options['force_platform']:
            self.add_platform(self.options['force_platform'])
            self.set_default_platform(self.options['force_platform'])
            return

        # otherwise load all platforms
        for section, platforms in self.config['hardware'].items():
            if section == 'driverboards':
                continue
            for hardware_platform in platforms:
                if hardware_platform.lower() != 'default':
                    self.add_platform(hardware_platform)

        # set default platform
        self.set_default_platform(self.config['hardware']['platform'][0])

    def _load_plugins(self) -> None:
        """Load plugins."""
        self.debug_log("Loading plugins...")

        for plugin in self.config['mpf']['plugins']:

            self.debug_log("Loading '%s' plugin", plugin)

            plugin_obj = Util.string_to_class(plugin)(self)
            self.plugins.append(plugin_obj)

    def _load_custom_code(self) -> None:
        """Load custom code."""
        if 'scriptlets' in self.config:
            self.debug_log("Loading scriptlets (deprecated).")
            for scriptlet in Util.string_to_event_list(self.config['scriptlets']):
                self.debug_log("Loading '%s' scriptlet (deprecated)", scriptlet)
                scriptlet_obj = Util.string_to_class(self.config['mpf']['paths']['scriptlets'] + "." + scriptlet)(
                    machine=self,
                    name=scriptlet.split('.')[1])
                self.custom_code.append(scriptlet_obj)

        if 'custom_code' in self.config:
            self.debug_log("Loading custom code.")

            for custom_code in Util.string_to_event_list(self.config['custom_code']):

                self.debug_log("Loading '%s' custom code", custom_code)

                custom_code_obj = Util.string_to_class(custom_code)(
                    machine=self,
                    name=custom_code)

                self.custom_code.append(custom_code_obj)

    async def reset(self) -> None:
        """Reset the machine.

        This method is safe to call. It essentially sets up everything from
        scratch without reloading the config files and assets from disk. This
        method is called after a game ends and before attract mode begins.
        """
        self.debug_log('Resetting...')

        await self.events.post_queue_async('machine_reset_phase_1')
        '''Event: machine_reset_phase_1

        Desc: The first phase of resetting the machine.

        These events are posted when MPF boots (after the init_phase events are
        posted), and they're also posted subsequently when the machine is reset
        (after existing the service mode, for example).

        This is a queue event. The machine reset phase 1 will not be complete
        until the queue is cleared.

        '''

        await self.events.post_queue_async('machine_reset_phase_2')
        '''Event: machine_reset_phase_2

        Desc: The second phase of resetting the machine.

        These events are posted when MPF boots (after the init_phase events are
        posted), and they're also posted subsequently when the machine is reset
        (after existing the service mode, for example).

        This is a queue event. The machine reset phase 2 will not be complete
        until the queue is cleared.

        '''

        await self.events.post_queue_async('machine_reset_phase_3')
        '''Event: machine_reset_phase_3

        Desc: The third phase of resetting the machine.

        These events are posted when MPF boots (after the init_phase events are
        posted), and they're also posted subsequently when the machine is reset
        (after existing the service mode, for example).

        This is a queue event. The machine reset phase 3 will not be complete
        until the queue is cleared.

        '''

        """Called when the machine reset process is complete."""
        self.debug_log('Reset Complete')
        await self.events.post_async('reset_complete')
        '''event: reset_complete

        desc: The machine reset process is complete

        '''

    def add_platform(self, name: str) -> None:
        """Make an additional hardware platform interface available to MPF.

        Args:
        ----
            name: String name of the platform to add. Must match the name of a
                platform file in the mpf/platforms folder (without the .py
                extension).
        """
        if name not in self.hardware_platforms:
            if name in self.config['mpf']['platforms']:
                # if platform is in config load it
                try:
                    hardware_platform = Util.string_to_class(self.config['mpf']['platforms'][name])
                except ImportError as e:  # pragma: no cover
                    if e.name != name:  # do not swallow unrelated errors
                        raise
                    raise ImportError("Cannot add hardware platform {}. This is "
                                      "not a valid platform name".format(name))

            else:
                # check entry points
                entry_points = list(iter_entry_points(group='mpf.platforms', name=name))
                if entry_points:
                    # load platform from entry point
                    self.debug_log("Loading platform %s from external entry_point", name)
                    if len(entry_points) != 1:
                        raise AssertionError("Got more than one entry point for platform {}: {}".format(name,
                                                                                                        entry_points))

                    hardware_platform = entry_points[0].load()
                else:
                    raise AssertionError("Unknown platform {}".format(name))

            self.hardware_platforms[name] = hardware_platform(self)

    def set_default_platform(self, name: str) -> None:
        """Set the default platform.

        It is used if a device class-specific or device-specific platform is not specified.

        Args:
        ----
            name: String name of the platform to set to default.
        """
        try:
            self.default_platform = self.hardware_platforms[name]
            self.debug_log("Setting default platform to '%s'", name)
        except KeyError:
            raise AssertionError("Cannot set default platform to '{}', as that's not"
                                 " a currently active platform".format(name))

    def register_monitor(self, monitor_class: str, monitor: Callable[..., Any]) -> None:
        """Register a monitor.

        Args:
        ----
            monitor_class: String name of the monitor class for this monitor
                that's being registered.
            monitor: Callback to notify

        MPF uses monitors to allow components to monitor certain internal
        elements of MPF.

        For example, a player variable monitor could be setup to be notified of
        any changes to a player variable, or a switch monitor could be used to
        allow a plugin to be notified of any changes to any switches.

        The MachineController's list of registered monitors doesn't actually
        do anything. Rather it's a dictionary of sets which the monitors
        themselves can reference when they need to do something. We just needed
        a central registry of monitors.

        """
        if monitor_class not in self.monitors:
            self.monitors[monitor_class] = set()

        self.monitors[monitor_class].add(monitor)

    def initialise_mpf(self):
        """Initialise MPF."""
        self.info_log("Initialise MPF.")
        timeout = 30 if self.options["production"] else None
        try:
            init = asyncio.ensure_future(self.initialise())
            self.clock.loop.run_until_complete(Util.first([init, self.stop_future], cancel_others=False,
                                                          timeout=timeout))
        except asyncio.TimeoutError:
            self._crash_shutdown()
            self.error_log("MPF needed more than {}s for initialisation. Aborting!".format(timeout))
            return False
        except RuntimeError:
            self._crash_shutdown()
            # do not show a runtime useless runtime error
            self.error_log("Failed to initialise MPF")
            return False
        if init.done() and init.exception():
            self._crash_shutdown()
            try:
                raise init.exception()
            except:     # noqa
                self.log.exception("Failed to initialise MPF")
            return False

        return True

    def run(self) -> None:
        """Start the main machine run loop."""
        if not self.initialise_mpf():
            return

        self.info_log("Starting the main run loop.")
        self._run_loop()

    def stop(self, reason=None, **kwargs) -> None:
        """Perform a graceful exit of MPF."""
        del kwargs
        if self.stop_future.done():
            return

        self.clock.loop.call_soon_threadsafe(self._stop_loop, reason)

    def _stop_loop(self, reason):
        self.stop_future.set_result(reason)

    def _do_stop(self) -> None:
        self.is_shutting_down = True
        self.log.info("Shutting down...")
        self.events.post('shutdown')
        '''event: shutdown
        desc: Posted when the machine is shutting down to give all modules a
        chance to shut down gracefully.

        '''

        self.events.process_event_queue()
        self.shutdown()

    def _crash_shutdown(self):
        """MPF crashed. Cleanup as good as we can."""
        # call crash handlers
        for handler in self._crash_handlers:
            handler()
        if hasattr(self, "events") and hasattr(self, "clock"):
            # if we already got events and a clock use normal shutdown
            self._do_stop()
        else:
            # otherwise just shutdown
            self.shutdown()

    def shutdown(self) -> None:
        """Shutdown the machine."""
        self.thread_stopper.set()
        if hasattr(self, "device_manager"):
            self.device_manager.stop_devices()
        self._platform_stop()

        self.clock.loop.stop()
        # this is needed to properly close all sockets
        self.clock.loop.run_forever()
        self.clock.loop.close()

    def _run_loop(self) -> None:    # pragma: no cover
        # Main machine run loop with when the default platform interface
        # specifies the MPF should control the main timer

        try:
            reason = self.clock.run(self.stop_future)
        except KeyboardInterrupt:
            print("Shutdown because of keyboard interrupts")
            return
        except BaseException:   # pylint: disable-msg=broad-except
            # this happens when receiving a signal
            self.log.exception("Loop exited with exception")
            return

        if self._exception:
            self._crash_shutdown()

            print("Shutdown because of an exception:")
            try:
                raise self._exception['exception']
            except:     # noqa
                self.log.exception("Runtime Exception")
        else:
            self._do_stop()
            print("Shutdown reason: {}".format(reason))

    def _platform_stop(self) -> None:
        """Stop all platforms."""
        for hardware_platform in list(self.hardware_platforms.values()):
            hardware_platform.stop()

    def get_platform_sections(self, platform_section: str, overwrite: str) -> "SmartVirtualHardwarePlatform":
        """Return platform section."""
        assert self.default_platform is not None
        if overwrite == "drivers":
            return self.hardware_platforms[overwrite]

        if self.options['force_platform']:
            return self.default_platform

        if not overwrite:
            if self.config['hardware'][platform_section][0] != 'default':
                return self.hardware_platforms[self.config['hardware'][platform_section][0]]

            return self.default_platform

        try:
            return self.hardware_platforms[overwrite]
        except KeyError:
            raise AssertionError("Platform \"{}\" has not been loaded. Please add it to your \"hardware\" section.".
                                 format(overwrite))

    def register_boot_hold(self, hold: str) -> None:
        """Register a boot hold."""
        assert self.is_init_done is not None
        if self.is_init_done.is_set():
            raise AssertionError("Register hold after init_done")
        self._boot_holds.add(hold)

    def clear_boot_hold(self, hold: str) -> None:
        """Clear a boot hold."""
        assert self.is_init_done is not None
        if self.is_init_done.is_set():
            raise AssertionError("Clearing hold after init_done")
        self._boot_holds.remove(hold)
        self.debug_log('Clearing boot hold %s. Holds remaining: %s', hold, self._boot_holds)
        if not self._boot_holds:
            self.is_init_done.set()

    async def init_done(self) -> None:
        """Finish init.

        Called when init is done and all boot holds are cleared.
        """
        await self.events.post_async("init_done")
        '''event: init_done

        desc: Posted when the initial (one-time / boot) init phase is done. In
        other words, once this is posted, MPF is booted and ready to go.
        '''

        await self.reset()
