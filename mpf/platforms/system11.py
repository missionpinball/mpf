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

    __slots__ = ["delay", "platform", "system11_config", "a_side_queue", "c_side_queue", "debounce_secs",
                 "a_side_done_time", "c_side_done_time", "drivers_holding_a_side", "drivers_holding_c_side",
                 "_a_side_enabled", "_c_side_enabled", "ac_relay_in_transition", "prefer_a_side", "drivers",
                 "relay_switch"]

    def __init__(self, machine: MachineController) -> None:
        """Initialize the board."""
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
        self.debounce_secs = 0
        self.drivers_holding_a_side = set()     # type: Set[DriverPlatformInterface]
        self.drivers_holding_c_side = set()     # type: Set[DriverPlatformInterface]
        # Internal tracker for which side is enabled, for platforms that don't have switches
        self._a_side_enabled = True
        self._c_side_enabled = False
        self.drivers = {}               # type: Dict[str, DriverPlatformInterface]

        self.ac_relay_in_transition = False
        self.relay_switch = None
        # Specify whether the AC relay should favour the A or C side when at rest.
        # Typically during a game the 'C' side should be preferred, since that is
        # normally where the flashers are which need a quick response without having to wait on the relay.
        # At game over though, it should prefer the 'A' side so that the relay isn't permanently energised.
        self.prefer_a_side = True

    def stop(self):
        """Stop the overlay. Nothing to do here because stop is also called on parent platform."""

    @property
    def a_side_active(self):
        """Return if A side cannot be switched off right away."""
        return self.drivers_holding_a_side or self.a_side_done_time + self.debounce_secs > self.machine.clock.get_time()

    @property
    def a_side_busy(self):
        """Return if A side cannot be switched off right away."""
        return self.a_side_active or self.a_side_queue

    @property
    def a_side_enabled(self):
        """Return true if the A side is currently enabled."""
        if self.ac_relay_in_transition:
            return False
        if self.relay_switch:
            return not self.relay_switch.state
        return self._a_side_enabled

    @property
    def c_side_active(self):
        """Return if C side cannot be switched off right away."""
        return self.drivers_holding_c_side or self.c_side_done_time + self.debounce_secs > self.machine.clock.get_time()

    @property
    def c_side_busy(self):
        """Return if C side cannot be switched off right away."""
        return self.c_side_active or self.c_side_queue

    @property
    def c_side_enabled(self):
        """Return true if the C side is currently enabled."""
        if self.relay_switch:
            # Never enabled if the relay is in transition
            return not self.ac_relay_in_transition and self.relay_switch.state
        return self._c_side_enabled

    async def initialize(self):
        """Automatically called by the Platform class after all the core modules are loaded."""
        # Some platforms (like Fast Retro) may be system11, or may not be.
        # If no system11 config is present, do not initialize the System11 platform
        system11_config = self.machine.config.get('system11')
        if not system11_config:
            return

        # load coil platform
        self.platform = self.machine.get_platform_sections(
            "platform", getattr(system11_config, 'platform', None))

        # we have to wait for coils to be initialized
        self.machine.events.add_handler("init_phase_1", self._initialize)

    def _initialize(self, **kwargs):
        del kwargs
        self._validate_config()

        self.configure_logging('Platform.System11', self.system11_config['console_log'],
                               self.system11_config['file_log'])

        self.log.debug("Configuring A/C Select Relay for driver %s",
                       self.system11_config['ac_relay_driver'])

        self.system11_config['ac_relay_driver'].get_and_verify_hold_power(1.0)
        self.relay_switch = self.system11_config['ac_relay_switch']

        if self.relay_switch:
            self.log.debug("Configuring A/C Select Relay switch %s", self.relay_switch)
            self.relay_switch.add_handler(state=0, callback=self._on_a_side_enabled)
            self.relay_switch.add_handler(state=1, callback=self._on_c_side_enabled)

            # If the platform does not have a physical switch for the AC Relay, a virtual
            # switch may be implemented with a special driver configuration if that
            # driver class has a set_relay() method defined.
            if hasattr(self.system11_config['ac_relay_driver'].hw_driver, 'set_relay'):
                self.system11_config['ac_relay_driver'].hw_driver.set_relay(
                    self.relay_switch.hw_switch,
                    20,  # Ms to delay before reporting closed
                    20   # Ms to delay before reporting open
                )
        self.debounce_secs = self.system11_config['ac_relay_debounce_ms'] / 1000.0
        self.log.debug("Configuring A/C Select Relay transition delay for %sms and debounce for %s",
                       self.system11_config['ac_relay_delay_ms'],
                       self.system11_config['ac_relay_debounce_ms'])

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

    def validate_switch_section(self, switch, config: dict) -> dict:
        """Validate switch config for overlayed platform."""
        # Check for a platform to have a custom switch validation method, but avoid recursion
        # since the platform will (most likely) inherit from System11OverlayPlatform
        if self.platform is not None:
            return self.platform.validate_switch_section(switch, config)
        return SwitchPlatform.validate_switch_section(self, switch, config)

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
        number_str = str(number)

        if number_str and (number_str.lower().endswith('a') or number_str.lower().endswith('c')):

            side = number_str[-1:].upper()
            number_str = number_str[:-1]

            # only configure driver once
            if number_str not in self.drivers:
                self.drivers[number_str] = self.platform.configure_driver(config, number_str, platform_settings)

            system11_driver = System11Driver(number, self.drivers[number_str], self, side)

            return system11_driver

        return self.platform.configure_driver(config, number_str, platform_settings)

    @staticmethod
    def _check_if_driver_is_capable_for_rule(driver: DriverPlatformInterface):
        """Check if driver is capable for rule and bail out with an exception if not."""
        if isinstance(driver, System11Driver):
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

    # pylint: disable-msg=too-many-arguments
    def driver_action(self, driver, pulse_settings: Optional[PulseSettings], hold_settings: Optional[HoldSettings],
                      side: str, timed_enable: bool = False):
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
                self.a_side_queue.add((driver, pulse_settings, hold_settings, timed_enable))
                if not self.ac_relay_in_transition:
                    self._service_a_side()
            elif side == "C":
                self.c_side_queue.add((driver, pulse_settings, hold_settings, timed_enable))
                if not self.ac_relay_in_transition and not self.a_side_busy:
                    self._service_c_side()
            else:
                raise AssertionError("Invalid side {}".format(side))
        else:
            if side == "C":
                # Sometimes it doesn't make sense to queue the C side (flashers) and play them after
                # switching to the A side (coils) and back. If we are on A side or have a queue on
                # the A side, ignore this C side request.
                if (self.a_side_queue or not self.c_side_enabled) and \
                        not self.system11_config['queue_c_side_while_preferred']:
                    return
                self.c_side_queue.add((driver, pulse_settings, hold_settings, timed_enable))
                if not self.ac_relay_in_transition:
                    self._service_c_side()
            elif side == "A":
                self.a_side_queue.add((driver, pulse_settings, hold_settings, timed_enable))
                # Clear the C-side queue to prioritize A-side and get it switched over faster
                if not self.system11_config['queue_c_side_while_preferred']:
                    self.c_side_queue.clear()
                if not self.ac_relay_in_transition and not self.c_side_busy:
                    self._service_a_side()
            else:
                raise AssertionError("Invalid side {}".format(side))

    def _enable_ac_relay(self):
        self.system11_config['ac_relay_driver'].enable()
        self.ac_relay_in_transition = True
        self._a_side_enabled = False
        self._c_side_enabled = False
        # Without a relay switch, use a delay to wait for the relay to enable
        if not self.relay_switch:
            self.delay.add(ms=self.system11_config['ac_relay_delay_ms'],
                           callback=self._on_c_side_enabled,
                           name='enable_ac_relay')

    def _disable_ac_relay(self):
        self.system11_config['ac_relay_driver'].disable()
        self.ac_relay_in_transition = True
        self._a_side_enabled = False
        self._c_side_enabled = False
        # Clear out the C side queue if we don't want to hold onto it for later
        if not self.system11_config['queue_c_side_while_preferred']:
            self.c_side_queue.clear()
        if not self.relay_switch:
            self.delay.add(ms=self.system11_config['ac_relay_delay_ms'],
                           callback=self._on_a_side_enabled,
                           name='disable_ac_relay')

    # -------------------------------- A SIDE ---------------------------------

    def _enable_a_side(self):
        if self.prefer_a_side:
            if not self.a_side_enabled and not self.ac_relay_in_transition:

                if self.c_side_active:
                    self._disable_all_c_side_drivers()
                    self._disable_ac_relay()
                    return

                if self.c_side_enabled:
                    self._disable_ac_relay()

                else:
                    self._on_a_side_enabled()
        else:
            if (not self.ac_relay_in_transition and
                    not self.a_side_enabled and
                    not self.c_side_busy):
                self._disable_ac_relay()

            elif self.a_side_enabled and self.a_side_queue:
                self._service_a_side()

    def _on_a_side_enabled(self):
        self.ac_relay_in_transition = False
        # If A side has no queue and is not preferred, return to C side
        if not self.a_side_queue and not self.prefer_a_side:
            self._enable_c_side()
            return

        self._c_side_enabled = False
        self._a_side_enabled = True
        self._service_a_side()

    def _service_a_side(self):
        if not self.a_side_queue:
            return

        if not self.a_side_enabled:
            self._enable_a_side()
            return

        while self.a_side_queue:
            driver, pulse_settings, hold_settings, timed_enable = self.a_side_queue.pop()

            if timed_enable:
                wait_ms = driver.timed_enable(pulse_settings, hold_settings) or 0
                wait_secs = (pulse_settings.duration + hold_settings.duration + wait_ms) / 1000.0
                self.a_side_done_time = max(self.a_side_done_time, self.machine.clock.get_time() + wait_secs)

            elif hold_settings is None and pulse_settings:
                wait_ms = driver.pulse(pulse_settings) or 0
                wait_secs = (pulse_settings.duration + wait_ms) / 1000.0
                self.a_side_done_time = max(self.a_side_done_time, self.machine.clock.get_time() + wait_secs)

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
                    return

                if self.a_side_enabled:
                    self._enable_ac_relay()

                else:
                    self._on_c_side_enabled()
        else:
            if (not self.ac_relay_in_transition and
                    not self.c_side_enabled and
                    not self.a_side_busy):
                self._enable_ac_relay()

            elif self.c_side_enabled and self.c_side_queue:
                self._service_c_side()

    def _on_c_side_enabled(self):
        self.ac_relay_in_transition = False
        # If C side is not preferred and has no queue, return to A side
        if not self.c_side_queue and self.prefer_a_side:
            self._enable_a_side()
            return

        self._a_side_enabled = False
        self._c_side_enabled = True
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
            driver, pulse_settings, hold_settings, timed_enable = self.c_side_queue.pop()

            if timed_enable:
                driver.timed_enable(pulse_settings, hold_settings)
                self.c_side_done_time = max(self.c_side_done_time,
                                            self.machine.clock.get_time() + (pulse_settings.duration / 1000.0))

            elif hold_settings is None and pulse_settings:
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

    def _disable_all_a_side_drivers(self):
        if self.a_side_active:
            for driver in self.drivers_holding_a_side:
                driver.disable()
            self.drivers_holding_a_side = set()
            self.a_side_done_time = 0

    def validate_coil_section(self, driver, config):
        """Validate coil config for platform."""
        # Check for a platform to have a custom coil validation method, but avoid recursion
        # since the platform will (most likely) inherit from System11OverlayPlatform
        if self.platform is not None:
            return self.platform.validate_coil_section(driver, config)
        return DriverPlatform.validate_coil_section(self, driver, config)


class System11Driver(DriverPlatformInterface):

    """Represent one driver on the system11 overlay.

    Two of those drivers may be created for one real driver. One for the A and one for the C side.
    """

    __slots__ = ["platform_driver", "overlay", "side"]

    def __init__(self, number, platform_driver: DriverPlatformInterface, overlay, side) -> None:
        """Initialize driver."""
        super().__init__(platform_driver.config, number)
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

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and enable the coil for an explicit duration."""
        self.overlay.driver_action(self.platform_driver, pulse_settings, hold_settings, self.side, True)
