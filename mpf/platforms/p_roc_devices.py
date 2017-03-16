"""P-Roc hardware platform devices."""
import logging

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface
from mpf.core.utility_functions import Util


class PROCSwitch(SwitchPlatformInterface):

    """P-ROC switch object which is use to store the configure rules and config."""

    def __init__(self, config, number, notify_on_nondebounce):
        """Initialise P-ROC switch."""
        super().__init__(config, number)
        self.log = logging.getLogger('PROCSwitch')
        self.notify_on_nondebounce = notify_on_nondebounce
        self.hw_rules = {"closed_debounced": [],
                         "closed_nondebounced": [],
                         "open_debounced": [],
                         "open_nondebounced": []}


class PROCDriver(DriverPlatformInterface):

    """A P-ROC driver/coil.

    Base class for drivers connected to a P3-ROC. This class is used for all
    drivers, regardless of whether they're connected to a P-ROC driver board
    (such as the PD-16 or PD-8x8) or an OEM driver board.

    """

    def __init__(self, number, config, platform):
        """Initialise driver."""
        self.log = logging.getLogger('PROCDriver')
        super().__init__(config, number)
        self.proc = platform.proc
        self.machine = platform.machine
        self.pdbconfig = getattr(platform, "pdbconfig", None)

        self.log.debug("Driver Settings for %s", self.number)

    def get_board_name(self):
        """Return board of the driver."""
        if not self.pdbconfig:
            return "P-Roc"
        else:
            return "P-Roc Board {}".format(str(self.pdbconfig.get_coil_bank(self.config['number'])))

    @classmethod
    def get_pwm_on_ms(cls, coil):
        """Find out the pwm_on_ms for this driver."""
        # figure out what kind of enable we need:
        if coil.config['hold_power']:
            pwm_on_ms, pwm_off_ms = (Util.pwm8_to_on_off(coil.config['hold_power']))
            del pwm_off_ms
            return pwm_on_ms

        elif coil.config['pwm_on_ms'] and coil.config['pwm_off_ms']:
            return int(coil.config['pwm_on_ms'])
        else:
            return 0

    @classmethod
    def get_pwm_off_ms(cls, coil):
        """Find out the pwm_off_ms for this driver."""
        # figure out what kind of enable we need:
        if coil.config['hold_power']:
            pwm_on_ms, pwm_off_ms = (Util.pwm8_to_on_off(coil.config['hold_power']))
            del pwm_on_ms
            return pwm_off_ms

        elif coil.config['pwm_on_ms'] and coil.config['pwm_off_ms']:
            return int(coil.config['pwm_off_ms'])
        else:
            return 0

    def get_pulse_ms(self, coil):
        """Find out the pulse_ms for this driver."""
        if coil.config['pulse_ms'] is not None:
            return int(coil.config['pulse_ms'])
        else:
            return self.machine.config['mpf']['default_pulse_ms']

    def disable(self, coil):
        """Disable (turn off) this driver."""
        del coil
        self.log.debug('Disabling Driver')
        self.proc.driver_disable(self.number)

    def enable(self, coil):
        """Enable (turn on) this driver."""
        if self.get_pwm_on_ms(coil) and self.get_pwm_off_ms(coil):
            self.log.debug('Enabling. Initial pulse_ms:%s, pwm_on_ms: %s'
                           'pwm_off_ms: %s',
                           self.get_pwm_on_ms(coil),
                           self.get_pwm_off_ms(coil),
                           self.get_pulse_ms(coil))

            self.proc.driver_patter(self.number,
                                    self.get_pwm_on_ms(coil),
                                    self.get_pwm_off_ms(coil),
                                    self.get_pulse_ms(coil), True)
        else:
            self.log.debug('Enabling at 100%')

            if not coil.config['allow_enable']:
                raise AssertionError("Received a command to enable this coil "
                                     "without pwm, but 'allow_enable' has not been"
                                     "set to True in this coil's configuration.")

            self.proc.driver_schedule(number=self.number, schedule=0xffffffff,
                                      cycle_seconds=0, now=True)

    def pulse(self, coil, milliseconds):
        """Enable this driver for `milliseconds`.

        ``ValueError`` will be raised if `milliseconds` is outside of the range
        0-255.
        """
        del coil

        self.log.debug('Pulsing for %sms', milliseconds)
        self.proc.driver_pulse(self.number, milliseconds)

        return milliseconds

    def state(self):
        """Return a dictionary representing this driver's current configuration state."""
        return self.proc.driver_get_state(self.number)


class PROCMatrixLight(LightPlatformSoftwareFade):

    """A P-ROC matrix light device."""

    def __init__(self, number, proc_driver, machine):
        """Initialise matrix light device."""
        super().__init__(machine.clock.loop, int(1 / machine.config['mpf']['default_light_hw_update_hz'] * 1000))
        self.log = logging.getLogger('PROCMatrixLight')
        self.number = number
        self.proc = proc_driver

    def set_brightness(self, brightness: float):
        """Enable (turns on) this driver."""
        if brightness > 0:
            pwm_on_ms, pwm_off_ms = (Util.pwm8_to_on_off(int(brightness * 8)))
            self.proc.driver_patter(self.number, pwm_on_ms, pwm_off_ms, 0, True)
        else:
            self.proc.driver_disable(self.number)
