from packaging import version

from mpf.platforms.fast.communicators.base import FastSerialCommunicator

MIN_FW = version.parse('0.10')

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import

class FastAudCommunicator(FastSerialCommunicator):

    """Handles the serial communication to the FAST platform."""

    IGNORED_MESSAGES = []
