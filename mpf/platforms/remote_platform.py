"""Remote hardware platform using BCP."""
from typing import Dict, TYPE_CHECKING

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.core.platform import SwitchPlatform, DriverPlatform, DriverConfig, SwitchSettings, DriverSettings

if TYPE_CHECKING:
    from mpf.core.machine import MachineController


class RemoteHardwarePlatform(SwitchPlatform, DriverPlatform):

    """Remote hardware platform using BCP."""

    def __init__(self, machine):
        """Initialise remote hardware platform."""

        self._switches = {}     # type: Dict[str, RemoteSwitch]
        self.machine.bcp.interface.register_command_callback("remote_switch_change", self._remote_switch_change)
        self._initialised = False
        super().__init__(machine)
        # TODO: wait for remote to connect

    def initialize(self):
        self._initialised = True

    def stop(self):
        pass

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        self._add_rule("pulse_on_hit_and_enable_and_release", enable_switch, coil)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        self._add_rule("pulse_on_hit", enable_switch, coil)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        self._add_rule("pulse_on_hit_and_release", enable_switch, coil)

    def _add_rule(self, name: str, enable_switch: SwitchSettings, coil: DriverSettings):
        self.machine.bcp.transport.send_to_clients_with_handler(
            "remote_platform", "remote_rule",
            action=name,
            enable_switch_number=enable_switch.number,
            enable_switch_invert=enable_switch.invert,
            enable_switch_debounce=enable_switch.debounce,
            coil_number=coil.number,
            coil_pulse_power=coil.pulse_settings.power,
            coil_pulse_ms=coil.pulse_settings.duration,
            coil_hold_power=coil.hold_settings.power if coil.hold_settings else 0,
            coil_recycle=coil.recycle)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 disable_switch: SwitchSettings,
                                                                 coil: DriverSettings):
        self.machine.bcp.transport.send_to_clients_with_handler(
            "remote_platform", "remote_rule",
            action="pulse_on_hit_and_enable_and_release_and_disable",
            enable_switch_number=enable_switch.number,
            enable_switch_invert=enable_switch.invert,
            enable_switch_debounce=enable_switch.debounce,
            disable_switch_number=disable_switch.number,
            disable_switch_invert=disable_switch.invert,
            disable_switch_debounce=disable_switch.debounce,
            coil_number=coil.number,
            coil_pulse_power=coil.pulse_settings.power,
            coil_pulse_ms=coil.pulse_settings.duration,
            coil_hold_power=coil.hold_settings.power if coil.hold_settings else 0,
            coil_recycle=coil.recycle)

    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """Remove remote rule."""
        self.machine.bcp.transport.send_to_clients_with_handler("remote_platform", "remote_rule",
                                                                action="remove",
                                                                switch_number=switch.number,
                                                                switch_invert=switch.invert,
                                                                switch_debounce=switch.debounce,
                                                                coil_numbre=coil.number)

    def _remote_switch_change(self, switch_number, state, **kwargs):
        del kwargs
        self._switches[switch_number].state = state
        if self._initialised:
            self.machine.switch_controller.process_switch_by_num(switch_number, state, self)

    def configure_switch(self, config):
        """Configure remote switch."""
        number = config['number']
        switch = RemoteSwitch(number)
        self._switches[number] = switch
        return switch

    def get_hw_switch_states(self):
        """Return remote switch states."""
        states = {}
        for switch in self._switches.values():
            states[switch.number] = switch.state
        return states

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
        """Configure remote driver."""
        return RemoteDriver(number, self.machine)


class RemoteSwitch(SwitchPlatformInterface):

    """Represents a remote switch."""

    def __init__(self, number: str):
        """Initialise switch."""
        super().__init__({}, number)
        self.state = 0


class RemoteDriver(DriverPlatformInterface):

    """A remote driver object."""

    def __init__(self, number: str, machine: "MachineController") -> None:
        """Initialise remote driver."""
        super().__init__({}, number)
        self.machine = machine

    def get_board_name(self):
        """Return the name of the board of this driver."""
        return "Remote"

    def __repr__(self):
        """Str representation."""
        return "RemoteDriver.{}".format(self.number)

    def disable(self):
        """Disable remote coil."""
        self.machine.bcp.transport.send_to_clients_with_handler("remote_platform", "remote_driver",
                                                                number=self.number,
                                                                action="disable")

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable remote coil."""
        self.machine.bcp.transport.send_to_clients_with_handler("remote_platform", "remote_driver",
                                                                number=self.number,
                                                                action="enable",
                                                                pulse_ms=pulse_settings.duration,
                                                                pulse_power=pulse_settings.power,
                                                                hold_power=hold_settings.power)

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse remote coil."""
        self.machine.bcp.transport.send_to_clients_with_handler("remote_platform", "remote_driver",
                                                                number=self.number,
                                                                action="pulse",
                                                                pulse_ms=pulse_settings.duration,
                                                                pulse_power=pulse_settings.power)
