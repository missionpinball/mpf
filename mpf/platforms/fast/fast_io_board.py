from mpf.platforms.fast.fast_defines import VALID_IO_BOARDS
from mpf.platforms.fast.fast_switch import FASTSwitch
from mpf.core.platform import SwitchConfig

"""FAST I/O Board."""


class FastIoBoard:

    """A FAST I/O board on the NET processor."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, communicator, name, node_id, model_string, firmware_version, switch_count, driver_count, prior_switches, prior_drivers):
        """Initialise FastIoBoard."""
        self.communicator = communicator
        self.name = str(name)
        self.node_id = node_id  # position in the I/O loop, 0-indexed
        self.model = model_string
        self.firmware_version = firmware_version
        self.net_version = int(firmware_version.split('.')[0])
        self.start_switch = prior_switches
        self.start_driver = prior_drivers
        self.switch_count = switch_count
        self.driver_count = driver_count

        assert self.model in VALID_IO_BOARDS, "Invalid I/O board model: {}".format(self.model)

        self.create_switches()
        self.create_drivers()

    def __repr__(self):
        return f'{self.model} "{self.name}"'

    def get_description_string(self) -> str:
        """Return description string."""
        return "Board {} - Model: {} Firmware: {} Switches: {} Drivers: {}".format(
            self.node_id,
            self.model,
            self.firmware_version,
            self.switch_count,
            self.driver_count
        )

    def create_switches(self):
        for i in range(self.switch_count):
            hw_number = self.start_switch + i
            self.communicator.switches.append(FASTSwitch(self.communicator, self.net_version, hw_number))

    def create_drivers(self):
        pass