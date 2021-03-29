"""Interface for a light hardware devices."""
import abc
import asyncio
from asyncio import AbstractEventLoop
from functools import total_ordering

from typing import Any, Optional

from mpf.core.utility_functions import Util


@total_ordering     # type: ignore
class LightPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for a light in hardware platforms."""

    __slots__ = ["number"]

    def __init__(self, number: Any) -> None:
        """Initialise light."""
        self.number = number

    @abc.abstractmethod
    def set_fade(self, start_brightness, start_time, target_brightness, target_time):
        """Perform a fade to a brightness.

        Args:
        ----
            start_brightness: Brightness at start of fade.
            start_time: Timestamp when the fade started.
            target_brightness: Brightness at end of fade.
            target_time: Timestamp when the fade should finish.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_board_name(self):
        """Return the name of the board of this light."""
        raise NotImplementedError

    def is_successor_of(self, other):
        """Return true if this light is the direct successor of the other light passed as parameter."""
        raise NotImplementedError

    def get_successor_number(self):
        """Return the next light number after this light if possible.

        This is used for serial LED chains. Raise an error if this is not possible.
        """
        raise NotImplementedError

    def __lt__(self, other):
        """Order lights by their position on the hardware."""
        raise NotImplementedError

    def __repr__(self):
        """Return string representation."""
        return "<{} number={}>".format(self.__class__, self.number)


class LightPlatformDirectFade(LightPlatformInterface, metaclass=abc.ABCMeta):

    """Implement a light which can set fade and brightness directly."""

    __slots__ = ["loop", "task"]

    def __init__(self, number, loop: AbstractEventLoop) -> None:
        """Initialise light."""
        super().__init__(number)
        self.loop = loop
        self.task = None    # type: Optional[asyncio.Task]

    @abc.abstractmethod
    def get_max_fade_ms(self) -> int:
        """Return max fade time."""
        raise NotImplementedError()

    def get_fade_interval_ms(self) -> int:
        """Return max fade time."""
        return self.get_max_fade_ms()

    def set_fade(self, start_brightness, start_time, target_brightness, target_time):
        """Perform a fade with either a asyncio task or with a single command."""
        max_fade_ms = self.get_max_fade_ms()
        current_time = self.loop.time()
        if target_time > 0:
            fade_ms = (target_time - current_time) / 1000.0
        else:
            fade_ms = -1

        if fade_ms > max_fade_ms:
            # we have to continue the fade later
            if self.task:
                self.task.cancel()
            self.task = self.loop.create_task(self._fade(start_brightness, start_time, target_brightness, target_time))
            self.task.add_done_callback(Util.raise_exceptions)
        else:
            self.set_brightness_and_fade(target_brightness, max(fade_ms, 0))

    async def _fade(self, start_brightness, start_time, target_brightness, target_time):
        max_fade_ms = self.get_max_fade_ms()
        interval = self.get_fade_interval_ms() / 1000
        while True:
            current_time = self.loop.time()
            target_fade_ms = int((target_time - current_time) * 1000.0)
            if target_fade_ms > max_fade_ms >= 0:
                fade_ms = max_fade_ms
                ratio = ((current_time + (max_fade_ms / 1000.0) - start_time) /
                         (target_time - start_time))
                brightness = start_brightness + (target_brightness - start_brightness) * ratio
            else:
                fade_ms = target_fade_ms
                brightness = target_brightness
            self.set_brightness_and_fade(brightness, max(fade_ms, 0))
            if target_fade_ms <= max_fade_ms:
                return
            await asyncio.sleep(interval)

    @abc.abstractmethod
    def set_brightness_and_fade(self, brightness: float, fade_ms: int) -> None:
        """Set the light to the specified brightness.

        Args:
        ----
            brightness: float of the brightness
            fade_ms: ms to fade the light

        Does not return anything.
        """
        raise NotImplementedError

    def stop(self):
        """Stop light."""
        if self.task:
            self.task.cancel()


class LightPlatformSoftwareFade(LightPlatformDirectFade, metaclass=abc.ABCMeta):

    """Implement a light which cannot fade on its own."""

    __slots__ = ["software_fade_ms"]

    def __init__(self, number, loop: AbstractEventLoop, software_fade_ms: int) -> None:
        """Initialise light with software fade."""
        super().__init__(number, loop)
        self.software_fade_ms = software_fade_ms

    def get_max_fade_ms(self) -> int:
        """Return max fade time."""
        return 0

    def get_fade_interval_ms(self) -> int:
        """Return software fade interval."""
        return self.software_fade_ms

    def set_brightness_and_fade(self, brightness: float, fade_ms: int):
        """Set brightness and ensure that fade is 0."""
        assert fade_ms == 0
        self.set_brightness(brightness)

    @abc.abstractmethod
    def set_brightness(self, brightness: float) -> None:
        """Set the light to the specified brightness.

        Args:
        ----
            brightness: float of the brightness

        Does not return anything.
        """
        raise NotImplementedError
