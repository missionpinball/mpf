"""Base class for MPF controllers."""
import abc


class MpfController(metaclass=abc.ABCMeta):

    """Base class for MPF controllers."""

    def __init__(self, machine):
        """Initialise controller.

        Args:
            machine(mpf.core.machine.MachineController): the machine controller

        Returns:

        """
        self.machine = machine
