"""Fast Io board."""


class FastIoBoard:

    """A fast IO board on the NET processor."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, node_id, model_string, firmware_version, switch_count, driver_count):
        """Initialise FastIoBoard."""
        self.node_id = node_id
        self.model_string = model_string
        self.firmware_version = firmware_version
        self.switch_count = switch_count
        self.driver_count = driver_count

    def get_description_string(self) -> str:
        """Return description string."""
        return "Board {} - Model: {} Firmware: {} Switches: {} Drivers: {}".format(
            self.node_id,
            self.model_string,
            self.firmware_version,
            self.switch_count,
            self.driver_count
        )
