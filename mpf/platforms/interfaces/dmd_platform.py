"""Interface for monochrome and rgb platform devices."""
import abc


class DmdPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for monochrome DMDs in hardware platforms."""

    @abc.abstractmethod
    def update(self, data: bytes):
        """Update data on the DMD.

        Args:
            data: bytes to send to DMD
        """
        raise NotImplementedError('implement')
