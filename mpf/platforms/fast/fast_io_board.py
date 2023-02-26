"""FAST I/O Board."""


class FastIoBoard:

    """A FAST I/O board on the NET processor."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, name, node_id, model_string, firmware_version, switch_count, driver_count, prior_switches, prior_drivers):
        """Initialise FastIoBoard."""
        self.name = name
        self.node_id = node_id  # position in the I/O loop, 0-indexed
        self.model = model_string  # TODO clean this up
        self.firmware_version = firmware_version




        self.start_switch = prior_switches
        self.start_driver = prior_drivers
        self.switch_count = switch_count
        self.driver_count = driver_count

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
