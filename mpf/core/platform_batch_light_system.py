"""A light system for platforms which batches all updates."""
import abc
import asyncio

from typing import Tuple, Set, List
from sortedcontainers import SortedSet, SortedList
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.core.utility_functions import Util


class PlatformBatchLight(LightPlatformInterface, abc.ABC):

    """Light which can be batched."""

    __slots__ = ["light_system", "_current_fade", "_last_brightness"]

    def __init__(self, number, light_system: "PlatformBatchLightSystem"):
        """initialize light."""
        super().__init__(number)
        self.light_system = light_system
        self._current_fade = (0, -1, 0, -1)
        self._last_brightness = None

    @abc.abstractmethod
    def get_max_fade_ms(self):
        """Return max fade ms."""

    def set_fade(self, start_brightness, start_time, target_brightness, target_time):
        """Mark dirty and remember fade."""
        self.light_system.mark_dirty(self)
        self._current_fade = (start_brightness, start_time, target_brightness, target_time)
        self._last_brightness = None

    def get_fade_and_brightness(self, current_time):
        """Return fade + brightness and mark as clean if this is it."""
        if self._last_brightness:
            return self._last_brightness, 0, True
        max_fade_ms = self.get_max_fade_ms()
        start_brightness, start_time, target_brightness, target_time = self._current_fade
        fade_ms = int(round((target_time - current_time) * 1000.0))
        if fade_ms > max_fade_ms >= 0:
            fade_ms = max_fade_ms
            ratio = ((current_time + (fade_ms / 1000.0) - start_time) /
                     (target_time - start_time))
            brightness = start_brightness + (target_brightness - start_brightness) * ratio
            done = False
        else:
            if fade_ms < 0:
                fade_ms = 0
            brightness = target_brightness
            self._last_brightness = brightness
            done = True

        return brightness, fade_ms, done


class PlatformBatchLightSystem:

    """Batch light system for platforms."""

    __slots__ = ["dirty_lights", "dirty_schedule", "clock", "update_task", "update_callback",
                 "update_hz", "max_batch_size", "scheduler_task", "schedule_changed", "dirty_lights_changed",
                 "last_state"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, clock, update_callback, update_hz, max_batch_size):
        """initialize light system."""
        self.dirty_lights = SortedSet()    # type: Set[PlatformBatchLight]
        self.dirty_lights_changed = asyncio.Event()
        self.dirty_schedule = SortedList()
        self.schedule_changed = asyncio.Event()
        self.update_task = None
        self.scheduler_task = None
        self.clock = clock
        self.update_callback = update_callback
        self.update_hz = update_hz
        self.max_batch_size = max_batch_size
        self.last_state = {}

    def start(self):
        """Start light system."""
        self.update_task = self.clock.loop.create_task(self._send_updates())
        self.update_task.add_done_callback(Util.raise_exceptions)
        self.scheduler_task = self.clock.loop.create_task(self._schedule_updates())
        self.scheduler_task.add_done_callback(Util.raise_exceptions)

    def stop(self):
        """Stop light system."""
        if self.scheduler_task:
            self.scheduler_task.cancel()
            self.scheduler_task = None
        if self.update_task:
            self.update_task.cancel()
            self.update_task = None

    async def _schedule_updates(self):
        while True:
            run_time = self.clock.get_time()
            self.schedule_changed.clear()
            while self.dirty_schedule and self.dirty_schedule[0][0] <= run_time:
                self.dirty_lights.add(self.dirty_schedule[0][1])
                del self.dirty_schedule[0]
            self.dirty_lights_changed.set()

            if self.dirty_schedule:
                try:
                    await asyncio.wait_for(self.schedule_changed.wait(), self.dirty_schedule[0][0] - run_time)
                except asyncio.TimeoutError:
                    pass
            else:
                await self.schedule_changed.wait()

    async def _send_updates(self):
        poll_sleep_time = 1 / self.update_hz
        max_fade_tolerance = int(poll_sleep_time * 1000)
        while True:
            await self.dirty_lights_changed.wait()
            self.dirty_lights_changed.clear()
            sequential_lights = []
            for light in list(self.dirty_lights):
                if not sequential_lights:
                    # first light
                    sequential_lights = [light]
                elif light.is_successor_of(sequential_lights[-1]):
                    # lights are sequential
                    sequential_lights.append(light)
                else:
                    # sequence ended
                    await self._send_update_batch(sequential_lights, max_fade_tolerance)
                    # this light is a new sequence
                    sequential_lights = [light]

            if sequential_lights:
                await self._send_update_batch(sequential_lights, max_fade_tolerance)

            self.dirty_lights.clear()

            await asyncio.sleep(poll_sleep_time)

    async def _send_update_batch(self, sequential_lights: List[PlatformBatchLight], max_fade_tolerance):
        sequential_brightness_list = []     # type: List[Tuple[LightPlatformInterface, float, int]]
        common_fade_ms = None
        current_time = self.clock.get_time()
        for light in sequential_lights:
            brightness, fade_ms, done = light.get_fade_and_brightness(current_time)
            schedule_time = current_time + (fade_ms / 1000)
            if not done:
                if not self.dirty_schedule or self.dirty_schedule[0][0] > schedule_time:
                    self.schedule_changed.set()
                self.dirty_schedule.add((schedule_time, light))
            else:
                # check if we realized this brightness earlier
                last_state = self.last_state.get(light, None)
                if last_state and last_state[0] == brightness and last_state[1] < schedule_time and \
                        not sequential_brightness_list:
                    # we already set the light to that color earlier. skip it
                    # we only skip this light if we are in the beginning of the list for now
                    # the reason for that is that we do not want to break fade chains when one color channel
                    # of an RGB light did not change
                    # this could become an option in the future
                    continue

            self.last_state[light] = (brightness, schedule_time)

            if common_fade_ms is None:
                common_fade_ms = fade_ms

            if -max_fade_tolerance < common_fade_ms - fade_ms < max_fade_tolerance and \
                    len(sequential_brightness_list) < self.max_batch_size:
                sequential_brightness_list.append((light, brightness, common_fade_ms))
            else:
                await self.update_callback(sequential_brightness_list)
                # start new list
                current_time = self.clock.get_time()
                common_fade_ms = fade_ms
                sequential_brightness_list = [(light, brightness, common_fade_ms)]

        if sequential_brightness_list:
            await self.update_callback(sequential_brightness_list)

    def mark_dirty(self, light: "PlatformBatchLight"):
        """Mark as dirty."""
        self.dirty_lights.add(light)
        self.dirty_lights_changed.set()
        self.dirty_schedule = SortedList([x for x in self.dirty_schedule if x[1] != light])
