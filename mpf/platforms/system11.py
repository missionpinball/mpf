"""A generic system11 driver overlay.

This is based on the Snux platform to generically support all kinds of System11 platforms.
"""
from typing import Any, Optional, Set, Tuple, Dict

from mpf.core.machine import MachineController
from mpf.core.platform import DriverPlatform, DriverConfig, SwitchSettings, DriverSettings, RepulseSettings, \
    SwitchPlatform, SwitchConfig

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings

from mpf.core.delays import DelayManager

MYPY = False
if MYPY:   # pragma: no cover
    class SwitchDriverPlatform(DriverPlatform, SwitchPlatform):     # noqa
        pass


# pylint: disable-msg=too-many-instance-attributes
class System11OverlayPlatform(DriverPlatform, SwitchPlatform):

    """Overlay platform to drive system11 machines using a WPC controller."""

    __slots__ = ["delay", "platform", "system11_config", "a_side_queue", "c_side_queue",
                 "a_side_done_time", "c_side_done_time", "drivers_holding_a_side", "drivers_holding_c_side",
                 "a_side_enabled", "c_side_enabled", "ac_relay_in_transition", "prefer_a_side", "drivers"]

    def __init__(self, machine: MachineController) -> None:
        """Initialise the board."""
        super().__init__(machine)

        self.delay = DelayManager(machine)

        self.platform = None            # type: Optional[SwitchDriverPlatform]

        self.system11_config = None     # type: Any

        self.a_side_queue = \
            set()   # type: Set[Tuple[DriverPlatformInterface, Optional[PulseSettings], Optional[HoldSettings]]]
        self.c_side_queue = \
            set()   # type: Set[Tuple[DriverPlatformInterface, Optional[PulseSettings], Optional[HoldSettings]]]

        self.a_side_done_time = 0
        self.c_side_done_time = 0
        self.drivers_holding_a_side = set()     # type: Set[DriverPlatformInterface]
        self.drivers_holding_c_side = set()     # type: Set[DriverPlatformInterface]
        self.a_side_enabled = True
        self.c_side_enabled = False
        self.drivers = {}               # type: Dict[str, DriverPlatformInterface]

        self.ac_relay_in_transition = False
        # Specify whether the AC relay should favour the A or C side when at rest.
        # Typically during a game the 'C' side should be preferred, since that is
        # normally where the flashers are which need a quick response without having to wait on the relay.
        # At game over though, it should prefer the 'A' side so that the relay isn't permanently energised.
        self.prefer_a_side = True

    def stop(self):
        """Stop the overlay. Nothing to do here because stop is also called on parent platform."""

    @property
    def a_side_busy(self):
        """Return if A side cannot be switches off right away."""
        return self.drivers_holding_a_side or self.a_side_done_time > self.machine.clock.get_time() or self.a_side_queue

    @property
    def c_side_active(self):
        """Return if C side cannot be switches off right away."""
        return self.drivers_holding_c_side or self.c_side_done_time > self.machine.clock.get_time()

    @property
    def c_side_busy(self):
        """Return if C side cannot be switches off right away."""
        return self.drivers_holding_c_side or self.c_side_done_time > self.machine.clock.get_time() or self.c_side_queue

    @property
    def a_side_active(self):
        """Return if A side cannot be switches off right away."""
        return self.drivers_holding_a_side or self.a_side_done_time > self.machine.clock.get_time()

    def _null_log_handler(self, *args, **kwargs):
        pass

    async def initialize(self):
        """Automatically called by the Platform class after all the core modules are loaded."""
        # load coil platform
        self.platform = self.machine.get_platform_sections(
            "platform", getattr(self.machine.config.get('system11', {}), 'platform', None))

        # we have to wait for coils to be initialized
        self.machine.events.add_handler("init_phase_1", self._initialize)

    def _initialize(self, **kwargs):
        del kwargs
        self._validate_config()

        self.configure_logging('Platform.System11', self.system11_config['console_log'],
                               self.system11_config['file_log'])

        self.log.debug("Configuring A/C Select Relay for driver %s",
                       self.system11_config['ac_relay_driver'].name)

        self.system11_config['ac_relay_driver'].get_and_verify_hold_power(1.0)

        self.log.debug("Configuring A/C Select Relay transition delay for "
                       "%sms", self.system11_config['ac_relay_delay_ms'])

        self.machine.events.add_handler(self.system11_config['prefer_a_side_event'], self._prefer_a_side)
        self.log.info("Configuring System11 driver to prefer A side on event %s",
                      self.system11_config['prefer_a_side_event'])

        self.machine.events.add_handler(self.system11_config['prefer_c_side_event'], self._prefer_c_side)
        self.log.info("Configuring System11 driver to prefer C side on event %s",
                      self.system11_config['prefer_c_side_event'])

    def _prefer_a_side(self, **kwargs):
        del kwargs
        self.prefer_a_side = True
        self._enable_a_side()

    def _prefer_c_side(self, **kwargs):
        del kwargs
        self.prefer_a_side = False
        self._enable_c_side()

    def _validate_config(self):
        self.system11_config = self.machine.config_validator.validate_config(
            'system11', self.machine.config.get('system11', {}))

    def tick(self):
        """System11 main loop.

        Called based on the timer_tick event.
        """
        if self.prefer_a_side:
            if self.a_side_queue:
                self._service_a_side()
            elif self.c_side_queue:
                self._service_c_side()
            elif self.c_side_enabled and not self.c_side_active:
                self._enable_a_side()
        else:
            if self.c_side_queue:
                self._service_c_side()
            elif self.a_side_queue:
                self._service_a_side()
            elif self.a_side_enabled and not self.a_side_active:
                self._enable_c_side()

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict):
        """Configure switch on system11 overlay."""
        return self.platform.configure_switch(number, config, platform_config)

    async def get_hw_switch_states(self):
        """Get initial hardware state."""
        return await self.platform.get_hw_switch_states()

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
        """Configure a driver on the system11 overlay.

        Args:
        ----
            config: Driver config dict
            number: Number of the driver.
            platform_settings: Platform specific config.
        """
        assert self.platform is not None
        orig_number = number

        if number and (number.lower().endswith('a') or number.lower().endswith('c')):

            side = number[-1:].upper()
            number = number[:-1]

            # only configure driver once
            if number not in self.drivers:
                self.drivers[number] = self.platform.configure_driver(config, number, platform_settings)

            system11_driver = System11Driver(orig_number, self.drivers[number], self, side)

            return system11_driver

        return self.platform.configure_driver(config, number, platform_settings)

    @staticmethod
    def _check_if_driver_is_capable_for_rule(driver: DriverPlatformInterface):
        """Check if driver is capable for rule and bail out with an exception if not."""
        number = driver.number
        if number and (number.lower().endswith('a') or number.lower().endswith('c')):
            raise AssertionError("Received a request to set a hardware rule for a System11 driver {}. "
                                 "This is not supported.".format(driver))

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Configure a rule for a driver on the system11 overlay.

        Will pass the call onto the parent platform if the driver is not on A/C relay.
        """
        self._check_if_driver_is_capable_for_rule(coil.hw_driver)

        self.platform.set_pulse_on_hit_and_release_rule(enable_switch, coil)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        """Configure a rule for a driver on the system11 overlay.

        Will pass the call onto the parent platform if the driver is not on A/C relay.
        """
        self._check_if_driver_is_capable_for_rule(coil.hw_driver)

        self.platform.set_pulse_on_hit_and_enable_and_release_rule(enable_switch, coil)

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings, eos_switch: SwitchSettings,
                                                      coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Configure a rule for a driver on the system11 overlay.

        Will pass the call onto the parent platform if the driver is not on A/C relay.
        """
        self._check_if_driver_is_capable_for_rule(coil.hw_driver)

        self.platform.set_pulse_on_hit_and_release_and_disable_rule(enable_switch, eos_switch, coil, repulse_settings)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings,
                                                                 coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Configure a rule for a driver on the system11 overlay.

        Will pass the call onto the parent platform if the driver is not on A/C relay.
        """
        self._check_if_driver_is_capable_for_rule(coil.hw_driver)

        self.platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule(enable_switch, eos_switch, coil,
                                                                               repulse_settings)

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        """Configure a rule on the system11 overlay.

        Will pass the call onto the parent platform if the driver is not on A/C relay.
        """
        self._check_if_driver_is_capable_for_rule(coil.hw_driver)

        self.platform.set_pulse_on_hit_rule(enable_switch, coil)

    def clear_hw_rule(self, switch, coil):
        """Clear a rule for a driver on the system11 overlay."""
        self._check_if_driver_is_capable_for_rule(coil.hw_driver)

        self.platform.clear_hw_rule(switch, coil)

    def driver_action(self, driver, pulse_settings: Optional[PulseSettings], hold_settings: Optional[HoldSettings],
                      side: str):
        """Add a driver action for a switched driver to the queue (for either the A-side or C-side queue).

        Args:
        ----
            driver: A reference to the original platform class Driver instance.
            pulse_settings: Settings for the pulse or None
            hold_settings:Settings for hold or None
            side: Whatever the driver is on A or C side.

        This action will be serviced immediately if it can, or ASAP otherwise.
        """
        if self.prefer_a_side:
            if side == "A":
                self.a_side_queue.add((driver, pulse_settings, hold_settings))
                self._service_a_side()
            elif side == "C":
                self.c_side_queue.add((driver, pulse_settings, hold_settings))
                if not self.ac_relay_in_transition and not self.a_side_busy:
                    self._service_c_side()
            else:
                raise AssertionError("Invalid side {}".format(side))
        else:
            if side == "C":
                self.c_side_queue.add((driver, pulse_settings, hold_settings))
                self._service_c_side()
            elif side == "A":
                self.a_side_queue.add((driver, pulse_settings, hold_settings))
                if not self.ac_relay_in_transition and not self.c_side_busy:
                    self._service_a_side()
            else:
                raise AssertionError("Invalid side {}".format(side))

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
        if self.prefer_a_side:
            if not self.a_side_enabled and not self.ac_relay_in_transition:

                if self.c_side_active:
                    self._disable_all_c_side_drivers()
                    self._disable_ac_relay()
                    self.delay.add(ms=self.system11_config['ac_relay_delay_ms'],
                                   callback=self._enable_a_side,
                                   name='enable_a_side')
                    return

                if self.c_side_enabled:
                    self._disable_ac_relay()

                else:
                    self._a_side_enabled()
        else:
            if (not self.ac_relay_in_transition and
                    not self.a_side_enabled and
                    not self.c_side_busy):
                self._disable_ac_relay()

            elif self.a_side_enabled and self.a_side_queue:
                self._service_a_side()

    def _a_side_enabled(self):
        self.ac_relay_in_transition = False
        if self.prefer_a_side:
            self.a_side_enabled = True
            self.c_side_enabled = False
            self._service_a_side()
        else:

            if self.c_side_queue:
                self._enable_c_side()
                return

            self.c_side_enabled = False
            self.a_side_enabled = True
            self._service_a_side()

    def _service_a_side(self):
        if not self.a_side_queue:
            return

        if not self.a_side_enabled:
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

    # -------------------------------- C SIDE ---------------------------------

    def _enable_c_side(self):
        if self.prefer_a_side:
            if not self.c_side_enabled and not self.ac_relay_in_transition:

                if self.a_side_active:
                    self._disable_all_a_side_drivers()
                    self._enable_ac_relay()
                    self.delay.add(ms=self.system11_config['ac_relay_delay_ms'],
                                   callback=self._enable_c_side,
                                   name='enable_c_side')
                    return

                if self.a_side_enabled:
                    self._enable_ac_relay()

                else:
                    self._c_side_enabled()
        else:
            if (not self.ac_relay_in_transition and
                    not self.c_side_enabled and
                    not self.a_side_busy):
                self._enable_ac_relay()

            elif self.c_side_enabled and self.c_side_queue:
                self._service_c_side()

    def _c_side_enabled(self):
        self.ac_relay_in_transition = False

        if self.prefer_a_side:
            self.c_side_enabled = True
            self.a_side_enabled = False
            self._service_c_side()
        else:

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

        if not self.c_side_enabled:
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

    def _disable_all_c_side_drivers(self):
        if self.c_side_active:
            for driver in self.drivers_holding_c_side:
                driver.disable()
            self.drivers_holding_c_side = set()
            self.c_side_done_time = 0
            self.c_side_enabled = False

    def _disable_all_a_side_drivers(self):
        if self.a_side_active:
            for driver in self.drivers_holding_a_side:
                driver.disable()
            self.drivers_holding_a_side = set()
            self.a_side_done_time = 0
            self.a_side_enabled = False

    def validate_coil_section(self, driver, config):
        """Validate coil config for platform."""
        return self.platform.validate_coil_section(driver, config)


class System11Driver(DriverPlatformInterface):

    """Represent one driver on the system11 overlay.

    Two of those drivers may be created for one real driver. One for the A and one for the C side.
    """

    def __init__(self, number, platform_driver: DriverPlatformInterface, overlay, side) -> None:
        """Initialize driver."""
        super().__init__(platform_driver.config, number)
        self.number = number
        self.platform_driver = platform_driver
        self.overlay = overlay
        self.side = side

    def __repr__(self):
        """Pretty print."""
        return "System11Driver.{}".format(self.number)

    def get_board_name(self):
        """Return name of driver board."""
        return self.platform_driver.get_board_name()

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse driver."""
        self.overlay.driver_action(self.platform_driver, pulse_settings, None, self.side)

        # Usually pulse() returns the value (in ms) that the driver will pulse
        # for so we can update Driver.time_when_done. But with A/C switched
        # coils, we don't know when exactly that will be, so we return -1
        return -1

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable driver."""
        self.overlay.driver_action(self.platform_driver, pulse_settings, hold_settings, self.side)

    def disable(self):
        """Disable driver."""
        self.overlay.driver_action(self.platform_driver, None, None, self.side)
