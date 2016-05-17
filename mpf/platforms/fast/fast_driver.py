import logging

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface


class FASTDriver(DriverPlatformInterface):
    """Base class for drivers connected to a FAST Controller.

    """

    def __init__(self, config, sender, machine):
        """

        """

        self.autofire = None
        self.machine = machine
        self.driver_settings = dict()
        self.config = config

        self.log = logging.getLogger('FASTDriver')

        # Number is already normalized FAST hex string at this point
        self.number = config['number']
        self.send = sender

        if config['connection'] == 1:
            self.driver_settings['config_cmd'] = 'DN:'
            self.driver_settings['trigger_cmd'] = 'TN:'
        else:
            self.driver_settings['config_cmd'] = 'DL:'
            self.driver_settings['trigger_cmd'] = 'TL:'

        self.log.debug("Driver Settings: %s", self.driver_settings)
        self.reset()

    def _get_pulse_ms(self, coil):
        if coil.config['pulse_ms'] is None:
            return self.machine.config['mpf']['default_pulse_ms']
        else:
            return coil.config['pulse_ms']

    def get_pulse_ms_for_cmd(self, coil):
        pulse_ms = self._get_pulse_ms(coil)
        if pulse_ms > 255:
            return "00"
        else:
            return Util.int_to_hex_string(pulse_ms)

    @classmethod
    def get_pwm1_for_cmd(cls, coil):
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

    def get_recycle_ms_for_cmd(self, coil):
        if not coil.config['recycle']:
            return "00"
        elif coil.config['recycle_ms'] is not None:
            return Util.int_to_hex_string(coil.config['recycle_ms'])
        else:
            # default recycle_ms to pulse_ms * 2
            pulse_ms = self._get_pulse_ms(coil)
            if pulse_ms * 2 > 255:
                return "FF"
            else:
                return Util.int_to_hex_string(pulse_ms * 2)

    def get_config_cmd(self):
        return self.driver_settings['config_cmd']

    def get_trigger_cmd(self):
        return self.driver_settings['trigger_cmd']

    @classmethod
    def get_control_for_cmd(cls, switch):
        control = 0x01  # Driver enabled
        if switch.invert:
            control += 0x10
        return Util.int_to_hex_string(int(control))

    def reset(self):
        """

        Resets a driver

        """
        self.log.debug("Resetting driver %s", self.driver_settings)
        # cmd = (self.get_config_cmd() +
        #        self.number +
        #        ',00,00,00')

        cmd = '{}{},00,00,00'.format(self.get_config_cmd(), self.number)

        self.send(cmd)

    def disable(self, coil):
        """Disables (turns off) this driver. """
        del coil

        # cmd = (self.get_trigger_cmd() +
        #        self.number + ',' + '02')

        cmd = '{}{},02'.format(self.get_trigger_cmd(), self.number)

        self.log.debug("Sending Disable Command: %s", cmd)
        self.send(cmd)
        self.check_auto()

    def enable(self, coil):
        """Enables (turns on) this driver. """

        if self.autofire:
            # If this driver is also configured for an autofire rule, we just
            # manually trigger it with the trigger_cmd and manual on ('03')
            # cmd = (self.get_trigger_cmd() +
            #        self.number + ',' +
            #        '03')

            cmd = '{}{},03'.format(self.get_trigger_cmd(), self.number)

            self.log.warning("Recived a command to enable this driver, but "
                             "this driver is configured with an autofire rule,"
                             " so this enable will reset that rule. We need to"
                             " change this behavior...")

        else:
            # Otherwise we send a full config command, trigger C1 (logic triggered
            # and drive now) switch ID 00, mode 18 (latched)

            if (self.get_pwm1_for_cmd(coil) == 'ff' and
                    self.get_pwm2_for_cmd(coil) == 'ff' and
                    not coil.config['allow_enable']):

                raise AssertionError("Received a command to enable this coil "
                                     "without pwm, but 'allow_enable' has not been"
                                     "set to True in this coil's configuration.")

            else:

                pulse_ms = self.get_pulse_ms_for_cmd(coil)

                cmd = '{}{},C1,00,18,{},{},{},{}'.format(
                    self.get_config_cmd(),
                    self.number,
                    pulse_ms,
                    self.get_pwm1_for_cmd(coil),
                    self.get_pwm2_for_cmd(coil),
                    self.get_recycle_ms_for_cmd(coil))

        # todo pwm32

        self.log.debug("Sending Enable Command: %s", cmd)
        self.send(cmd)
        # todo change hold to pulse with re-ups

    def pulse(self, coil, milliseconds):
        """Pulses this driver. """

        if isinstance(milliseconds, int):
            hex_ms_string = Util.int_to_hex_string(milliseconds)
        else:
            hex_ms_string = milliseconds

        if self.autofire:
            cmd = '{}{},01'.format(self.get_trigger_cmd(), self.number)

            if milliseconds:
                self.log.debug("Received command to pulse driver for %sms, but"
                               "this driver is configured with an autofire rule"
                               ", so that pulse value will be used instead.")
        else:
            cmd = '{}{},89,00,10,{},{},00,00,{}'.format(
                self.get_config_cmd(),
                self.number,
                hex_ms_string,
                self.get_pwm1_for_cmd(coil),
                self.get_recycle_ms_for_cmd(coil))

        self.log.debug("Sending Pulse Command: %s", cmd)
        self.send(cmd)
        self.check_auto()

        return Util.hex_string_to_int(hex_ms_string)

    def check_auto(self):

        if self.autofire:
            cmd = '{}{},00'.format(self.get_trigger_cmd(), self.number)

            self.log.debug("Re-enabling auto fire mode: %s", cmd)
            self.send(cmd)
