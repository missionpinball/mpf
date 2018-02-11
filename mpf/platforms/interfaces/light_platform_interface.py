"""Interface for a light hardware devices."""
import abc
import asyncio
from asyncio import AbstractEventLoop

from typing import Callable, Tuple, Any


class LightPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for a light in hardware platforms."""

    def __init__(self, number: Any) -> None:
        """Initialise light."""
        self.number = number

    @abc.abstractmethod
    def set_fade(self, color_and_fade_callback: Callable[[int], Tuple[float, int]]):
        """Perform a fade to a brightness.

        Pass a callback which has the max_fade_time as parameter and returns the desired fade time and the brightness.
        This is a callback because the platform may send the brightness later on and we do not want to introduce latency
        between setting and sending the color.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_board_name(self):
        """Return the name of the board of this light."""
        raise NotImplementedError


class LightPlatformDirectFade(LightPlatformInterface, metaclass=abc.ABCMeta):

    """Implement a light which can set fade and brightness directly."""

    def __init__(self, number, loop: AbstractEventLoop) -> None:
        """Initialise light."""
        super().__init__(number)
        self.loop = loop
        self.task = None    # type: asyncio.Task

    @abc.abstractmethod
    def get_max_fade_ms(self) -> int:
        """Return max fade time."""
        raise NotImplementedError()

    def get_fade_interval_ms(self) -> int:
        """Return max fade time."""
        return self.get_max_fade_ms()

    def set_fade(self, color_and_fade_callback: Callable[[int], Tuple[float, int]]):
        """Perform a fade with either a asyncio task or with a single command."""
        max_fade_ms = self.get_max_fade_ms()

        brightness, fade_ms = color_and_fade_callback(max_fade_ms)
        self.set_brightness_and_fade(brightness, max(fade_ms, 0))
        if fade_ms >= max_fade_ms:
            # we have to continue the fade later
            if self.task:
                self.task.cancel()
            self.task = self.loop.create_task(self._fade(color_and_fade_callback))

    @asyncio.coroutine
    def _fade(self, color_and_fade_callback):
        while True:
            yield from asyncio.sleep(self.get_fade_interval_ms() / 1000, loop=self.loop)
            max_fade_ms = self.get_max_fade_ms()
            brightness, fade_ms = color_and_fade_callback(max_fade_ms)
            self.set_brightness_and_fade(brightness, max(fade_ms, 0))
            if fade_ms < max_fade_ms:
                return

    @abc.abstractmethod
    def set_brightness_and_fade(self, brightness: float, fade_ms: int):
        """Set the light to the specified brightness.

        Args:
            brightness: float of the brightness
            fade_ms: ms to fade the light

        Returns:
            None
        """
        raise NotImplementedError


class LightPlatformSoftwareFade(LightPlatformDirectFade, metaclass=abc.ABCMeta):

    """Implement a light which cannot fade on its own."""

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
    def set_brightness(self, brightness: float):
        """Set the light to the specified brightness.

        Args:
            brightness: float of the brightness

        Returns:
            None
        """
        raise NotImplementedError
