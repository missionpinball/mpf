"""Controls the rules on all platforms."""
from collections import namedtuple

from typing import Optional

from mpf.core.mpf_controller import MpfController
from mpf.core.platform import DriverPlatform, SwitchSettings, DriverSettings
from mpf.core.switch_controller import SwitchHandler
from mpf.devices.driver import Driver
from mpf.devices.switch import Switch
from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings

SwitchRuleSettings = namedtuple("SwitchRuleSettings", ["switch", "invert", "debounce"])
DriverRuleSettings = namedtuple("DriverRuleSettings", ["driver", "recycle"])
PulseRuleSettings = namedtuple("PulseRuleSettings", ["power", "duration"])
HoldRuleSettings = namedtuple("HoldRuleSettings", ["power"])
HardwareRule = namedtuple("HardwareRule", ["platform", "switch_settings", "driver_settings", "switch_key"])


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

    def _setup_switch_callback_for_psu(self, switch: Switch, driver: Driver, switch_settings: SwitchSettings,
                                       driver_settings: DriverSettings) -> Optional[SwitchHandler]:
        """Setup a switch handler which """
        if driver_settings.pulse_settings.duration == 0:
            return None

        key = self.machine.switch_controller.add_switch_handler(
            switch_name=switch.name,
            state=0 if switch_settings.invert else 1,
            callback=self._notify_psu_about_pulse,
            callback_kwargs={"driver": driver,
                             "pulse_ms": driver_settings.pulse_settings.duration})

        return key

    @staticmethod
    def _notify_psu_about_pulse(driver: Driver, pulse_ms: int):
        """Notify PSU that a pulse via a rule happened."""
        driver.config['psu'].notify_about_instant_pulse(pulse_ms=pulse_ms)

    @staticmethod
    def _get_configured_switch(switch: SwitchRuleSettings) -> SwitchSettings:
        """Return configured switch for rule."""
        return SwitchSettings(
            hw_switch=switch.switch.hw_switch,
            invert=switch.invert != switch.switch.invert,
            debounce=switch.debounce)

    @staticmethod
    def _get_configured_driver_with_hold(driver: DriverRuleSettings, pulse_setting: PulseRuleSettings,
                                         hold_settings: HoldRuleSettings) -> DriverSettings:
        """Return configured driver for rule."""
        pulse_duration = driver.driver.get_and_verify_pulse_ms(pulse_setting.duration if pulse_setting else None)
        pulse_power = driver.driver.get_and_verify_pulse_power(pulse_setting.power if pulse_setting else None)
        hold_power = driver.driver.get_and_verify_hold_power(hold_settings.power if hold_settings else None)
        return DriverSettings(
            hw_driver=driver.driver.hw_driver,
            pulse_settings=PulseSettings(duration=pulse_duration, power=pulse_power),
            hold_settings=HoldSettings(power=hold_power),
            recycle=driver.recycle)

    @staticmethod
    def _get_configured_driver_no_hold(driver: DriverRuleSettings, pulse_setting: PulseRuleSettings) -> DriverSettings:
        """Return configured driver for rule."""
        pulse_duration = driver.driver.get_and_verify_pulse_ms(pulse_setting.duration if pulse_setting else None)
        pulse_power = driver.driver.get_and_verify_pulse_power(pulse_setting.power if pulse_setting else None)
        return DriverSettings(
            hw_driver=driver.driver.hw_driver,
            pulse_settings=PulseSettings(duration=pulse_duration, power=pulse_power),
            hold_settings=None,
            recycle=driver.recycle)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchRuleSettings,
                                          driver: DriverRuleSettings,
                                          pulse_setting: PulseRuleSettings = None) -> HardwareRule:
        """Add pulse on hit and relase rule to driver.

        Pulse a driver but cancel pulse when switch is released.

        Args:
            enable_switch: Switch which triggers the rule.
        """
        platform = self._check_and_get_platform(enable_switch.switch, driver.driver)

        enable_settings = self._get_configured_switch(enable_switch)
        driver_settings = self._get_configured_driver_no_hold(driver, pulse_setting)

        platform.set_pulse_on_hit_and_release_rule(enable_settings, driver_settings)

        switch_key = self._setup_switch_callback_for_psu(enable_switch.switch, driver.driver, enable_settings,
                                                         driver_settings)

        return HardwareRule(platform=platform, switch_settings=[enable_settings], driver_settings=driver_settings,
                            switch_key=switch_key)

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

        enable_settings = self._get_configured_switch(enable_switch)
        driver_settings = self._get_configured_driver_with_hold(driver, pulse_setting, hold_settings)

        platform.set_pulse_on_hit_and_enable_and_release_rule(enable_settings, driver_settings)

        switch_key = self._setup_switch_callback_for_psu(enable_switch.switch, driver.driver, enable_settings,
                                                         driver_settings)

        return HardwareRule(platform=platform, switch_settings=[enable_settings], driver_settings=driver_settings,
                            switch_key=switch_key)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchRuleSettings,
                              driver: DriverRuleSettings,
                              pulse_setting: PulseRuleSettings = None) -> HardwareRule:
        """Add pulse on hit rule to driver.

        Alway do the full pulse. Even when the switch is released.

        Args:
            enable_switch: Switch which triggers the rule.
        """
        platform = self._check_and_get_platform(enable_switch.switch, driver.driver)

        enable_settings = self._get_configured_switch(enable_switch)
        driver_settings = self._get_configured_driver_no_hold(driver, pulse_setting)

        platform.set_pulse_on_hit_rule(enable_settings, driver_settings)

        switch_key = self._setup_switch_callback_for_psu(enable_switch.switch, driver.driver, enable_settings,
                                                         driver_settings)

        return HardwareRule(platform=platform, switch_settings=[enable_settings], driver_settings=driver_settings,
                            switch_key=switch_key)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchRuleSettings,
                                                                 disable_switch: SwitchRuleSettings,
                                                                 driver: DriverRuleSettings,
                                                                 pulse_setting: PulseRuleSettings = None,
                                                                 hold_settings: HoldRuleSettings = None
                                                                 ) -> HardwareRule:
        """Add pulse on hit and enable and release and disable rule to driver.

        Pulse and then enable driver. Cancel pulse and enable when switch is released or a disable switch is hit.

        Args:
            enable_switch: Switch which triggers the rule.
            disable_switch: Switch which disables the rule.
        """
        platform = self._check_and_get_platform(enable_switch.switch, driver.driver)
        self._check_and_get_platform(disable_switch.switch, driver.driver)

        enable_settings = self._get_configured_switch(enable_switch)
        disable_settings = self._get_configured_switch(disable_switch)
        driver_settings = self._get_configured_driver_with_hold(driver, pulse_setting, hold_settings)

        platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule(
            enable_settings, disable_settings, driver_settings)

        switch_key = self._setup_switch_callback_for_psu(enable_switch.switch, driver.driver, enable_settings,
                                                         driver_settings)

        return HardwareRule(platform=platform, switch_settings=[enable_settings, disable_settings],
                            driver_settings=driver_settings, switch_key=switch_key)

    def clear_hw_rule(self, rule: HardwareRule):
        """Clear all rules for switch and this driver.

        Args:
            rule: Hardware rule to clean.
        """
        for switch_settings in rule.switch_settings:
            rule.platform.clear_hw_rule(switch_settings, rule.driver_settings)

        if rule.switch_key:
            self.machine.switch_controller.remove_switch_handler_by_key(rule.switch_key)
