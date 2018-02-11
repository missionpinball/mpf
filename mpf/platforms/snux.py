"""Contains the base class for the Snux driver overlay.

This class overlays an existing WPC-compatible platform interface to work with
Mark Sunnucks's System 11 interface board.
"""
import asyncio
import logging

from typing import Any, Optional, Set, Tuple

from mpf.core.machine import MachineController
from mpf.core.platform import DriverPlatform, DriverConfig

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings

from mpf.core.delays import DelayManager


# pylint: disable-msg=too-many-instance-attributes
class SnuxHardwarePlatform(DriverPlatform):

    """Overlay platform for the snux hardware board."""

    def __init__(self, machine: MachineController) -> None:
        """Initalise the board."""
        super().__init__(machine)

        self.log = logging.getLogger('Platform.Snux')
        self.delay = DelayManager(machine.delayRegistry)

        self.platform = None            # type: DriverPlatform

        self.system11_config = None     # type: Any
        self.snux_config = None         # type: Any

        self.a_side_queue = set()       # type: Set[Tuple[DriverPlatformInterface, PulseSettings, HoldSettings]]
        self.c_side_queue = set()       # type: Set[Tuple[DriverPlatformInterface, PulseSettings, HoldSettings]]

        self.a_drivers = set()          # type: Set[DriverPlatformInterface]
        self.c_drivers = set()          # type: Set[DriverPlatformInterface]

        self.a_side_done_time = 0
        self.c_side_done_time = 0
        self.drivers_holding_a_side = set()     # type: Set[DriverPlatformInterface]
        self.drivers_holding_c_side = set()     # type: Set[DriverPlatformInterface]
        self.a_side_enabled = True
        self.c_side_enabled = False

        self.ac_relay_in_transition = False

    def stop(self):
        """Stop the overlay. Nothing to do here because stop is also called on parent platform."""
        pass

    @property
    def a_side_busy(self):
        """Return if A side cannot be switches off right away."""
        return self.drivers_holding_a_side or self.a_side_done_time > self.machine.clock.get_time() or self.a_side_queue

    @property
    def c_side_active(self):
        """Return if C side cannot be switches off right away."""
        return self.drivers_holding_c_side or self.c_side_done_time > self.machine.clock.get_time()

    def _null_log_handler(self, *args, **kwargs):
        pass

    @asyncio.coroutine
    def initialize(self):
        """Automatically called by the Platform class after all the core modules are loaded."""
        # load coil platform
        self.platform = self.machine.get_platform_sections(
            "platform", getattr(self.machine.config['snux'], 'platform', None))

        # we have to wait for coils to be initialized
        self.machine.events.add_handler("init_phase_1", self._initialize)

    def _initialize(self, **kwargs):
        del kwargs
        self._validate_config()

        self.log.debug("Configuring Snux Diag LED for driver %s",
                       self.snux_config['diag_led_driver'].name)

        # Hack to silence logging of P_ROC
        # TODO: clean this up
        self.snux_config['diag_led_driver'].hw_driver.log.info = self._null_log_handler
        self.snux_config['diag_led_driver'].hw_driver.log.debug = self._null_log_handler

        self.snux_config['diag_led_driver'].enable()

        self.log.debug("Configuring A/C Select Relay for driver %s",
                       self.system11_config['ac_relay_driver'].name)

        self.system11_config['ac_relay_driver'].get_and_verify_hold_power(1.0)

        self.log.debug("Configuring A/C Select Relay transition delay for "
                       "%sms", self.system11_config['ac_relay_delay_ms'])

        self.log.debug("Configuring Flipper Enable for driver %s",
                       self.snux_config['flipper_enable_driver'].name)

        self.snux_config['flipper_enable_driver'].get_and_verify_hold_power(1.0)

        self.machine.events.add_handler('init_phase_5',
                                        self._initialize_phase_2)

    def _initialize_phase_2(self, **kwargs):
        del kwargs
        self.machine.clock.schedule_interval(self._flash_diag_led, 0.5)

    def _validate_config(self):
        self.system11_config = self.machine.config_validator.validate_config(
            'system11', self.machine.config['system11'])

        self.snux_config = self.machine.config_validator.validate_config(
            'snux', self.machine.config['snux'])

    def tick(self):
        """Snux main loop.

        Called based on the timer_tick event
        """
        if self.a_side_queue:
            self._service_a_side()
        elif self.c_side_queue:
            self._service_c_side()
        elif self.c_side_enabled and not self.c_side_active:
            self._enable_a_side()

    def _flash_diag_led(self):
        """Flash diagnosis LED."""
        self.snux_config['diag_led_driver'].pulse(250)

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
        """Configure a driver on the snux board.

        Args:
            config: Driver config dict
        """
        orig_number = number

        if number and (number.endswith('a') or number.lower().endswith('c')):

            number = number[:-1]

            platform_driver = self.platform.configure_driver(config, number, platform_settings)

            snux_driver = SnuxDriver(orig_number, platform_driver, self)

            if orig_number.lower().endswith('a'):
                self._add_a_driver(snux_driver.platform_driver)
            elif orig_number.lower().endswith('c'):
                self._add_c_driver(snux_driver.platform_driver)

            return snux_driver

        else:
            return self.platform.configure_driver(config, number, platform_settings)

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Configure a rule for a driver on the snux board.

        Will pass the call onto the parent platform if the driver is not on A/C relay.
        """
        if coil.hw_driver in self.a_drivers or coil.hw_driver in self.c_drivers:
            self.log.warning("Received a request to set a hardware rule for a"
                             "switched driver. Ignoring")
        else:
            self.platform.set_pulse_on_hit_and_release_rule(enable_switch, coil)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        """Configure a rule for a driver on the snux board.

        Will pass the call onto the parent platform if the driver is not on A/C relay.
        """
        if coil.hw_driver in self.a_drivers or coil.hw_driver in self.c_drivers:
            self.log.warning("Received a request to set a hardware rule for a"
                             "switched driver. Ignoring")
        else:
            self.platform.set_pulse_on_hit_and_enable_and_release_rule(enable_switch, coil)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        """Configure a rule for a driver on the snux board.

        Will pass the call onto the parent platform if the driver is not on A/C relay.
        """
        if coil.hw_driver in self.a_drivers or coil.hw_driver in self.c_drivers:
            self.log.warning("Received a request to set a hardware rule for a"
                             "switched driver. Ignoring")
        else:
            self.platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule(enable_switch, disable_switch, coil)

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        """Configure a rule on the snux board.

        Will pass the call onto the parent platform if the driver is not on A/C relay.
        """
        if coil.hw_driver in self.a_drivers or coil.hw_driver in self.c_drivers:
            self.log.warning("Received a request to set a hardware rule for a"
                             "switched driver. Ignoring")
        else:
            self.platform.set_pulse_on_hit_rule(enable_switch, coil)

    def clear_hw_rule(self, switch, coil):
        """Clear a rule for a driver on the snux board."""
        self.platform.clear_hw_rule(switch, coil)

    def driver_action(self, driver, pulse_settings: Optional[PulseSettings], hold_settings: Optional[HoldSettings]):
        """Add a driver action for a switched driver to the queue (for either the A-side or C-side queue).

        Args:
            driver: A reference to the original platform class Driver instance.
            pulse_settings: Settings for the pulse or None
            hold_settings:Settings for hold or None

        This action will be serviced immediately if it can, or ASAP otherwise.
        """
        if driver in self.a_drivers:
            self.a_side_queue.add((driver, pulse_settings, hold_settings))
            self._service_a_side()
        elif driver in self.c_drivers:
            self.c_side_queue.add((driver, pulse_settings, hold_settings))
            if not self.ac_relay_in_transition and not self.a_side_busy:
                self._service_c_side()

    def _enable_ac_relay(self):
        self.system11_config['ac_relay_driver'].enable()
        self.ac_relay_in_transition = True
        self.a_side_enabled = False
        self.c_side_enabled = False
        self.delay.add(ms=self.system11_config['ac_relay_delay_ms'],
                       callback=self._c_side_enabled,
                       name='enable_ac_relay')

    def _disable_ac_relay(self):
        self.system11_config['ac_relay_driver'].disable()
        self.ac_relay_in_transition = True
        self.a_side_enabled = False
        self.c_side_enabled = False
        self.delay.add(ms=self.system11_config['ac_relay_delay_ms'],
                       callback=self._a_side_enabled,
                       name='disable_ac_relay')

    # -------------------------------- A SIDE ---------------------------------

    def _enable_a_side(self):
        if not self.a_side_enabled and not self.ac_relay_in_transition:

            if self.c_side_active:
                self._disable_all_c_side_drivers()
                self._disable_ac_relay()
                self.delay.add(ms=self.system11_config['ac_relay_delay_ms'],
                               callback=self._enable_a_side,
                               name='enable_a_side')
                return

            elif self.c_side_enabled:
                self._disable_ac_relay()

            else:
                self._a_side_enabled()

    def _a_side_enabled(self):
        self.ac_relay_in_transition = False
        self.a_side_enabled = True
        self.c_side_enabled = False
        self._service_a_side()

    def _service_a_side(self):
        if not self.a_side_queue:
            return

        elif not self.a_side_enabled:
            self._enable_a_side()
            return

        while self.a_side_queue:
            driver, pulse_settings, hold_settings = self.a_side_queue.pop()

            if hold_settings is None and pulse_settings:
                driver.pulse(pulse_settings)
                self.a_side_done_time = max(self.a_side_done_time,
                                            self.machine.clock.get_time() + (pulse_settings.duration / 1000.0))

            elif hold_settings and pulse_settings:
                driver.enable(pulse_settings, hold_settings)
                self.drivers_holding_a_side.add(driver)

            else:  # ms == 0
                driver.disable()
                try:
                    self.drivers_holding_a_side.remove(driver)
                except KeyError:
                    pass

    def _add_a_driver(self, driver):
        self.a_drivers.add(driver)

    # -------------------------------- C SIDE ---------------------------------

    def _enable_c_side(self):
        if (not self.ac_relay_in_transition and
                not self.c_side_enabled and
                not self.a_side_busy):
            self._enable_ac_relay()

        elif self.c_side_enabled and self.c_side_queue:
            self._service_c_side()

    def _c_side_enabled(self):
        self.ac_relay_in_transition = False

        if self.a_side_queue:
            self._enable_a_side()
            return

        self.a_side_enabled = False
        self.c_side_enabled = True
        self._service_c_side()

    def _service_c_side(self):
        if not self.c_side_queue:
            return

        if self.ac_relay_in_transition or self.a_side_busy:
            return

        elif not self.c_side_enabled:
            self._enable_c_side()
            return

        while self.c_side_queue:
            driver, pulse_settings, hold_settings = self.c_side_queue.pop()

            if hold_settings is None and pulse_settings:
                driver.pulse(pulse_settings)
                self.c_side_done_time = max(self.c_side_done_time,
                                            self.machine.clock.get_time() + (pulse_settings.duration / 1000.0))
            elif hold_settings and pulse_settings:
                driver.enable(pulse_settings, hold_settings)
                self.drivers_holding_c_side.add(driver)

            else:
                driver.disable()
                try:
                    self.drivers_holding_c_side.remove(driver)
                except KeyError:
                    pass

    def _add_c_driver(self, driver):
        self.c_drivers.add(driver)

    def _disable_all_c_side_drivers(self):
        if self.c_side_active:
            for driver in self.drivers_holding_c_side:
                driver.disable()
            self.drivers_holding_c_side = set()
            self.c_side_done_time = 0
            self.c_side_enabled = False

    def validate_coil_section(self, driver, config):
        """Validate coil config for platform."""
        return self.platform.validate_coil_section(driver, config)


class SnuxDriver(DriverPlatformInterface):

    """Represent one driver on the snux board.

    Two of those drivers may be created for one real driver. One for the A and one for the C side.
    """

    def __init__(self, number, platform_driver: DriverPlatformInterface, overlay) -> None:
        """Initialize driver."""
        super().__init__(platform_driver.config, number)
        self.number = number
        self.platform_driver = platform_driver
        self.overlay = overlay

    def __repr__(self):
        """Pretty print."""
        return "SnuxDriver.{}".format(self.number)

    def get_board_name(self):
        """Return name of driver board."""
        return self.platform_driver.get_board_name()

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse driver."""
        self.overlay.driver_action(self.platform_driver, pulse_settings, None)

        # Usually pulse() returns the value (in ms) that the driver will pulse
        # for so we can update Driver.time_when_done. But with A/C switched
        # coils, we don't know when exactly that will be, so we return -1
        return -1

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable driver."""
        self.overlay.driver_action(self.platform_driver, pulse_settings, hold_settings)

    def disable(self):
        """Disable driver."""
        self.overlay.driver_action(self.platform_driver, None, None)
