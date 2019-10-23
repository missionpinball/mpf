"""A system wide device which can be defined in the main config."""
import abc

from mpf.core.device import Device


class SystemWideDevice(Device, metaclass=abc.ABCMeta):

    """A system wide device which can be defined in the main config."""

    __slots__ = []

    async def device_added_system_wide(self):
        """Add the device system wide."""
        await self._initialize()
