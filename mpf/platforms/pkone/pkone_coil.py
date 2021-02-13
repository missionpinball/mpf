"""A coil/driver in the PKONE platform."""
import logging
from collections import namedtuple
from typing import Dict, Tuple, Optional

from mpf.core.platform import DriverConfig
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform    # pylint: disable-msg=cyclic-import,unused-import

PKONECoilNumber = namedtuple("PKONECoilNumber", ["board_address_id", "coil_number"])


class PKONECoil(DriverPlatformInterface):
    """Base class for coils/drivers connected to a PKONE Controller/Extension."""

    __slots__ = ["log", "autofire", "_autofire_cleared", "config_state", "machine", "platform", "coil_settings",
                 "send", "platform_settings"]

    def __init__(self, config: DriverConfig, platform: "PKONEHardwarePlatform", number: PKONECoilNumber,
                 platform_settings: dict) -> None:
        """Initialise Coil."""
        super().__init__(config, number)
        self.log = logging.getLogger('PKONECoil')
        self.autofire = None                        # type: Optional[Tuple[str, Dict[str, float]]]
        self._autofire_cleared = False
        self.config_state = None                    # type: Optional[Tuple[float, float, float]]
        self.machine = platform.machine
        self.platform = platform
        self.coil_settings = dict()               # type: Dict[str, str]
        self.send = platform.controller_connection.send
        self.platform_settings = platform_settings

        self.log.debug("Coil Settings: %s", self.coil_settings)
        self.reset()

    def get_board_name(self):
        """Return PKONE Extension addr."""
        if self.number.board_address_id not in self.platform.pkone_extensions.keys():
            return "PKONE Unknown Board"
        return "PKONE Extension Board {}".format(self.number.board_address_id)

    def get_recycle_ms_for_cmd(self, recycle, pulse_ms):
        """Return recycle ms."""
        if not recycle:
            return 0
        if self.platform_settings['recycle_ms'] is not None:
            return self.platform_settings['recycle_ms']

        # default recycle_ms to pulse_ms * 2 (cap at 250ms)
        return min(pulse_ms * 2, 250)

    def reset(self):
        """Reset a coil."""
        self.log.debug("Resetting coil %s", self.coil_settings)

        # TODO: Determine command to reset a driver/coil
        cmd = ""

        self.send(cmd)

    def disable(self):
        """Disable (turn off) this coil."""

        # TODO: Determine command to disable coil/driver
        cmd = ""

        self.log.debug("Sending Disable Command: %s", cmd)
        self.send(cmd)

        self._reenable_autofire_if_configured()

        # re-enable the autofire
        if self.autofire:
            # TODO: Determine command to re-enable hardware rule for a coil
            cmd = ""

            self.log.debug("Re-enabling auto fire mode: %s", cmd)
            self.send(cmd)

    def set_autofire(self, autofire_cmd, pulse_duration, pulse_power, hold_power):
        """Set an autofire."""
        self.autofire = autofire_cmd, (pulse_duration, pulse_power, hold_power)
        self.config_state = pulse_duration, pulse_power, hold_power
        self._autofire_cleared = False
        self.log.debug("Writing hardware rule: %s", autofire_cmd)
        self.send(autofire_cmd)

    def clear_autofire(self, config_cmd, number):
        """Clear autofire."""
        # TODO: Determine command to clear a hardware rule for a coil
        cmd = ""
        self.log.debug("Clearing hardware rule: %s", cmd)
        self.send(cmd)
        self.autofire = None
        self.config_state = None

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable (turn on) this coil/driver."""
        config_state = pulse_settings.duration, pulse_settings.power, hold_settings.power
        if self.autofire and self.config_state == config_state:
            # If this driver is also configured for an autofire rule, we just
            # manually trigger it with the trigger_cmd and manual on ('03')
            # TODO: Determine command to enable coil with a hardware rule
            cmd = ""
        else:
            # Otherwise we send a full config command, trigger C1 (logic triggered
            # and drive now) switch ID 00, mode 18 (latched)
            self._autofire_cleared = True

            # TODO: Determine command to enable this coil/driver with all options
            cmd = ""
            self.config_state = (pulse_settings.duration, pulse_settings.duration, hold_settings.power)

        self.log.debug("Sending Enable Command: %s", cmd)
        self.send(cmd)

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse this coil/driver."""
        # Determine existing configuration state
        config_state = (pulse_settings.duration, pulse_settings.power, 0)

        # Reconfigure configuration (if necessary)
        if not self.config_state or self.config_state[0] != config_state[0] or self.config_state[1] != config_state[1]:
            self.config_state = config_state
            self._autofire_cleared = True

            # TODO: Determine command to reconfigure coil/driver
            cmd = ""
            self.send(cmd)

        # pulse/trigger driver
        cmd = "PCP{}{}E".format(self.number.board_address_id, self.number.coil_number)
        self.send(cmd)

        # restore autofire
        self._reenable_autofire_if_configured()

        return pulse_settings.duration

    def _reenable_autofire_if_configured(self):
        """Reenable autofire if configured."""
        if self.autofire and self._autofire_cleared:
            self._autofire_cleared = False
            cmd = self.autofire[0]
            self.config_state = self.autofire[1]

            self.log.debug("Re-enabling auto fire mode: %s", cmd)
            self.send(cmd)
