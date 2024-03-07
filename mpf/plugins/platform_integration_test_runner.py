"""Test framework for testing physical platform integration"""

import asyncio

from mpf.core.delays import DelayManager
from mpf.core.plugin import MpfPlugin
from mpf.core.utility_functions import Util


class MpfPlatformIntegrationTestRunner(MpfPlugin):

    __slots__ = ("machine", "name", "delay", "_task", "_test_obj")

    @property
    def is_plugin_enabled(self):
        """This plugin is controlled by the '-pit' command line arg."""
        return self.machine.options["platform_integration_test"]


    def initialize(self):
        """initialize custom code but with custom logging formatter"""
        self.configure_logging('MpfPlatformIntegration', 'basic', 'full')
        self.info_log("Platform Integration Test is here! Arg value is %s", self.machine.options["platform_integration_test"])
        self.delay = DelayManager(self.machine)

        # Find the file with the test
        test_file = self.machine.options["platform_integration_test"]
        if test_file.endswith(".py"):
            self.info_log("Trying to make a test from python file %s", test_file)
            parts = test_file.split("/")
            parts[-1] = parts[-1][:-3]
            # Assume the class name is the same as the filename
            parts.append(Util.snake_to_pascal(parts[-1]))
            test_file = ".".join(parts)


        self.info_log("Trying to import from module '%s'", test_file)
        # Look for a file path
        test_target = Util.string_to_class(test_file)(self)

        self.machine.events.add_handler("mode_attract_started", self._run_tests)
        for s in range(1,4):
            self.machine.switch_controller.process_switch(f"s_trough_{s}", 1)
        self.info_log("Re-initializing trough ball count")
        asyncio.create_task(self.machine.ball_devices['bd_trough']._initialize_async())

    def _run_tests(self, **kwargs):
        del kwargs
        self.log.info("Running tests!")
        for playfield in self.machine.playfields.values():
            playfield.ball_search.disable()
        self._task = asyncio.create_task(self.test_skillshot())
        self._task.add_done_callback(self._stop_callback)

    def _stop_callback(self, future):
        Util.raise_exceptions(future)

        if self._task:
            self._task.cancel()
            self._task = None
        self.machine.stop("All tests completed successfully.")

    def set_switch_sync(self, switch_name, state):
        if state is None:
            state = int(not self.machine.switches[switch_name].state)
        self.delay.remove(switch_name)
        self.info_log("Setting switch %s to state %s", switch_name, state)
        self.machine.switch_controller.process_switch(switch_name, state)

    async def wait_for_event(self, event, timeout=None):
        """Wait for an event to be posted within a given timeout (secs)."""
        try:
            await asyncio.wait_for(self.machine.events.wait_for_event(event), timeout)
            self.info_log(f"Successfully caught event '{event}'")
        except asyncio.TimeoutError:
            self.machine.stop_with_exception({ "exception": AssertionError(f"Awaited event '{event}' failed to trigger within {timeout}s.")})

    async def set_switch(self, switch_name, state=None, duration_secs=None, blocking=True):
        self.set_switch_sync(switch_name, state)
        if not duration_secs:
            return

        # Blocking mode: await the duration before returning
        if blocking:
            self.info_log(f" - waiting {duration_secs}s to toggle back switch {switch_name}")
            await asyncio.sleep(duration_secs)
            self.set_switch_sync(switch_name, int(not state))
        else:
            # Remove any existing reversion, add a new one if necessary
            self.delay.add(name=switch_name, ms=duration_secs*1000, callback=self.set_switch_sync,
                          switch_name=switch_name, state=int(not state))

    async def start_game(self, force_character=None, force_quest=None):
        self.info_log("Starting game.")
        # self.machine.events.add_handler("balldevice_bd_trough_ejecting_ball", self.eject_and_plunge_ball)
        # self.machine.events.add_handler("balldevice_bd_drain_ejecting_ball", self.move_ball_from_drain_to_trough)
        await asyncio.sleep(1)
        for _ in range(0, NUM_PLAYERS):
            await self.set_switch("s_credit", 1, 0.2)
            await asyncio.sleep(1)
        assert self.machine.modes.missionselect.active, "Mission select mode not active"
        if force_character or force_quest:
            self.machine.modes.missionselect.force_selection(force_character, force_quest)

    async def eject_and_plunge_ball(self, **kwargs):
        del kwargs
        self.info_log("Ejecting and plunging ball...")
        self.set_switch_sync("s_trough_1", 0)
        await asyncio.sleep(0.03)
        self.set_switch_sync("s_trough_3", 0)
        await asyncio.sleep(0.1)
        self.set_switch_sync("s_trough_1", 1)
        await asyncio.sleep(0.25)
        await self.set_switch("s_plunger_lane", 1, 2)
        await asyncio.sleep(1)

    async def move_ball_from_drain_to_trough(self, **kwargs):
        del kwargs
        self.set_switch_sync("s_drain", 0)
        await asyncio.sleep(0.25)
        self.set_switch_sync("s_trough_3", 1)
        await asyncio.sleep(0.25)

    async def test_skillshot(self):
        p = 1
        await self.start_game("asrak", "swamp")
        for p in range(1, NUM_PLAYERS + 2):
            for ball in range(1,4):
                await self.eject_and_plunge_ball()
                for ball_save in self.machine.ball_saves.values():
                    ball_save.disable()
                # self.info_log("Testing skillshot!")
                # await self.set_switch("s_center_ramp_exit", 1, 0.1, blocking=False)
                # await self.wait_for_event("skillshot_asrak_lit_hit", 1)
                self.info_log("Beginning spinner test")
                for _ in range(0, 100):
                    await self.set_switch("s_titan_spinner", 1, 0.005)
                self.info_log("Spinner test complete.")
                self.machine.events.post("debug_dump_stats")
                await asyncio.sleep(0.5)
                self.info_log(f"Draining ball {ball} for player {p}")
                await self.set_switch("s_drain", 1)
                self.info_log(f"End of ball {ball} for player {p}")
                await self.move_ball_from_drain_to_trough()

                if ball == 3 and p == NUM_PLAYERS:
                    await self.wait_for_event("game_will_end")
                    # self.machine.events.post("debug_dump_stats")
                else:
                    self.info_log("Waiting for player turn to start")
                    await self.wait_for_event("player_turn_started")
        await self.wait_for_event("mode_game_stopped")
