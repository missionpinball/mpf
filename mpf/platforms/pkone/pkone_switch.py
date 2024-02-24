"""A switch input on a PKONE Extension board."""
import logging
from collections import namedtuple

from mpf.core.platform import SwitchConfig
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform    # pylint: disable-msg=cyclic-import,unused-import

PKONESwitchNumber = namedtuple("PKONESwitchNumber", ["board_address_id", "switch_number"])


# pylint: disable-msg=too-few-public-methods
class PKONESwitch(SwitchPlatformInterface):

    """An PKONE input on a PKONE Extension board."""

    __slots__ = ["log"]

    def __init__(self, config: SwitchConfig, number: PKONESwitchNumber, platform: "PKONEHardwarePlatform") -> None:
        """initialize switch."""
        super().__init__(config, number, platform)
        self.log = logging.getLogger('PKONESwitch')

    def get_board_name(self):
        """Return PKONE Extension addr."""
        if self.number.board_address_id not in self.platform.pkone_extensions.keys():
            return "PKONE Unknown Board"
        return "PKONE Extension Board {}".format(self.number.board_address_id)
