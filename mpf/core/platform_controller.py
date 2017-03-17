from collections import namedtuple

from mpf.core.mpf_controller import MpfController
from mpf.core.platform import DriverPlatform, SwitchSettings, DriverSettings
from mpf.devices.driver import Driver
from mpf.devices.switch import Switch
from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings

SwitchRuleSettings = namedtuple("SwitchRuleSettings", ["switch", "invert", "debounce"])
DriverRuleSettings = namedtuple("DriverRuleSettings", ["driver", "recycle"])
PulseRuleSettings = namedtuple("PulseRuleSettings", ["power", "duration"])
HoldRuleSettings = namedtuple("HoldRuleSettings", ["power"])
HardwareRule = namedtuple("HardwareRule", ["switch_settings", "driver_settings"])


class PlatformController(MpfController):

    """Manages all platforms and rules."""

    def __init__(self, machine):
        """Initialise platform controller."""
        super().__init__(machine)

    @staticmethod
    def _check_and_get_platform(switch: Switch, driver: Driver) -> DriverPlatform:
        if driver.platform != switch.platform:
            raise AssertionError("Switch and Coil have to use the same platform")

        return driver.platform

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchRuleSettings,
                                          driver: DriverRuleSettings,
                                          pulse_setting: PulseRuleSettings = None) -> HardwareRule:
        """Add pulse on hit and relase rule to driver.

        Pulse a driver but cancel pulse when switch is released.

        Args:
            enable_switch: Switch which triggers the rule.
        """
        platform = self._check_and_get_platform(enable_switch.switch, driver.driver)

        pulse_duration = driver.driver.get_and_verify_pulse_ms(pulse_setting.duration if pulse_setting else None)
        pulse_power = driver.driver.get_and_verify_pulse_power(pulse_setting.power if pulse_setting else None)

        platform.set_pulse_on_hit_and_release_rule(
            SwitchSettings(hw_switch=enable_switch.switch.hw_switch,
                           invert=enable_switch.invert != enable_switch.switch.invert,
                           debounce=enable_switch.debounce),
            DriverSettings(hw_driver=driver.driver.hw_driver,
                           pulse_settings=PulseSettings(duration=pulse_duration, power=pulse_power),
                           hold_settings=None,
                           recycle=driver.recycle))

        return HardwareRule(switch_settings=[enable_switch], driver_settings=driver)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchRuleSettings,
                                                     driver: DriverRuleSettings,
                                                     pulse_setting: PulseRuleSettings = None,
                                                     hold_settings: HoldRuleSettings = None) -> HardwareRule:
        """Add pulse on hit and enable and relase rule to driver.

        Pulse and enable a driver. Cancel pulse and enable if switch is released.

        Args:
            enable_switch: Switch which triggers the rule.
            driver: Driver to trigger.
        """
        platform = self._check_and_get_platform(enable_switch.switch, driver.driver)

        pulse_duration = driver.driver.get_and_verify_pulse_ms(pulse_setting.duration if pulse_setting else None)
        pulse_power = driver.driver.get_and_verify_pulse_power(pulse_setting.power if pulse_setting else None)
        hold_power = driver.driver.get_and_verify_hold_power(hold_settings.power if hold_settings else None)

        platform.set_pulse_on_hit_and_enable_and_release_rule(
            SwitchSettings(hw_switch=enable_switch.switch.hw_switch,
                           invert=enable_switch.invert != enable_switch.switch.invert,
                           debounce=enable_switch.debounce),
            DriverSettings(hw_driver=driver.driver.hw_driver,
                           pulse_settings=PulseSettings(duration=pulse_duration, power=pulse_power),
                           hold_settings=HoldSettings(power=hold_power),
                           recycle=driver.recycle))

        return HardwareRule(switch_settings=[enable_switch], driver_settings=driver)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchRuleSettings,
                              driver: DriverRuleSettings,
                              pulse_setting: PulseRuleSettings = None) -> HardwareRule:
        """Add pulse on hit rule to driver.

        Alway do the full pulse. Even when the switch is released.

        Args:
            enable_switch: Switch which triggers the rule.
        """
        platform = self._check_and_get_platform(enable_switch.switch, driver.driver)

        pulse_duration = driver.driver.get_and_verify_pulse_ms(pulse_setting.duration if pulse_setting else None)
        pulse_power = driver.driver.get_and_verify_pulse_power(pulse_setting.power if pulse_setting else None)

        platform.set_pulse_on_hit_rule(
            SwitchSettings(hw_switch=enable_switch.switch.hw_switch,
                           invert=enable_switch.invert != enable_switch.switch.invert,
                           debounce=enable_switch.debounce),
            DriverSettings(hw_driver=driver.driver.hw_driver,
                           pulse_settings=PulseSettings(duration=pulse_duration, power=pulse_power),
                           hold_settings=None,
                           recycle=driver.recycle))

        return HardwareRule(switch_settings=[enable_switch], driver_settings=driver)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchRuleSettings,
                                                                 disable_switch: SwitchRuleSettings,
                                                                 driver: DriverRuleSettings,
                                                                 pulse_setting: PulseRuleSettings = None,
                                                                 hold_settings: HoldRuleSettings = None) -> HardwareRule:
        """Add pulse on hit and enable and release and disable rule to driver.

        Pulse and then enable driver. Cancel pulse and enable when switch is released or a disable switch is hit.

        Args:
            enable_switch: Switch which triggers the rule.
            disable_switch: Switch which disables the rule.
        """
        platform = self._check_and_get_platform(enable_switch.switch, driver.driver)
        self._check_and_get_platform(disable_switch.switch, driver.driver)

        pulse_duration = driver.driver.get_and_verify_pulse_ms(pulse_setting.duration if pulse_setting else None)
        pulse_power = driver.driver.get_and_verify_pulse_power(pulse_setting.power if pulse_setting else None)
        hold_power = driver.driver.get_and_verify_hold_power(hold_settings.power if hold_settings else None)

        platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule(
            SwitchSettings(hw_switch=enable_switch.switch.hw_switch,
                           invert=enable_switch.invert != enable_switch.switch.invert,
                           debounce=enable_switch.debounce),
            SwitchSettings(hw_switch=disable_switch.switch.hw_switch,
                           invert=disable_switch.invert != disable_switch.switch.invert,
                           debounce=disable_switch.debounce),
            DriverSettings(hw_driver=driver.driver.hw_driver,
                           pulse_settings=PulseSettings(duration=pulse_duration, power=pulse_power),
                           hold_settings=HoldSettings(power=hold_power),
                           recycle=driver.recycle))

        return HardwareRule(switch_settings=[enable_switch], driver_settings=driver)

    def clear_hw_rule(self, rule: HardwareRule):
        """Clear all rules for switch and this driver.

        Args:
            switch: Switch to clear on this driver.
        """
        for switch_settings in rule.switch_settings:
            rule.driver_settings.driver.platform.clear_hw_rule(switch_settings, rule.driver_settings)
