"""Contains the base class for the Snux driver overlay.

This class overlays an existing WPC-compatible platform interface to work with
Mark Sunnucks's System 11 interface board.
"""

import logging
from mpf.core.delays import DelayManager


class Snux(object):

    def __init__(self, machine, platform):
        self.log = logging.getLogger('Platform.Snux')
        self.delay = DelayManager(machine.delayRegistry)

        self.machine = machine
        self.platform = platform

        self.system11_config = None
        self.snux_config = None
        self.ac_relay_delay_ms = 100
        self.special_drivers = set()

        self.diag_led = None
        '''Diagnostics LED (LED 3) on the Snux board turns on solid when MPF
        first connects, then starts flashing once the MPF init is done.'''
        self.ac_relay = None
        self.flipper_relay = None
        self.ac_relay_enabled = False  # disabled = A, enabled = C

        self.a_side_queue = set()
        self.c_side_queue = set()

        self.a_drivers = set()
        self.c_drivers = set()

        self.a_side_done_time = 0
        self.c_side_done_time = 0
        self.drivers_holding_a_side = set()
        self.drivers_holding_c_side = set()
        # self.a_side_busy = False  # This is a property
        # self.c_side_active = False  # This is a property
        self.a_side_enabled = True
        self.c_side_enabled = False

        self.ac_relay_in_transition = False

        self._morph()

    @property
    def a_side_busy(self):
        return self.drivers_holding_a_side or self.a_side_done_time > self.machine.clock.get_time() or self.a_side_queue

    @property
    def c_side_active(self):
        return self.drivers_holding_c_side or self.c_side_done_time > self.machine.clock.get_time()

    def null_log_handler(self, *args, **kwargs):
        pass

    def _morph(self):
        self.platform_configure_driver = self.platform.configure_driver
        self.platform.configure_driver = self.configure_driver

        self.platform_set_pulse_on_hit_and_release_rule = self.platform.set_pulse_on_hit_and_release_rule
        self.platform.set_pulse_on_hit_and_release_rule = self.set_pulse_on_hit_and_release_rule

        self.platform_set_pulse_on_hit_rule = self.platform.set_pulse_on_hit_rule
        self.platform.set_pulse_on_hit_rule = self.set_pulse_on_hit_rule

        self.platform_set_pulse_on_hit_and_enable_and_release_rule = \
            self.platform.set_pulse_on_hit_and_enable_and_release_rule
        self.platform.set_pulse_on_hit_and_enable_and_release_rule = self.set_pulse_on_hit_and_enable_and_release_rule

    def initialize(self):
        """Automatically called by the Platform class after all the core
        modules are loaded.

        """
        self._validate_config()

        self.log.debug("Configuring Snux Diag LED for driver %s",
                       self.snux_config['diag_led_driver_number'])

        self.diag_led, _ = self.platform_configure_driver(
            {'number': self.snux_config['diag_led_driver_number'],
             'allow_enable': True})

        self.diag_led.log.info = self.null_log_handler
        self.diag_led.log.debug = self.null_log_handler

        self.diag_led.enable()

        self.special_drivers.add(
            self.snux_config['diag_led_driver_number'].lower())

        self.log.debug("Configuring A/C Select Relay for driver %s",
                       self.system11_config['ac_relay_driver_number'])

        self.ac_relay, _ = self.platform_configure_driver(
            {'number': self.system11_config['ac_relay_driver_number'],
             'allow_enable': True})

        self.special_drivers.add(
            self.system11_config['ac_relay_driver_number'].lower())

        self.log.debug("Configuring A/C Select Relay transition delay for "
                       "%sms", self.system11_config['ac_relay_delay_ms'])

        self.ac_relay_delay_ms = self.system11_config['ac_relay_delay_ms']

        self.flipper_relay, _ = self.platform_configure_driver(
            {'number': self.snux_config['flipper_enable_driver_number'],
             'allow_enable': True})

        self.log.debug("Configuring Flipper Enable for driver %s",
                       self.snux_config['flipper_enable_driver_number'])

        self.machine.events.add_handler('init_phase_5',
                                        self._initialize_phase_2)

    def _initialize_phase_2(self):
        self.machine.clock.schedule_interval(self.flash_diag_led, 0.5)

        # Schedule processing callback
        # TODO: Make callback interval a config item
        self.machine.clock.schedule_interval(self._tick, 0)

    def _validate_config(self):
        self.system11_config = self.machine.config_validator.validate_config(
            'system11', self.machine.config['system11'])

        snux = self.machine.config.get('snux', dict())
        self.snux_config = self.machine.config_validator.validate_config(
            'snux', snux)

    def _tick(self, dt):
        # Called based on the timer_tick event
        del dt
        if self.a_side_queue:
            self._service_a_side()
        elif self.c_side_queue:
            self._service_c_side()
        elif self.c_side_enabled and not self.c_side_active:
            self._enable_a_side()

    def flash_diag_led(self, dt):
        del dt
        self.diag_led.pulse(250)

    def configure_driver(self, config):
        # If the user has configured one of the special drivers in their
        # machine config, don't set it up since that could let them do weird
        # things.
        if config['number'].lower() in self.special_drivers:
            return

        orig_number = config['number']

        if (config['number'].lower().endswith('a') or
                config['number'].lower().endswith('c')):

            config['number'] = config['number'][:-1]

            platform_driver, _ = (
                self.platform_configure_driver(config))

            snux_driver = SnuxDriver(orig_number, platform_driver, self)

            if orig_number.lower().endswith('a'):
                self._add_a_driver(snux_driver.platform_driver)
            elif orig_number.lower().endswith('c'):
                self._add_c_driver(snux_driver.platform_driver)

            return snux_driver, orig_number

        else:
            return self.platform_configure_driver(config)

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        if coil in self.a_drivers or coil in self.c_drivers:
            self.log.warning("Received a request to set a hardware rule for a"
                             "switched driver. Ignoring")
        else:
            self.platform_set_pulse_on_hit_and_release_rule(enable_switch, coil)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        if coil in self.a_drivers or coil in self.c_drivers:
            self.log.warning("Received a request to set a hardware rule for a"
                             "switched driver. Ignoring")
        else:
            self.platform_set_pulse_on_hit_and_enable_and_release_rule(enable_switch, coil)

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        if coil in self.a_drivers or coil in self.c_drivers:
            self.log.warning("Received a request to set a hardware rule for a"
                             "switched driver. Ignoring")
        else:
            self.platform_set_pulse_on_hit_rule(enable_switch, coil)

    def driver_action(self, driver, milliseconds):
        """Adds a driver action for a switched driver to the queue (for either
        the A-side or C-side queue).

        Args:
            driver: A reference to the original platform class Driver instance.
            milliseconds: Integer of the number of milliseconds this action is
                for. 0 = pulse, -1 = enable (hold), any other value is a timed
                action (either pulse or long_pulse)

        This action will be serviced immediately if it can, or ASAP otherwise.

        """
        if driver in self.a_drivers:
            self.a_side_queue.add((driver, milliseconds))
            self._service_a_side()
        elif driver in self.c_drivers:
            self.c_side_queue.add((driver, milliseconds))
            if not self.ac_relay_in_transition and not self.a_side_busy:
                self._service_c_side()

    def _enable_ac_relay(self):
        self.ac_relay.enable()
        self.ac_relay_in_transition = True
        self.a_side_enabled = False
        self.c_side_enabled = False
        self.delay.add(ms=self.ac_relay_delay_ms,
                       callback=self._c_side_enabled,
                       name='enable_ac_relay')

    def _disable_ac_relay(self):
        self.ac_relay.disable()
        self.ac_relay_in_transition = True
        self.a_side_enabled = False
        self.c_side_enabled = False
        self.delay.add(ms=self.ac_relay_delay_ms,
                       callback=self._a_side_enabled,
                       name='disable_ac_relay')

    # -------------------------------- A SIDE ---------------------------------

    def _enable_a_side(self):
        if not self.a_side_enabled and not self.ac_relay_in_transition:

            if self.c_side_active:
                self._disable_all_c_side_drivers()
                self.delay.add(ms=self.ac_relay_delay_ms,
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
            driver, ms = self.a_side_queue.pop()

            if ms > 0:
                driver.pulse(ms)
                self.a_side_done_time = max(self.a_side_done_time,
                                            self.machine.clock.get_time() + (ms / 1000.0))

            elif ms == -1:
                driver.enable()
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
            driver, ms = self.c_side_queue.pop()

            if ms > 0:
                driver.pulse(ms)
                self.c_side_done_time = max(self.c_side_done_time,
                                            self.machine.clock.get_time() + (ms / 1000.))
            elif ms == -1:
                driver.enable()
                self.drivers_holding_c_side.add(driver)

            else:  # ms == 0
                driver.disable()
                try:
                    self.drivers_holding_c_side.remove(driver)
                except KeyError:
                    pass

    def _add_c_driver(self, driver):
        self.c_drivers.add(driver)

    def _disable_all_c_side_drivers(self):
        if self.c_side_active:
            for driver in self.c_drivers:
                driver.disable()
            self.drivers_holding_c_side = set()
            self.c_side_done_time = 0
            self.c_side_enabled = False


class SnuxDriver(object):

    def __init__(self, number, platform_driver, overlay):
        self.number = number
        self.platform_driver = platform_driver
        self.driver_settings = platform_driver.driver_settings
        self.overlay = overlay

    def __repr__(self):
        return "SnuxDriver.{}".format(self.number)

    def pulse(self, coil, milliseconds, **kwargs):
        del kwargs
        del coil

        self.overlay.driver_action(self.platform_driver, milliseconds)

        # Usually pulse() returns the value (in ms) that the driver will pulse
        # for so we can update Driver.time_when_done. But with A/C switched
        # coils, we don't know when exactly that will be, so we return -1
        return -1

    def enable(self, **kwargs):
        del kwargs
        self.overlay.driver_action(self.platform_driver, -1)

    def disable(self, **kwargs):
        del kwargs
        self.overlay.driver_action(self.platform_driver, 0)


driver_overlay_class = Snux
