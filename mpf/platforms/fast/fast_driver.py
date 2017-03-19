"""A driver/coil in the fast platform."""
import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings


class FASTDriver(DriverPlatformInterface):

    """Base class for drivers connected to a FAST Controller."""

    def __init__(self, config, platform, number, platform_settings):
        """Initialise driver."""
        super().__init__(config, number)
        self.log = logging.getLogger('FASTDriver')
        self.autofire = None
        self.machine = platform.machine
        self.platform = platform
        self.driver_settings = dict()
        self.send = platform.net_connection.send
        self.platform_settings = platform_settings

        if platform_settings['connection'] == 1:
            self.driver_settings['config_cmd'] = 'DN:'
            self.driver_settings['trigger_cmd'] = 'TN:'
        else:
            self.driver_settings['config_cmd'] = 'DL:'
            self.driver_settings['trigger_cmd'] = 'TL:'

        self.log.debug("Driver Settings: %s", self.driver_settings)
        self.reset()

    def get_board_name(self):
        """Return the board of this driver."""
        if self.platform.machine_type == 'wpc':
            return "FAST WPC"
        else:
            coil_index = 0
            number = Util.hex_string_to_int(self.number)
            for board_obj in self.platform.io_boards.values():
                if coil_index <= number < coil_index + board_obj.driver_count:
                    return "FAST Board {}".format(str(board_obj.node_id))
                coil_index += board_obj.driver_count

            # fall back if not found
            return "FAST Unknown Board"

    def _get_pulse_ms(self, coil):
        if coil.config['pulse_ms'] is None:
            return self.machine.config['mpf']['default_pulse_ms']
        else:
            return coil.config['pulse_ms']

    def get_pulse_ms_for_cmd(self, coil):
        """Return pulse ms."""
        pulse_ms = self._get_pulse_ms(coil)
        if pulse_ms > 255:
            return "00"
        else:
            return Util.int_to_hex_string(pulse_ms)

    @classmethod
    def get_pwm_for_cmd(cls, power: float):
        """Return a hex string for a float power setting."""
        # use PWM8 if sufficiently accurate
        if (power * 8) - int(power * 8) < 0.025:
            return Util.pwm8_to_hex_string(int(power * 8)).upper()
        else:
            return Util.pwm32_to_hex_string(int(power * 32)).upper()

    @classmethod
    def get_pwm1_for_cmd(cls, coil):
        """Return pwm1/pulse pwm."""
        if coil.config['pulse_pwm_mask']:
            pulse_pwm_mask = str(coil.config['pulse_pwm_mask'])
            if len(pulse_pwm_mask) == 32:
                return Util.bin_str_to_hex_str(pulse_pwm_mask, 8)
            elif len(pulse_pwm_mask) == 8:
                return Util.bin_str_to_hex_str(pulse_pwm_mask, 2)
            else:
                raise ValueError("pulse_pwm_mask must either be 8 or 32 bits")
        elif coil.config['pulse_power32'] is not None:
            return "ff"
        elif coil.config['pulse_power'] is not None:
            return Util.pwm8_to_hex_string(coil.config['pulse_power'])
        else:
            return "ff"

    @classmethod
    def get_pwm2_for_cmd(cls, coil):
        """Return pwm2/hold pwm."""
        if coil.config['hold_pwm_mask']:
            hold_pwm_mask = str(coil.config['hold_pwm_mask'])
            if len(hold_pwm_mask) == 32:
                return Util.bin_str_to_hex_str(hold_pwm_mask, 8)
            elif len(hold_pwm_mask) == 8:
                return Util.bin_str_to_hex_str(hold_pwm_mask, 2)
            else:
                raise ValueError("hold_pwm_mask must either be 8 or 32 bits")
        elif coil.config['hold_power32'] is not None:
            return "ff"
        elif coil.config['hold_power'] is not None:
            return Util.pwm8_to_hex_string(coil.config['hold_power'])
        else:
            return "ff"

    def get_recycle_ms_for_cmd(self, recycle, pulse_ms):
        """Return recycle ms."""
        if not recycle:
            return "00"
        elif self.platform_settings['recycle_ms'] is not None:
            return Util.int_to_hex_string(self.platform_settings['recycle_ms'])
        else:
            # default recycle_ms to pulse_ms * 2
            if pulse_ms * 2 > 255:
                return "FF"
            else:
                return Util.int_to_hex_string(pulse_ms * 2)

    def get_config_cmd(self):
        """Return config cmd str."""
        return self.driver_settings['config_cmd']

    def get_trigger_cmd(self):
        """Return trigger cmd."""
        return self.driver_settings['trigger_cmd']

    @classmethod
    def get_control_for_cmd(cls, switch):
        """Return control bytes."""
        control = 0x01  # Driver enabled
        if switch.invert:
            control += 0x10
        return Util.int_to_hex_string(int(control))

    def reset(self):
        """Reset a driver."""
        self.log.debug("Resetting driver %s", self.driver_settings)
        # cmd = (self.get_config_cmd() +
        #        self.number +
        #        ',00,00,00')

        cmd = '{}{},00,00,00'.format(self.get_config_cmd(), self.number)

        self.send(cmd)

    def disable(self):
        """Disable (turn off) this driver."""
        cmd = '{}{},02'.format(self.get_trigger_cmd(), self.number)

        self.log.debug("Sending Disable Command: %s", cmd)
        self.send(cmd)
        self.check_auto()

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable (turn on) this driver."""
        if self.autofire:
            # If this driver is also configured for an autofire rule, we just
            # manually trigger it with the trigger_cmd and manual on ('03')
            cmd = '{}{},03'.format(self.get_trigger_cmd(), self.number)
        else:
            # Otherwise we send a full config command, trigger C1 (logic triggered
            # and drive now) switch ID 00, mode 18 (latched)

            cmd = '{}{},C1,00,18,{},{},{},00'.format(
                self.get_config_cmd(),
                self.number,
                Util.int_to_hex_string(pulse_settings.duration),
                self.get_pwm_for_cmd(pulse_settings.power),
                self.get_pwm_for_cmd(hold_settings.power))

        self.log.debug("Sending Enable Command: %s", cmd)
        self.send(cmd)

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse this driver."""
        hex_ms_string = Util.int_to_hex_string(pulse_settings.duration)

        if self.autofire:
            cmd = '{}{},01'.format(self.get_trigger_cmd(), self.number)

            self.log.debug("Received command to pulse driver, but"
                           " this driver is configured with an autofire "
                           "rule, so that pulse value will be used.")
        else:
            cmd = '{}{},89,00,10,{},{},00,00,00'.format(
                self.get_config_cmd(),
                self.number,
                hex_ms_string,
                self.get_pwm_for_cmd(pulse_settings.power))

        self.log.debug("Sending Pulse Command: %s", cmd)
        self.send(cmd)
        self.check_auto()

        return Util.hex_string_to_int(hex_ms_string)

    def check_auto(self):
        """Reenable autofire if configured."""
        if self.autofire:
            cmd = '{}{},00'.format(self.get_trigger_cmd(), self.number)

            self.log.debug("Re-enabling auto fire mode: %s", cmd)
            self.send(cmd)
