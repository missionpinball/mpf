"""A switch input on a PKONE Extension board."""
import logging

from mpf.core.platform import SwitchConfig
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface


MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform    # pylint: disable-msg=cyclic-import,unused-import


class PKONESwitch(SwitchPlatformInterface):

    """An PKONE input on a PKONE Extension board."""

    __slots__ = ["log", "connection", "platform", "platform_settings"]

    def __init__(self, config: SwitchConfig, number_tuple, platform: "PKONEHardwarePlatform", platform_settings) -> None:
        """Initialise switch."""
        super().__init__(config, number_tuple)
        self.log = logging.getLogger('FASTSwitch')
        self.connection = number_tuple[1]
        self.platform = platform
        self.platform_settings = platform_settings

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "OPP {} Board {}".format(str(self.card.chain_serial), "0x%02x" % self.card.addr)
