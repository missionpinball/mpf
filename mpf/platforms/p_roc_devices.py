"""P-Roc hardware platform devices."""
import logging

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface
from mpf.platforms.interfaces.gi_platform_interface import GIPlatformInterface
from mpf.platforms.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface
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
        if coil.config['pulse_ms']:
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


class PROCGiString(GIPlatformInterface):

    """A P-ROc GI hardware device."""

    def __init__(self, number, proc_driver, config):
        """Initialise GI."""
        self.log = logging.getLogger('PROCGiString')
        self.number = number
        self.proc = proc_driver
        self.config = config

    def on(self, brightness=255):
        """Turn on GI to `brightness`.

        A brightness of 0 will turn it off. For values between 0 and 255 hardware pulse patter is used.
        """
        if brightness > 255:
            brightness = 255

        # run the GIs at 50Hz
        duty_on = int(brightness / 12.75)
        duty_off = 20 - duty_on
        self.proc.driver_patter(self.number,
                                int(duty_on),
                                int(duty_off),
                                0, True)

    def off(self):
        """Turn off a GI."""
        self.proc.driver_disable(self.number)


class PROCMatrixLight(MatrixLightPlatformInterface):

    """A P-ROC matrix light device."""

    def __init__(self, number, proc_driver):
        """Initialise matrix light device."""
        self.log = logging.getLogger('PROCMatrixLight')
        self.number = number
        self.proc = proc_driver

    def off(self):
        """Disable (turns off) this driver."""
        self.proc.driver_disable(self.number)

    def on(self, brightness=255):
        """Enable (turns on) this driver."""
        if brightness >= 255:
            self.proc.driver_schedule(number=self.number, schedule=0xffffffff,
                                      cycle_seconds=0, now=True)
        elif brightness == 0:
            self.off()
        else:
            pass
            # patter rates of 10/1 through 2/9

        """
        Koen's fade code he posted to pinballcontrollers:
        def mode_tick(self):
            if self.fade_counter % 10 == 0:
                for lamp in self.game.lamps:
                    if lamp.name.find("gi0") == -1:
                        var = 4.0*math.sin(0.02*float(self.fade_counter)) + 5.0
                        on_time = 11-round(var)
                        off_time = round(var)
                        lamp.patter(on_time, off_time)
                self.fade_counter += 1
        """     # pylint: disable=W0105
