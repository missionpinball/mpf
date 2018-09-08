"""MMA8451 accelerometer platform."""
import asyncio
import logging

from mpf.platforms.interfaces.accelerometer_platform_interface import AccelerometerPlatformInterface

from mpf.core.platform import AccelerometerPlatform, I2cPlatform


class MMA8451Device(AccelerometerPlatformInterface):

    """MMA8451 accelerometer."""

    __slots__ = ["i2c_platform", "platform", "callback", "number", "task"]

    def __init__(self, number, callback, i2c_platform, platform):
        """Initialise MMA8451 accelerometer."""
        self.i2c_platform = i2c_platform    # type: I2cPlatform
        self.platform = platform            # type: MMA8451Platform
        self.callback = callback
        self.number = number

        self.task = self.platform.machine.clock.loop.create_task(self._poll())
        self.task.add_done_callback(self._done)

    @staticmethod
    def _done(future: asyncio.Future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    @asyncio.coroutine
    def _poll(self):
        device = yield from self.i2c_platform.configure_i2c(self.number)
        # check id
        self.platform.log.info("Checking ID of device at: %s", self.number)
        device_id = yield from device.i2c_read8(0x0D)
        if device_id != 0x1A:
            raise AssertionError("Device ID does not match MMA8451. Detected: {}".format(device_id))

        # reset
        self.platform.log.info("Resetting device at: %s", self.number)
        device.i2c_write8(0x2B, 0x40)
        yield from asyncio.sleep(.3, loop=self.platform.machine.clock.loop)
        result = -1
        for _ in range(10):
            result = yield from device.i2c_read8(0x2B)
            if result == 0:
                break
            self.platform.log.warning("Failed to reset: %s at %s", result, self.number)
            yield from asyncio.sleep(.5, loop=self.platform.machine.clock.loop)
        else:
            raise AssertionError("Failed to reset MMA8451 accelerometer. Result: {}".format(result))

        # set resolution to 2g
        device.i2c_write8(0x2B, 0x02)

        # set ready
        device.i2c_write8(0x2D, 0x01)
        device.i2c_write8(0x2E, 0x01)

        # turn on orientation
        device.i2c_write8(0x11, 0x40)

        # low noise mode, 12,5Hz and activate
        device.i2c_write8(0x2A, 0x2D)

        # wait for activate
        yield from asyncio.sleep(.3, loop=self.platform.machine.clock.loop)

        self.platform.log.info("Init done for device at: %s", self.number)

        while True:
            data = yield from device.i2c_read_block(0x01, 6)
            x = ((data[0] << 8) | data[1]) >> 2
            y = ((data[2] << 8) | data[3]) >> 2
            z = ((data[4] << 8) | data[5]) >> 2
            max_val = 2 ** (14 - 1) - 1
            signed_max = 2 ** 14
            x -= signed_max if x > max_val else 0
            y -= signed_max if y > max_val else 0
            z -= signed_max if z > max_val else 0
            range_divisor = 4096 / 9.80665
            x = round((float(x)) / range_divisor, 3)
            y = round((float(y)) / range_divisor, 3)
            z = round((float(z)) / range_divisor, 3)
            self.callback.update_acceleration(x, y, z)
            yield from asyncio.sleep(.1, loop=self.platform.machine.clock.loop)


class MMA8451Platform(AccelerometerPlatform):

    """MMA8451 accelerometer platform."""

    __slots__ = ["accelerometers"]

    def __init__(self, machine):
        """Configure MMA8451 based accelerometers."""
        super().__init__(machine)
        self.log = logging.getLogger('mma8451')
        self.debug_log("Configuring MMA8451 based accelerometers.")
        self.accelerometers = {}

    @asyncio.coroutine
    def initialize(self):
        """Initialise MMA8451 platform."""
        pass

    def stop(self):
        """Stop accelerometer poll tasks."""
        for accelerometer in self.accelerometers:
            if accelerometer.task:
                accelerometer.task.cancel()
                accelerometer.task = None

    def configure_accelerometer(self, number, config, callback) -> MMA8451Device:
        """Configure MMA8451 accelerometer."""
        config = self.machine.config_validator.validate_config("mma8451_accelerometer", config)
        i2c_platform = self.machine.get_platform_sections("i2c", config['i2c_platform'])
        return MMA8451Device(number, callback, i2c_platform, self)
