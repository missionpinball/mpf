"""Support for physical DMDs."""
from mpf.core.machine import MachineController

from mpf.core.system_wide_device import SystemWideDevice


class PhysicalDmd(SystemWideDevice):

    """A physical DMD."""

    config_section = 'physical_dmds'
    collection = 'physical_dmds'
    class_label = 'physical_dmd'
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
        super().__init__(machine, name)

    def _initialize(self):
        self.load_platform_section("dmd")
        self.hw_device = self.platform.configure_dmd()

    @classmethod
    def _bcp_receive_dmd_frame(cls, client, name, rawbytes, **kwargs):
        """Update dmd from BCP."""
        del client
        del kwargs

        if name not in cls.machine.physical_dmds:
            raise TypeError("dmd {} not known".format(name))

        cls.machine.physical_dmds[name].update(rawbytes)

    def update(self, data: bytes):
        """Update data on the dmd.

        Args:
            data: bytes to send
        """
        self.hw_device.update(data)
