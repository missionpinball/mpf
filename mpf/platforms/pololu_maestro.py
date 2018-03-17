"""Pololu Maestro servo controller platform."""
import math
import asyncio
import logging
import serial
from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface

from mpf.core.platform import ServoPlatform


class PololuMaestroHardwarePlatform(ServoPlatform):

    """Supports the Pololu Maestro servo controllers via PySerial.

    Works with Micro Maestro 6, and Mini Maestro 12, 18, and 24.
    """

    def __init__(self, machine):
        """Initialise Pololu Servo Controller platform."""
        super().__init__(machine)
        self.log = logging.getLogger("Pololu Maestro")
        self.log.debug("Configuring template hardware interface.")
        self.config = self.machine.config['pololu_maestro']
        self.platform = None
        self.serial = None
        self.features['tickless'] = True

    def __repr__(self):
        """Return string representation."""
        return '<Platform.Pololu_Maestro>'

    @asyncio.coroutine
    def initialize(self):
        """Initialise platform."""
        yield from super().initialize()

        # validate our config (has to be in intialize since config_processor
        # is not read in __init__)
        self.config = self.machine.config_validator.validate_config("pololu_maestro", self.config)
        self.serial = serial.Serial(self.config['port'])

    def stop(self):
        """Close serial."""
        self.serial.close()

    def configure_servo(self, number: str):
        """Configure a servo device in paltform.

        Args:
            config (dict): Configuration of device
        """
        return PololuServo(int(number), self.config, self.serial)


class PololuServo(ServoPlatformInterface):

    """A servo on the pololu servo controller."""

    def __init__(self, number, config, serial_port):
        """Initialise Pololu servo."""
        self.log = logging.getLogger('PololuServo')
        self.number = number
        self.config = config
        self.serial = serial_port
        self.cmd_header = bytes([0xaa, 0xc])

    def go_to_position(self, position):
        """Set channel to a specified target value.

        Servo will begin moving
        based on Speed and Acceleration parameters previously set.
        Target values will be constrained within Min and Max range, if set.
        For servos, target represents the pulse width in of
        quarter-microseconds.
        Servo center is at 1500 microseconds, or 6000 quarter-microseconds
        Typcially valid servo range is 3000 to 9000 quarter-microseconds
        If channel is configured for digital output, values < 6000 = Low ouputco.

        Args:
            position: Servo position between 0 and 1
        """
        servo_min = self.config['servo_min']
        servo_max = self.config['servo_max']
        value = int(servo_min + position * (servo_max - servo_min))

        # if Min is defined and Target is below, force to Min
        if (self.config['servo_min'] > 0 and
                value < self.config['servo_min']):
            value = self.config['servo_min']

        # if Max is defined and Target is above, force to Max
        if 0 < self.config['servo_max'] < value:
            value = self.config['servo_max']

        lsb = value & 0x7f  # 7 bits for least significant byte
        msb = (value >> 7) & 0x7f  # shift 7 and take next 7 bits for msb
        # Send Pololu intro, device number, command, channel, and target
        # lsb/msb
        cmd = self.cmd_header + bytes([0x04, self.number, lsb, msb])
        if self.config['debug']:
            self.log.debug("Sending cmd: %s", "".join(" 0x%02x" % b for b in cmd))
        self.serial.write(cmd)

    def set_speed_limit(self, speed_limit):
        """Set the speed of the channel.

        Speed is measured as 0.25microseconds/10milliseconds

        For the standard 1ms pulse width change to move a servo between
        extremes, a speed of 1 will take 1 minute, and a speed of 60 would take
        1 second.

        Speed of 0 is unrestricted.

        Args:
            speed_limit: speed_limit to set

        """
        if speed_limit == -1.0:
            maestro_speed_limit = 0  # 0 is unrestricted for the maestro
        elif speed_limit == 0:
            maestro_speed_limit = 1  # minimum speed setting
        else:
            max_pos_change_per_second = speed_limit * self.config['servo_max']  # change normalized values for maestro
            maestro_speed_limit = int(max_pos_change_per_second / 1000 / 0.25)

        lsb = maestro_speed_limit & 0x7f  # 7 bits for least significant byte
        msb = (maestro_speed_limit >> 7) & 0x7f  # shift 7 and take next 7 bits for msb
        cmd = self.cmd_header + bytes([0x07, self.number, lsb, msb])
        self.serial.write(cmd)

    def set_acceleration_limit(self, acceleration_limit):
        """Set acceleration of channel.

        This provide soft starts and finishes when servo moves to target
        position.

        Valid values are from 0 to 255. 0=unrestricted, 1 is slowest start.
        It is measured in units of 0.25microseconds/10milliseconds/80milliseconds
        A value of 1 will take the servo about 3s to move between 1ms to 2ms
        range.
        """
        if acceleration_limit == -1.0:
            maestro_acceleration_normalized = 0  # 0 is unrestricted for the maestro
        elif acceleration_limit == 0:
            maestro_acceleration_normalized = 1  # minimum acceleration setting
        else:
            max_speed_change_per_second = math.sqrt(acceleration_limit * self.config['servo_max'])
            maestro_acceleration_limit = calculate_maestro_acceleration(max_speed_change_per_second)
            max_limit_value = calculate_maestro_acceleration(math.sqrt(1.0 * self.config['servo_max']))
            maestro_acceleration_normalized = int(255 / max_limit_value * maestro_acceleration_limit)

        lsb = maestro_acceleration_normalized & 0x7f  # 7 bits for least significant byte
        msb = (maestro_acceleration_normalized >> 7) & 0x7f  # shift 7 and take next 7 bits for msb
        cmd = self.cmd_header + bytes([0x09, self.number, lsb, msb])
        self.serial.write(cmd)


def calculate_maestro_acceleration(normalized_limit):
    """Calculate acceleration limit for the maestro."""
    return normalized_limit / 1000 / 0.25 / 80
