"""A light system for platforms which batches all updates."""
import abc
import asyncio
from typing import Callable, Tuple, Set
from sortedcontainers import SortedSet
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class PlatformBatchLight(LightPlatformInterface, abc.ABC):

    """Light which can be batched."""

    __slots__ = ["light_system", "_callback"]

    def __init__(self, number, light_system: "PlatformBatchLightSystem"):
        """Initialise light."""
        super().__init__(number)
        self.light_system = light_system
        self._callback = None

    @abc.abstractmethod
    def get_max_fade_ms(self):
        """Return max fade ms."""
        pass

    def set_fade(self, color_and_fade_callback: Callable[[int], Tuple[float, int]]):
        """Mark dirty and remember callback."""
        self.light_system.mark_dirty(self)
        self._callback = color_and_fade_callback

    def get_fade_and_brightness(self):
        """Return fade + brightness and mark as clean if this is it."""
        max_fade_ms = self.get_max_fade_ms()
        brightness, fade_ms = self._callback(max_fade_ms)
        if fade_ms < max_fade_ms:
            self.light_system.mark_clean(self)

        return brightness, fade_ms


class PlatformBatchLightSystem:

    """Batch light system for platforms."""

    __slots__ = ["dirty_lights", "loop", "is_sequential_function", "update_task", "update_callback"]

    def __init__(self, loop, sort_function, is_sequential_function, update_callback):
        """Initialise light system."""
        self.dirty_lights = SortedSet(key=sort_function)    # type: Set[PlatformBatchLight]
        self.is_sequential_function = is_sequential_function
        self.update_task = None
        self.loop = loop
        self.update_callback = update_callback

    def start(self):
        """Start light system."""
        self.update_task = self.loop.create_task(self._send_updates())
        self.update_task.add_done_callback(self._done)

    def stop(self):
        """Stop light system."""
        if self.update_task:
            self.update_task.cancel()
            self.update_task = None

    @staticmethod
    def _done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    @asyncio.coroutine
    def _send_updates(self):
        while True:
            sequential_lights = []
            for light in self.dirty_lights:
                if not sequential_lights:
                    # first light
                    sequential_lights = [light]
                elif self.is_sequential_function(sequential_lights[-1], light):
                    # lights are sequential
                    sequential_lights.append(light)
                else:
                    # sequence ended
                    yield from self.update_callback(sequential_lights)
                    # this light is a new sequence
                    sequential_lights = [light]

            if sequential_lights:
                yield from self.update_callback(sequential_lights)

            yield from asyncio.sleep(.001, loop=self.loop)

    def mark_dirty(self, light: "PlatformBatchLight"):
        """Mark as dirty."""
        self.dirty_lights.add(light)

    def mark_clean(self, light: "PlatformBatchLight"):
        """Mark as clean."""
        self.dirty_lights.remove(light)
