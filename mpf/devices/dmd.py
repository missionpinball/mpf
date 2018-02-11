"""Support for physical DMDs."""
import asyncio

from mpf.core.machine import MachineController
from mpf.core.platform import DmdPlatform

from mpf.core.system_wide_device import SystemWideDevice


class Dmd(SystemWideDevice):

    """A physical DMD."""

    config_section = 'dmds'
    collection = 'dmds'
    class_label = 'dmd'
    machine = None

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Create BCP methods.

        Args:
            machine: MachineController which is used
        """
        cls.machine = machine
        cls.machine.bcp.interface.register_command_callback("dmd_frame", cls._bcp_receive_dmd_frame)

    def __init__(self, machine, name):
        """Initialise DMD."""
        self.hw_device = None
        self.platform = None        # type: DmdPlatform
        super().__init__(machine, name)

    def _initialize(self):
        self.platform = self.machine.get_platform_sections("dmd", self.config['platform'])
        self.hw_device = self.platform.configure_dmd()

    @classmethod
    @asyncio.coroutine
    def _bcp_receive_dmd_frame(cls, client, name, rawbytes, **kwargs):
        """Update dmd from BCP."""
        del client
        del kwargs

        if name not in cls.machine.dmds:
            raise TypeError("dmd {} not known".format(name))

        cls.machine.dmds[name].update(rawbytes)

    def update(self, data: bytes):
        """Update data on the dmd.

        Args:
            data: bytes to send
        """
        self.hw_device.update(data)
