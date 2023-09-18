"""OPP servo implementation."""

from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface
from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf
import logging

MYPY = False
if MYPY:  # pragma: no cover
    from mpf.platforms.opp.opp import OppHardwarePlatform  # pylint: disable-msg=cyclic-import,unused-import


class OPPServo(ServoPlatformInterface):
    """A servo in the OPP platform."""

    __slots__ = ["number", "chain_serial", "platform", "speed", "current_position"]

    def __init__(self, chain_serial, servo_num, platform: "OppHardwarePlatform"):
        """initialize servo."""
        self.number = servo_num
        self.platform = platform
        self.chain_serial = chain_serial
        self.speed = 0
        self.current_position = 0

    def stop(self):
        """Disable servo.
        Set position to 0 to disable servo.
        """
        self.go_to_position(0)

    def go_to_position(self, position):
        """Set a servo position.

        position [0 to 1.0] is converted to position_numeric [0 to 255].
        position_numeric is measured in 10us intervals, so a position_numeric of 100 is a 1ms pulse
        and 150 is 1.5ms. A position_numeric of 0 disables the servo. Use caution with extreme
        position values as it could cause a servo to drive to a position it cannot reach.
        """

        # convert from [0,1] to [0, 255]
        position_numeric = int(position * 255)
        servo_offset = 0x3000 + self.number


        if position_numeric == 0 or self.current_position == 0 or self.speed <= 0:
            fade_ms = 0
        else:
            fade_ms = 600 * abs(position_numeric - self.current_position) / self.speed
            if fade_ms > 65535:
                fade_ms = 65535

        msg = bytearray()
        msg.append(0x20)
        msg.append(OppRs232Intf.SERIAL_LED_CMD_FADE)
        msg.append(int(servo_offset / 256))
        msg.append(int(servo_offset % 256))
        msg.append(int(0))  #number of servos (high)
        msg.append(int(1))  #number of servos (low)...only commanding one at a time.
        msg.append(int(fade_ms / 256))
        msg.append(int(fade_ms % 256))
        msg.append(position_numeric)
        msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
        cmd = bytes(msg)

        self.platform.debug_log("Set servo position on %s: %s", self.chain_serial, "".join(" 0x%02x" % b for b in cmd))

        self.platform.send_to_processor(self.chain_serial, cmd)

        self.current_position = position_numeric


    def set_speed_limit(self, speed_limit):
        """Set the speed of this servo

        For the standard 1ms pulse width change to move a servo between
        extremes, a speed of 1 will take 1 minute, and a speed of 60 would take
        1 second.

        A speed <= 0 is unrestricted by firmware
        """
        self.platform.debug_log("Change servo speed limit on %s: %s", self.chain_serial, int(speed_limit))

        self.speed = speed_limit

    def set_acceleration_limit(self, acceleration_limit):
        """Not implemented."""
