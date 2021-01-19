# pylint: disable-msg=too-many-lines
"""PKONE Hardware interface.

Contains the hardware interface and drivers for the Penny K Pinball PKONE
platform hardware.
"""
import serial.tools.list_ports

from mpf.platforms.pkone.pkone_serial_communicator import PKONESerialCommunicator
from mpf.platforms.pkone.pkone_extension import PKONEExtensionBoard

from mpf.core.platform import SwitchPlatform, DriverPlatform, LightsPlatform, SwitchSettings, DriverSettings, \
    DriverConfig, SwitchConfig


# pylint: disable-msg=too-many-instance-attributes
class PKONEHardwarePlatform(SwitchPlatform, DriverPlatform):

    """Platform class for the PKONE Nano hardware controller.

    Args:
        machine: The MachineController instance.
    """

    __slots__ = ["config", "serial_connections", "pkone_extensions"]

    def __init__(self, machine) -> None:
        """Initialize PKONE platform."""
        super().__init__(machine)
        self.serial_connections = set()     # type: Set[PKONESerialCommunicator]
        self.pkone_extensions = []          # type: List[PKONEExtensionBoard]

        self.config = self.machine.config_validator.validate_config("pkone", self.machine.config['pkone'])
        self._configure_device_logging_and_debug("PKONE", self.config)
        self.debug_log("Configuring PKONE hardware.")

    async def initialize(self):
        """Initialize connection to PKONE Nano hardware."""
        await self._connect_to_hardware()

    def get_info_string(self):
        """Dump infos about boards."""
        if not self.serial_connections:
            return "No connection to any controller board."

        infos = "Connected Nano Controllers:\n"
        for connection in sorted(self.serial_connections, key=lambda x: x.chain_serial):
            infos += " - Port: {} at {} baud.\n".format(connection.port, connection.baud)

        infos += "\nExtension boards:\n"
        for extension in self.pkone_extensions:
            infos += " - Address ID: {}\n".format(extension.addr)

        return infos

    async def _connect_to_hardware(self):
        """Connect to each port from the config.

        This process will cause the connection threads to figure out which processor they've connected to
        and to register themselves.
        """
        for port in self.config['ports']:
            comm = PKONESerialCommunicator(platform=self, port=port, baud=self.config['baud'])
            await comm.connect()
            self.serial_connections.add(comm)

