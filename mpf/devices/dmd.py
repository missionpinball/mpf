"""Support for physical DMDs."""
import asyncio
from functools import partial

from mpf.core.machine import MachineController
from mpf.core.platform import DmdPlatform

from mpf.core.system_wide_device import SystemWideDevice


class Dmd(SystemWideDevice):

    """A physical DMD."""

    config_section = 'dmds'
    collection = 'dmds'
    class_label = 'dmd'

    __slots__ = ["hw_device", "platform"]

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Create BCP methods.

        Args:
            machine: MachineController which is used
        """
        machine.bcp.interface.register_command_callback("dmd_frame", partial(cls._bcp_receive_dmd_frame, machine))

    def __init__(self, machine, name):
        """Initialise DMD."""
        self.hw_device = None
        self.platform = None        # type: DmdPlatform
        super().__init__(machine, name)

    @asyncio.coroutine
    def _initialize(self):
        yield from super()._initialize()
        self.platform = self.machine.get_platform_sections("dmd", self.config['platform'])
        self.hw_device = self.platform.configure_dmd()

    @classmethod
    @asyncio.coroutine
    def _bcp_receive_dmd_frame(cls, machine, client, name, rawbytes, **kwargs):
        """Update dmd from BCP."""
        del client
        del kwargs

        if name not in machine.dmds:
            raise TypeError("dmd {} not known".format(name))

        machine.dmds[name].update(rawbytes)

    def update(self, data: bytes):
        """Update data on the dmd.

        Args:
            data: bytes to send
        """
        self.hw_device.update(data)
