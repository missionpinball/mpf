"""Interface for switches."""
import abc
from typing import Any
from mpf.core.platform import SwitchConfig


class SwitchPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for switches in hardware platforms.

    SwitchPlatformInterface is an abstract base class that should be overridden for all
    switches interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support switch operations in MPF.
    """

    __slots__ = ["config", "number"]

    def __init__(self, config: SwitchConfig, number: Any) -> None:
        """Initialise default attributes for switches."""
        self.config = config    # type: SwitchConfig
        self.number = number    # type: Any

    @abc.abstractmethod
    def get_board_name(self):
        """Return the name of the board of this driver."""
        raise NotImplementedError

    def __repr__(self):
        """Return board + number."""
        return "<Switch {} {} (config: {})>".format(self.get_board_name(), self.number, self.config)
