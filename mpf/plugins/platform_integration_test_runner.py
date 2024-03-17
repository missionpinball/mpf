"""Test framework for testing physical platform integration."""

import asyncio
from datetime import datetime

from mpf.core.delays import DelayManager
from mpf.core.plugin import MpfPlugin
from mpf.core.utility_functions import Util


class MpfPlatformIntegrationTestRunner(MpfPlugin):

    """Runs a Platform Integration test provided by the command line.

    mpf -pit path_to/test_file.py
        -or-
    mpf -pit path.to.ModuleFile.ModuleClassName
    """

    __slots__ = ("delay", "_task", "_keep_alive", "_start_time", "_test_obj",
                 "trough_switches")

    def __init__(self, *args, **kwargs):
        """Initialize the test runner."""
        super().__init__(*args, **kwargs)
        self._keep_alive = None
        self._task = None
        self._test_obj = None
        self._start_time = None
        self.delay = None
        self.trough_switches = None

    @property
    def is_plugin_enabled(self):
        """Enable this plugin by the '-pit' command line arg."""
        return self.machine.options["platform_integration_test"]

    def initialize(self):
        """Initialize test runner and load test module."""
        self.configure_logging('MpfPlatformIntegration', 'basic', 'full')
        self.info_log("Initializing Platform Integration Test: Arg value is %s",
                      self.machine.options["platform_integration_test"])
        self.delay = DelayManager(self.machine)

        # Find the file with the test
        test_file = self.machine.options["platform_integration_test"]
        # If a path to a python file is found, convert it to a module path
        # This requires the import class to be the PascalCase version
        # of the python file's snake_case name.
        if test_file.endswith(".py"):
            parts = test_file.split("/")
            parts[-1] = parts[-1][:-3]
            parts.append(Util.snake_to_pascal(parts[-1]))
            test_file = ".".join(parts)

        self.info_log("Trying to import from module '%s'", test_file)
        # Look for a file path
        self._test_obj = Util.string_to_class(test_file)(self)

        # Wait until init phase 3 to setup test
        self.machine.events.add_handler("init_phase_3", self._setup_test)

    def keep_alive(self, value=True):
        """Configure whether the test runner will keep the MPF instance running after the test run finishes."""
        self._keep_alive = value

    def _setup_test(self, **kwargs):
        del kwargs
        self.machine.events.remove_handler(self._setup_test)

        # Create an event handler to begin the test run
        self.machine.events.add_handler(self._test_obj.test_start_event, self._run_test)

        self.trough_switches = []
        for ball_device in self.machine.ball_devices.items_tagged('trough'):
            jam_switch = ball_device.config.get('jam_switch')
            for s in Util.string_to_list(ball_device.config["ball_switches"]):
                if s != jam_switch:
                    self.trough_switches.append(s)

        # Pre-set initial switches defined in the test
        if self._test_obj.initial_switches is not None:
            for s in self._test_obj.initial_switches:
                # If a tuple is provided, the second value is the target state
                if type(s) == tuple:
                    s, s_state = s
                else:
                    s_state = 1
                if self.machine.switches[s].invert:
                    s_state ^= 1
                self.machine.switch_controller.process_switch(s, s_state)
            # Recheck all the ball counts
            for ball_device in self.machine.ball_devices.values():
                if hasattr(ball_device, "ball_count_handler"):
                    self.info_log("Resetting ball count for %s", ball_device)
                    ball_device.ball_count_handler.counter.trigger_recount()
                    ball_device.ball_count_handler._count_valid.clear()
        # Pre-fill the trough with balls if no initial switches are defined
        else:
            for s in self.trough_switches:
                s_state = 0 if self.machine.switches[s].invert else 1
                self.info_log("Initializing trough switch %s", s)
                self.machine.switch_controller.process_switch(s, s_state)
            self.info_log("Re-initializing trough ball counts")
            for ball_device in self.machine.ball_devices.items_tagged('trough'):
                ball_device.ball_count_handler.counter.trigger_recount()
            self.machine.ball_controller.num_balls_known = len(self.trough_switches)

    def _run_test(self, **kwargs):
        del kwargs
        self.machine.events.remove_handler(self._run_test)
        self.log.info("Running platform integration test!")
        self._start_time = datetime.now()
        for playfield in self.machine.playfields.values():
            playfield.ball_search.disable()
        self._task = asyncio.create_task(self._test_obj.run_test())
        self._task.add_done_callback(self._stop_callback)

    def _stop_callback(self, future):
        Util.raise_exceptions(future)

        if self._task:
            self._task.cancel()
            self._task = None
        duration = datetime.now() - self._start_time
        msg = f"All tests completed successfully in {duration.seconds}.{duration.microseconds // 1000} seconds."
        if not self._keep_alive:
            self.machine.stop(msg)
        else:
            self.info_log("%s Keep Alive is enabled, runner will not exit game." % msg)

    def disable_ball_search(self):
        """Disable ball search."""
        for playfield in self.machine.playfields.values():
            playfield.ball_search.disable()

    def disable_ball_saves(self):
        """Disable all ball saves."""
        for ball_save in self.machine.ball_saves.values():
            ball_save.disable()

    def accelerate_high_score(self):
        """If there is a high score mode and the test achieves a high score, accelerate the text entry timeout."""
        if hasattr(self.machine.modes, "high_score"):
            self.machine.modes.high_score.high_score_config['enter_initials_timeout'] = 2

    def set_switch_sync(self, switch_name, state):
        """Set a switch to a given state, synchronously."""
        if state is None:
            state = int(not self.machine.switches[switch_name].state)
        if self.machine.switches[switch_name].invert:
            state ^= 1
        self.delay.remove(switch_name)
        self.info_log("Setting switch %s to state %s", switch_name, state)
        self.machine.switch_controller.process_switch(switch_name, state)

    async def wait_for_event(self, event, timeout=None, continue_on_timeout=False):
        """Wait for an event to be posted within a given timeout (secs)."""
        try:
            await asyncio.wait_for(self.machine.events.wait_for_event(event), timeout)
            self.info_log(f"Successfully caught event '{event}'")
            return True
        except asyncio.TimeoutError:
            if continue_on_timeout:
                return False
            self.machine.stop_with_exception({
                "exception": AssertionError(f"Awaited event '{event}' failed to trigger within {timeout}s.")
            })

    # pylint: disable-msg=too-many-arguments
    async def set_switch(self, switch_name, state=None, duration_secs=None, wait_after=None, blocking=True):
        """Set a switch to a given state.

        Parameters
        ----------
            - duration_secs: Number of seconds to hold the switch in that state. If none, will switch indefinitely.
            - wait_after: Number of seconds to wait after the switch before returning
            - blocking: If true, will wait for duration_secs before returning. If false, will fire-and-forget.
        """
        self.set_switch_sync(switch_name, state)
        if duration_secs:
            # Blocking mode: await the duration before returning
            if blocking:
                self.info_log(f" - waiting {duration_secs}s to toggle back switch {switch_name}")
                await asyncio.sleep(duration_secs)
                self.set_switch_sync(switch_name, int(not state))
            else:
                # Remove any existing reversion, add a new one if necessary
                self.delay.add(name=switch_name, ms=duration_secs * 1000,
                               callback=self.set_switch_sync,
                               switch_name=switch_name, state=int(not state))

        if wait_after:
            await asyncio.sleep(wait_after)

    async def start_game(self, num_players=1):
        """Start a game with the requested number of players."""
        self.info_log("Starting game.")
        await asyncio.sleep(1)
        start_button = self.machine.switches.items_tagged('start')[0]
        for _ in range(0, num_players):
            await self.set_switch(start_button.name, 1, 0.2)
            await asyncio.sleep(0.5)
        assert self.machine.game, "Game failed to start"

    async def eject_and_plunge_ball(self, plunger_switch_name, plunger_lane_settle_time=2, **kwargs):
        """Shuffle the trough switches and plunger to simulate an eject."""
        del kwargs
        self.info_log("Ejecting and plunging ball...")
        self.set_switch_sync(self.trough_switches[0], 0)
        await asyncio.sleep(0.03)
        self.set_switch_sync(self.trough_switches[-1], 0)
        await asyncio.sleep(0.1)
        self.set_switch_sync(self.trough_switches[0], 1)
        await asyncio.sleep(0.25)
        await self.set_switch(plunger_switch_name, 1, duration_secs=plunger_lane_settle_time)
        await asyncio.sleep(1)

    async def move_ball_from_drain_to_trough(self, **kwargs):
        """Move a ball from the drain device to the trough device."""
        del kwargs
        drain_switches = self.machine.ball_devices.items_tagged('drain')[0].config.get('ball_switches')
        self.set_switch_sync(drain_switches[-1], 0)
        await asyncio.sleep(0.25)
        self.set_switch_sync(self.trough_switches[-1], 1)
        await asyncio.sleep(0.25)
