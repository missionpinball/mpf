"""A switch input on a PKONE Extension board."""
import logging

from typing import Tuple

from mpf.core.platform import SwitchConfig
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface


MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform    # pylint: disable-msg=cyclic-import,unused-import


class PKONESwitch(SwitchPlatformInterface):
    """An PKONE input on a PKONE Extension board."""

    __slots__ = ["log", "platform"]

    def __init__(self, config: SwitchConfig, number_tuple: Tuple[int, int], platform: "PKONEHardwarePlatform") -> None:
        """Initialise switch."""
        super().__init__(config, number_tuple)
        self.log = logging.getLogger('PKONESwitch')
        self.platform = platform

    def get_board_name(self):
        """Return PKONE Extension addr."""
        return "PKONE Extension Board {}".format(self.number[0])
