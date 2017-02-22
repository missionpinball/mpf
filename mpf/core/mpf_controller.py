"""Base class for MPF controllers."""
import abc
import re

from mpf.core.logging import LogMixin


class MpfController(LogMixin, metaclass=abc.ABCMeta):

    """Base class for MPF controllers."""

    module_name = None
    config_name = None

    def __init__(self, machine):
        """Initialise controller.

        Args:
            machine(mpf.core.machine.MachineController): the machine controller

        Returns:

        """
        self.machine = machine

        if not self.module_name:
            self.module_name = self.__class__.__name__

        if not self.config_name:
            x = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.module_name)
            self.config_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', x).lower()

        self.configure_logging(
            self.module_name,
            self.machine.machine_config['logging']['console'][self.config_name],
            self.machine.machine_config['logging']['file'][self.config_name])

        self.debug_log("Loading the {}".format(self.module_name))
