"""P-Roc hardware platform devices."""
import logging

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.core.utility_functions import Util


class PROCSwitch(SwitchPlatformInterface):

    """P-ROC switch object which is use to store the configure rules and config."""

    def __init__(self, config, number, notify_on_nondebounce, platform):
        """Initialise P-ROC switch."""
        super().__init__(config, number)
        self.string_number = number
        self.log = logging.getLogger('PROCSwitch')
        self.notify_on_nondebounce = notify_on_nondebounce
        self.hw_rules = {"closed_debounced": [],
                         "closed_nondebounced": [],
                         "open_debounced": [],
                         "open_nondebounced": []}
        self.pdbconfig = getattr(platform, "pdbconfig", None)

    def get_board_name(self):
        """Return board of the switch."""
        if not self.pdbconfig:
            return "P-Roc"

        board, bank, _ = self.pdbconfig.decode_pdb_address(self.string_number)

        return "SW-16 Board {} Bank {}".format(board, bank)


class PROCDriver(DriverPlatformInterface):

    """A P-ROC driver/coil.

    Base class for drivers connected to a P3-ROC. This class is used for all
    drivers, regardless of whether they're connected to a P-ROC driver board
    (such as the PD-16 or PD-8x8) or an OEM driver board.

    """

    def __init__(self, number, config, platform, string_number):
        """Initialise driver."""
        self.log = logging.getLogger('PROCDriver')
        super().__init__(config, number)
        self.proc = platform.proc
        self.string_number = string_number
        self.pdbconfig = getattr(platform, "pdbconfig", None)

        self.log.debug("Driver Settings for %s", self.number)

    def get_board_name(self):
        """Return board of the driver."""
        if not self.pdbconfig:
            return "P-Roc"

        board, bank, _ = self.pdbconfig.decode_pdb_address(self.string_number)

        return "PD-16 Board {} Bank {}".format(board, bank)

    @classmethod
    def get_pwm_on_off_ms(cls, coil: HoldSettings):
        """Find out the pwm_on_ms and pwm_off_ms for this driver."""
        return Util.power_to_on_off(coil.power)

    def disable(self):
        """Disable (turn off) this driver."""
        self.log.debug('Disabling Driver')
        self.proc.driver_disable(self.number)

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable (turn on) this driver."""
        if pulse_settings.power != 1:
            raise AssertionError("Not pulse_power not supported in P-Roc currently.")

        if hold_settings.power < 1.0:
            pwm_on, pwm_off = self.get_pwm_on_off_ms(hold_settings)
            self.log.debug('Enabling. Initial pulse_ms:%s, pwm_on_ms: %s'
                           'pwm_off_ms: %s', pwm_on, pwm_off, pulse_settings.duration)

            self.proc.driver_patter(self.number, pwm_on, pwm_off, pulse_settings.duration, True)
        else:
            self.log.debug('Enabling at 100%')

            self.proc.driver_schedule(number=self.number, schedule=0xffffffff,
                                      cycle_seconds=0, now=True)

    def pulse(self, pulse_settings: PulseSettings):
        """Enable this driver for `milliseconds`.

        ``ValueError`` will be raised if `milliseconds` is outside of the range
        0-255.
        """
        # TODO: implement pulsed_patter for pulse_power != 1
        if pulse_settings.power != 1:
            raise AssertionError("Not pulse_power not supported in P-Roc currently.")
        self.log.debug('Pulsing for %sms', pulse_settings.duration)
        self.proc.driver_pulse(self.number, pulse_settings.duration)

    def state(self):
        """Return a dictionary representing this driver's current configuration state."""
        return self.proc.driver_get_state(self.number)


class PROCMatrixLight(LightPlatformSoftwareFade):

    """A P-ROC matrix light device."""

    def __init__(self, number, proc_driver, machine):
        """Initialise matrix light device."""
        super().__init__(number, machine.clock.loop,
                         int(1 / machine.config['mpf']['default_light_hw_update_hz'] * 1000))
        self.log = logging.getLogger('PROCMatrixLight')
        self.proc = proc_driver

    def set_brightness(self, brightness: float):
        """Enable (turns on) this driver."""
        if brightness >= 1:
            self.proc.driver_schedule(number=self.number, schedule=0xffffffff,
                                      cycle_seconds=0, now=True)
        elif brightness > 0:
            pwm_on_ms, pwm_off_ms = Util.power_to_on_off(brightness)
            self.proc.driver_patter(self.number, pwm_on_ms, pwm_off_ms, 0, True)
        else:
            self.proc.driver_disable(self.number)

    def get_board_name(self):
        """Return board of the light."""
        # TODO: Implement this for PDB matrixes
        return "P-Roc Matrix"
