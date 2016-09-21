"""Support for physical RGB DMDs."""
from mpf.core.machine import MachineController

from mpf.core.system_wide_device import SystemWideDevice


class PhysicalRgbDmd(SystemWideDevice):

    """A physical DMD."""

    config_section = 'physical_rgb_dmds'
    collection = 'physical_rgb_dmds'
    class_label = 'physical_rgb_dmd'
    machine = None

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Create BCP methods.

        Args:
            machine: MachineController which is used
        """
        cls.machine = machine
        cls.machine.bcp.interface.register_command_callback("rgb_dmd_frame", cls._bcp_receive_dmd_frame)

    def __init__(self, machine, name):
        """Initialise DMD."""
        self.hw_device = None
        super().__init__(machine, name)

    def _initialize(self):
        self.load_platform_section("rgb_dmd")
        self.hw_device = self.platform.configure_rgb_dmd()

    @classmethod
    def _bcp_receive_dmd_frame(cls, client, name, rawbytes, **kwargs):
        """Update dmd from BCP."""
        del client
        del kwargs

        if name not in cls.machine.physical_rgb_dmds:
            raise TypeError("rgb dmd {} not known".format(name))

        cls.machine.physical_rgb_dmds[name].update(rawbytes)

    def update(self, data: bytes):
        """Update data on the dmd.

        Args:
            data: bytes to send
        """
        self.hw_device.update(data)
