"""Support for physical RGB DMDs."""
import asyncio
from functools import partial

from mpf.core.machine import MachineController
from mpf.core.platform import RgbDmdPlatform

from mpf.core.system_wide_device import SystemWideDevice


class RgbDmd(SystemWideDevice):

    """A physical DMD."""

    config_section = 'rgb_dmds'
    collection = 'rgb_dmds'
    class_label = 'rgb_dmd'

    __slots__ = ["hw_device", "platform"]

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Create BCP methods.

        Args:
            machine: MachineController which is used
        """
        machine.bcp.interface.register_command_callback("rgb_dmd_frame", partial(cls._bcp_receive_dmd_frame, machine))

    def __init__(self, machine, name):
        """Initialise DMD."""
        self.hw_device = None
        self.platform = None        # type: RgbDmdPlatform
        super().__init__(machine, name)

    @asyncio.coroutine
    def _initialize(self):
        yield from super()._initialize()
        self.platform = self.machine.get_platform_sections("rgb_dmd", self.config['platform'])
        self.hw_device = self.platform.configure_rgb_dmd(self.name)
        self._update_brightness(None)

    def _update_brightness(self, future):
        del future
        brightness, brightness_changed_future = self.config['hardware_brightness'].evaluate_and_subscribe([])
        self.hw_device.set_brightness(brightness)
        brightness_changed_future.add_done_callback(self._update_brightness)

    @classmethod
    @asyncio.coroutine
    def _bcp_receive_dmd_frame(cls, machine, client, name, rawbytes, **kwargs):
        """Update dmd from BCP."""
        del client
        del kwargs

        if name not in machine.rgb_dmds:
            raise TypeError("rgb dmd {} not known".format(name))

        machine.rgb_dmds[name].update(rawbytes)

    def update(self, data: bytes):
        """Update data on the dmd.

        Args:
            data: bytes to send
        """
        self.hw_device.update(data)
