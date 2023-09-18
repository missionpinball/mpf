from mpf.platforms.fast.fast_defines import VALID_IO_BOARDS

"""FAST I/O Board."""


class FastIoBoard:

    """A FAST I/O board on the NET processor."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, communicator, name, node_id, model_string, firmware_version, switch_count, driver_count, prior_switches, prior_drivers):
        """initialize FastIoBoard."""
        self.communicator = communicator
        self.name = str(name)
        self.node_id = node_id  # position in the I/O loop, 0-indexed
        self.model = model_string
        self.firmware_version = firmware_version
        self.start_switch = prior_switches
        self.start_driver = prior_drivers
        self.switch_count = switch_count
        self.driver_count = driver_count

        assert self.model in VALID_IO_BOARDS, "Invalid I/O board model: {}".format(self.model)

    def __repr__(self):
        return f'{self.model} "{self.name}"'

    def get_description_string(self) -> str:
        """Return description string."""
        return f"Board {self.node_id} - Model: {self.model}, Firmware: {self.firmware_version}, Switches: {self.switch_count}, Drivers: {self.driver_count}"
