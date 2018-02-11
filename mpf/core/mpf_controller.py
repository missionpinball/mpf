"""Base class for MPF controllers."""
import abc

from mpf.core.logging import LogMixin
MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController


class MpfController(LogMixin, metaclass=abc.ABCMeta):

    """Base class for MPF controllers."""

    module_name = None  # type: str
    config_name = None  # type: str

    def __init__(self, machine: "MachineController") -> None:
        """Initialise controller.

        Args:
            machine(mpf.core.machine.MachineController): the machine controller

        Returns:

        """
        super().__init__()
        self.machine = machine

        if not self.module_name:
            self.module_name = self.__class__.__name__

        if not self.config_name:
            raise AssertionError("Please specify a config name for {}".format(self))

        self.configure_logging(
            self.module_name,
            self.machine.machine_config['logging']['console'][self.config_name],
            self.machine.machine_config['logging']['file'][self.config_name])

        self.debug_log("Loading the {}".format(self.module_name))
