"""A coil/driver in the PKONE platform."""
import logging
from collections import namedtuple
from typing import Optional

from mpf.core.platform import DriverConfig, SwitchSettings
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings

MYPY = False
if MYPY:  # pragma: no cover
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform  # pylint: disable-msg=cyclic-import,unused-import

PKONECoilNumber = namedtuple("PKONECoilNumber", ["board_address_id", "coil_number"])
PKONECoilConfiguration = namedtuple("PKONECoilConfiguration", ["pulse_settings", "hold_settings", "recycle_time"])


class PKONECoil(DriverPlatformInterface):

    """Base class for coils/drivers connected to a PKONE Controller/Extension."""

    __slots__ = ["log", "hardware_rule", "_config_state", "machine", "platform",
                 "send", "platform_settings"]

    def __init__(self, config: DriverConfig, platform: "PKONEHardwarePlatform", number: PKONECoilNumber,
                 platform_settings: dict) -> None:
        """Initialize Coil."""
        super().__init__(config, number)
        self.log = logging.getLogger('PKONECoil')
        self.hardware_rule = False  # type: bool
        self._config_state = None  # type: Optional[PKONECoilConfiguration]
        self.machine = platform.machine
        self.platform = platform
        self.send = platform.controller_connection.send
        self.platform_settings = platform_settings

        self.log.debug("Initialize Coil Settings: %s", self.config)
        self.reset()

    def get_board_name(self):
        """Return PKONE Extension addr."""
        if self.number.board_address_id not in self.platform.pkone_extensions.keys():
            return "PKONE Unknown Board"
        return "PKONE Extension Board {}".format(self.number.board_address_id)

    def get_recycle_time_ms_for_cmd(self, recycle, pulse_ms) -> int:
        """Return recycle ms."""
        if not recycle:
            return 0
        if self.platform_settings['recycle_ms'] is not None:
            return self.platform_settings['recycle_ms']

        # default recycle_ms to pulse_ms * 2 (cap at 500ms)
        return min(pulse_ms * 2, 500)

    def reset(self):
        """Reset a coil - removes all settings, including any hardware rules, for the coil."""
        self.log.debug("Resetting coil %s", self.number)

        # Ensure settings will be sent to the coil before it is activated again
        self._config_state = None

        if self.hardware_rule:
            self.clear_hardware_rule()

        # Configure coil with default/empty/0 settings (coil will not fire until it is configured with
        # real settings values)
        cmd = "PCC{}{:02d}0000000000".format(self.number.board_address_id, self.number.coil_number)
        self.send(cmd)

    def configure_coil(self, pulse_settings: PulseSettings, hold_settings: Optional[HoldSettings],
                       recycle_time: int = 0) -> None:
        """Configure a coil (will overwrite existing configuration settings)."""
        new_config_state = PKONECoilConfiguration(pulse_settings, hold_settings, recycle_time)

        # if config would not change do nothing
        if new_config_state == self._config_state:
            return

        # send the new coil configuration
        self._config_state = new_config_state
        cmd = "PCC{}{:02d}{:03d}{:02d}{:02d}{:03d}".format(self.number.board_address_id,
                                                           self.number.coil_number,
                                                           pulse_settings.duration,
                                                           # power must be mapped from 0-1 to 0-99
                                                           int(pulse_settings.power * 99),
                                                           int(hold_settings.power * 99) if hold_settings else 0,
                                                           recycle_time)
        self.log.debug("Sending Configure Coil command: %s", cmd)
        self.send(cmd)

    def disable(self) -> None:
        """Disable/release (turn off) this coil."""
        cmd = "PCR{}{:02d}".format(self.number.board_address_id, self.number.coil_number)
        self.log.debug("Sending Release/Disable Coil command: %s", cmd)
        self.send(cmd)

    # pylint: disable-msg=too-many-arguments
    def set_hardware_rule(self, mode: int, switch_settings: SwitchSettings,
                          eos_switch_settings: Optional[SwitchSettings], delay_time: int,
                          pulse_settings: PulseSettings, hold_settings: Optional[HoldSettings]) -> None:
        """Set a hardware rule for an autofire coil."""
        self.hardware_rule = True

        cmd = "PHR{}{:02d}{}{:02d}{}{:02d}{}" \
              "{:03d}{:03d}{:02d}{:02d}{:03d}".format(self.number.board_address_id,
                                                      self.number.coil_number,
                                                      mode,
                                                      switch_settings.hw_switch.number.switch_number,
                                                      1 if switch_settings.invert else 0,
                                                      eos_switch_settings.hw_switch.number.switch_number
                                                      if eos_switch_settings else 0,
                                                      1 if eos_switch_settings and eos_switch_settings.invert else 0,
                                                      delay_time,
                                                      pulse_settings.duration,
                                                      int(pulse_settings.power * 99),
                                                      int(hold_settings.power * 99) if hold_settings else 0,
                                                      self.get_recycle_time_ms_for_cmd(self.config.default_recycle,
                                                                                       pulse_settings.duration))

        self.log.debug("Writing Hardware Rule for coil: %s", cmd)
        self.send(cmd)

    def clear_hardware_rule(self) -> None:
        """Clear hardware rule."""
        cmd = "PHD{}{:02d}".format(self.number.board_address_id, self.number.coil_number)
        self.log.debug("Clearing Hardware Rule for coil: %s", cmd)
        self.send(cmd)
        self.hardware_rule = False

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings) -> None:
        """Enable (turn on) this coil/driver."""
        # reconfigure coil (if necessary)
        self.configure_coil(pulse_settings, hold_settings,
                            self.get_recycle_time_ms_for_cmd(self.config.default_recycle, pulse_settings.duration))
        cmd = "PCH{}{:02d}".format(self.number.board_address_id, self.number.coil_number)
        self.log.debug("Sending Hold/Enable coil command: %s", cmd)
        self.send(cmd)

    def pulse(self, pulse_settings: PulseSettings) -> None:
        """Pulse this coil/driver."""
        # reconfigure coil (if necessary) -- use existing hold settings (if they exist) as the
        # hold settings do not matter for a pulse command (may keep the coil configuration from
        # having to be rewritten)
        hold_settings = self._config_state.hold_settings if self._config_state else None
        self.configure_coil(pulse_settings, hold_settings,
                            self.get_recycle_time_ms_for_cmd(self.config.default_recycle, pulse_settings.duration))

        # pulse/trigger coil
        cmd = "PCP{}{:02}".format(self.number.board_address_id, self.number.coil_number)
        self.log.debug("Sending Pulse coil command: %s", cmd)
        self.send(cmd)

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and enable the coil for an explicit duration."""
        raise NotImplementedError
