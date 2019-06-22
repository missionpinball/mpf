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

    config_name = "platform_controller"

    @staticmethod
    def _check_and_get_platform(switch: Switch, driver: Driver) -> DriverPlatform:
        if driver.platform != switch.platform:
            raise AssertionError("Switch and Coil have to use the same platform")

        return driver.platform

    def _setup_switch_callback_for_psu(self, switch: Switch, driver: Driver, switch_settings: SwitchSettings,
                                       driver_settings: DriverSettings) -> Optional[SwitchHandler]:
        """Set up a switch handler which informs the PSU about pulses performed by the rule."""
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
        """Return configured driver with hold > 0 for rule."""
        pulse_duration = driver.driver.get_and_verify_pulse_ms(pulse_setting.duration if pulse_setting else None)
        pulse_power = driver.driver.get_and_verify_pulse_power(pulse_setting.power if pulse_setting else None)
        hold_power = driver.driver.get_and_verify_hold_power(hold_settings.power if hold_settings else None)

        if hold_power == 0.0:
            raise AssertionError("Cannot enable driver with hold_power 0.0")

        return DriverSettings(
            hw_driver=driver.driver.hw_driver,
            pulse_settings=PulseSettings(duration=pulse_duration, power=pulse_power),
            hold_settings=HoldSettings(power=hold_power),
            recycle=driver.recycle)

    @staticmethod
    def _get_configured_driver_with_optional_hold(driver: DriverRuleSettings, pulse_setting: PulseRuleSettings,
                                                  hold_settings: HoldRuleSettings) -> DriverSettings:
        """Return configured driver for rule which might have hold."""
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
        """Return configured driver without hold for rule."""
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
            driver: .. class:: DriverRuleSettings
            pulse_setting: .. class:: PulseRuleSettings
        """
        platform = self._check_and_get_platform(enable_switch.switch, driver.driver)

        enable_settings = self._get_configured_switch(enable_switch)
        driver_settings = self._get_configured_driver_no_hold(driver, pulse_setting)

        platform.set_pulse_on_hit_and_release_rule(enable_settings, driver_settings)

        switch_key = self._setup_switch_callback_for_psu(enable_switch.switch, driver.driver, enable_settings,
                                                         driver_settings)

        self.machine.bcp.interface.send_driver_event(
            action="pulse_on_hit_and_release",
            enable_switch_number=enable_switch.switch.hw_switch.number,
            enable_switch_name=enable_switch.switch.name,
            enable_switch_invert=enable_settings.invert,
            enable_switch_debounce=enable_settings.debounce,
            coil_number=driver.driver.hw_driver.number,
            coil_name=driver.driver.name,
            coil_pulse_power=driver_settings.pulse_settings.power,
            coil_pulse_ms=driver_settings.pulse_settings.duration,
            coil_hold_power=0,
            coil_recycle=driver_settings.recycle)

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
            pulse_setting: .. class:: PulseRuleSettings
            hold_settings: .. class:: HoldRuleSettings
        """
        platform = self._check_and_get_platform(enable_switch.switch, driver.driver)

        enable_settings = self._get_configured_switch(enable_switch)
        driver_settings = self._get_configured_driver_with_hold(driver, pulse_setting, hold_settings)

        platform.set_pulse_on_hit_and_enable_and_release_rule(enable_settings, driver_settings)

        switch_key = self._setup_switch_callback_for_psu(enable_switch.switch, driver.driver, enable_settings,
                                                         driver_settings)

        self.machine.bcp.interface.send_driver_event(
            action="pulse_on_hit_and_enable_and_release",
            enable_switch_number=enable_switch.switch.hw_switch.number,
            enable_switch_name=enable_switch.switch.name,
            enable_switch_invert=enable_settings.invert,
            enable_switch_debounce=enable_settings.debounce,
            coil_number=driver.driver.hw_driver.number,
            coil_name=driver.driver.name,
            coil_pulse_power=driver_settings.pulse_settings.power,
            coil_pulse_ms=driver_settings.pulse_settings.duration,
            coil_hold_power=driver_settings.hold_settings,
            coil_recycle=driver_settings.recycle)

        return HardwareRule(platform=platform, switch_settings=[enable_settings], driver_settings=driver_settings,
                            switch_key=switch_key)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchRuleSettings,
                              driver: DriverRuleSettings,
                              pulse_setting: PulseRuleSettings = None) -> HardwareRule:
        """Add pulse on hit rule to driver.

        Always do the full pulse. Even when the switch is released.

        Args:
            enable_switch: Switch which triggers the rule.
            driver: .. class:: DriverRuleSettings
            pulse_setting: .. class:: PulseRuleSettings
        """
        platform = self._check_and_get_platform(enable_switch.switch, driver.driver)

        enable_settings = self._get_configured_switch(enable_switch)
        driver_settings = self._get_configured_driver_no_hold(driver, pulse_setting)

        platform.set_pulse_on_hit_rule(enable_settings, driver_settings)

        switch_key = self._setup_switch_callback_for_psu(enable_switch.switch, driver.driver, enable_settings,
                                                         driver_settings)

        self.machine.bcp.interface.send_driver_event(
            action="pulse_on_hit",
            enable_switch_number=enable_switch.switch.hw_switch.number,
            enable_switch_name=enable_switch.switch.name,
            enable_switch_invert=enable_settings.invert,
            enable_switch_debounce=enable_settings.debounce,
            coil_number=driver.driver.hw_driver.number,
            coil_name=driver.driver.name,
            coil_pulse_power=driver_settings.pulse_settings.power,
            coil_pulse_ms=driver_settings.pulse_settings.duration,
            coil_hold_power=0,
            coil_recycle=driver_settings.recycle)

        return HardwareRule(platform=platform, switch_settings=[enable_settings], driver_settings=driver_settings,
                            switch_key=switch_key)

    # pylint: disable-msg=too-many-arguments
    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchRuleSettings,
                                                                 disable_switch: SwitchRuleSettings,
                                                                 driver: DriverRuleSettings,
                                                                 pulse_setting: PulseRuleSettings = None,
                                                                 hold_settings: HoldRuleSettings = None
                                                                 ) -> HardwareRule:
        """Add pulse on hit and enable and release and disable rule to driver.

        Pulse and then enable driver. Cancel pulse and enable when switch is released or a disable switch is hit.

        Args:
            enable_switch:
            disable_switch:
            driver:
            pulse_setting:
            hold_settings:
        """
        platform = self._check_and_get_platform(enable_switch.switch, driver.driver)
        self._check_and_get_platform(disable_switch.switch, driver.driver)

        enable_settings = self._get_configured_switch(enable_switch)
        disable_settings = self._get_configured_switch(disable_switch)
        driver_settings = self._get_configured_driver_with_optional_hold(driver, pulse_setting, hold_settings)

        platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule(
            enable_settings, disable_settings, driver_settings)

        switch_key = self._setup_switch_callback_for_psu(enable_switch.switch, driver.driver, enable_settings,
                                                         driver_settings)

        self.machine.bcp.interface.send_driver_event(
            action="pulse_on_hit_and_enable_and_release_and_disable",
            enable_switch_number=enable_switch.switch.hw_switch.number,
            enable_switch_name=enable_switch.switch.name,
            enable_switch_invert=enable_settings.invert,
            enable_switch_debounce=enable_settings.debounce,
            disable_switch_number=disable_switch.switch.hw_switch.number,
            disable_switch_name=disable_switch.switch.name,
            disable_switch_invert=disable_settings.invert,
            disable_switch_debounce=disable_settings.debounce,
            coil_number=driver.driver.hw_driver.number,
            coil_name=driver.driver.name,
            coil_pulse_power=driver_settings.pulse_settings.power,
            coil_pulse_ms=driver_settings.pulse_settings.duration,
            coil_hold_power=driver_settings.hold_settings,
            coil_recycle=driver_settings.recycle)

        return HardwareRule(platform=platform, switch_settings=[enable_settings, disable_settings],
                            driver_settings=driver_settings, switch_key=switch_key)

    def clear_hw_rule(self, rule: HardwareRule):
        """Clear all rules for switch and this driver.

        Args:
            rule: Hardware rule to clean.
        """
        for switch_settings in rule.switch_settings:
            rule.platform.clear_hw_rule(switch_settings, rule.driver_settings)

            self.machine.bcp.interface.send_driver_event(
                action="remove",
                enable_switch_number=switch_settings.hw_switch.number,
                enable_switch_invert=switch_settings.invert,
                coil_number=rule.driver_settings.hw_driver.number)

        if rule.switch_key:
            self.machine.switch_controller.remove_switch_handler_by_key(rule.switch_key)
